import sys
import os
import json
import asyncio
import tempfile
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from google.adk.agents import Agent
from google.adk.apps.app import App
from google.adk.tools.load_artifacts_tool import load_artifacts_tool
from google.adk.tools.tool_context import ToolContext
from google.adk.plugins.save_files_as_artifacts_plugin import SaveFilesAsArtifactsPlugin


def score_video_ad(video_source: str, ad_type: str = "brand") -> str:
    """Score a video ad against ABCD criteria: Attention (YT-A1), Branding (YT-B1), Connection (YT-C1), Direction (YT-D1).

    Args:
        video_source: YouTube URL (e.g. https://www.youtube.com/watch?v=...) OR an absolute
                      local file path (e.g. /Users/cyrus/Desktop/ad.mp4). Supports .mp4,
                      .mov, .avi, and any other ffmpeg-compatible video format.
        ad_type: "brand" for brand awareness ads (default), "direct_response" for performance/DR ads.

    Returns:
        A JSON string with per-criterion scores (0-2), evidence timestamps, and fix recommendations.
    """
    from web_search_agent.video_scorer import ingest_video, score_criterion, aggregate_scores

    video = ingest_video(video_source, sample_fps=1.0)

    results = [
        score_criterion(video, criterion_id="YT-A1", votes=3, ad_type=ad_type),
        score_criterion(video, criterion_id="YT-B1", votes=3, ad_type=ad_type),
        score_criterion(video, criterion_id="YT-C1", votes=3, ad_type=ad_type),
        score_criterion(video, criterion_id="YT-D1", votes=3, ad_type=ad_type),
    ]
    ad_score = aggregate_scores(results, video, source=video_source, ad_type=ad_type)

    result = ad_score.model_dump()
    for dim in result["dimensions"]:
        for ev in dim["evidence"]:
            ev.pop("frame_b64", None)

    safety_result = score_criterion(video, criterion_id="YT-E1", votes=3, ad_type=ad_type)
    safety_dump = safety_result.model_dump()
    for ev in safety_dump["evidence"]:
        ev.pop("frame_b64", None)
    result["brand_safety"] = safety_dump

    return json.dumps(result, indent=2)


async def score_multiple_videos(video_sources: list, ad_type: str = "brand") -> str:
    """Score up to 3 video ads in parallel. Use this whenever the user provides more than one
    YouTube URL or file path in the same message — it is faster than scoring them one by one.

    Args:
        video_sources: A list of YouTube URLs and/or absolute local file paths.
        ad_type: "brand" for brand awareness ads (default), "direct_response" for DR ads.

    Returns:
        A JSON object mapping each source to its full ABCD scoring result.
    """
    async def _score_one(source: str) -> tuple[str, object]:
        try:
            result_str = await asyncio.to_thread(score_video_ad, source, ad_type)
            return source, json.loads(result_str)
        except Exception as exc:
            return source, {"error": str(exc)}

    pairs = await asyncio.gather(*[_score_one(s) for s in video_sources])
    return json.dumps({source: result for source, result in pairs}, indent=2)


async def score_uploaded_video(filename: str, tool_context: ToolContext, ad_type: str = "brand") -> str:
    """Score a video that was uploaded or dragged directly into the chat.

    Call this when the user uploads or drags a video file into the chat as an attachment.
    Do NOT use this for YouTube URLs or file paths — use score_video_ad for those.

    Args:
        filename: The exact filename of the uploaded video shown in the artifacts list
                  (e.g. 'ad.mp4', 'spot.mov'). Do not include a directory path.
        ad_type: "brand" for brand awareness ads (default), "direct_response" for DR ads.
    """
    artifact = await tool_context.load_artifact(filename)
    if artifact is None:
        available = await tool_context.list_artifacts()
        return json.dumps({
            "error": f"No artifact named '{filename}' found in this session.",
            "available_artifacts": available,
            "hint": "Use one of the filenames from available_artifacts.",
        })

    if not artifact.inline_data or not artifact.inline_data.data:
        return json.dumps({"error": f"Could not read video bytes for '{filename}'."})

    video_bytes = artifact.inline_data.data
    if isinstance(video_bytes, str):
        import base64 as _b64
        video_bytes = _b64.b64decode(video_bytes)

    suffix = Path(filename).suffix or ".mp4"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(video_bytes)
        tmp_path = tmp.name

    try:
        return score_video_ad(tmp_path, ad_type)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


root_agent = Agent(
    name="web_search_agent",
    model="gemini-2.5-flash",
    description="An agent that scores YouTube video ads against the ABCD creative rubric.",
    instruction=(
        "You are a video ad creative quality assistant. "
        "You can score video ads four ways:\n"
        "  1. Single YouTube URL — call score_video_ad with the URL as video_source.\n"
        "  2. Single local file path — call score_video_ad with the absolute path as video_source.\n"
        "  3. Multiple videos — call score_multiple_videos with the full list. "
        "Always use this when the user provides more than one video source — never call "
        "score_video_ad repeatedly in sequence.\n"
        "  4. Uploaded/dragged file — when the user's message contains "
        "[Uploaded Artifact: \"filename\"], extract the filename from that placeholder "
        "and IMMEDIATELY call score_uploaded_video with that exact filename. "
        "Always use the filename from the CURRENT message, never from history. "
        "Do NOT call load_artifacts. Do NOT say you cannot process uploaded videos.\n\n"
        "After any tool returns, present results for EACH video in this exact order:\n\n"
        "SECTION 1 — Header\n"
        "Write: '## Ad Effectiveness Analysis — [Brand/Ad Name]'\n"
        "Infer the brand from the Branding dimension evidence. If unclear, use the video ID.\n\n"
        "SECTION 2 — ABCD Breakdown\n"
        "For each of the 4 dimensions (Attention, Branding, Connection, Direction) write:\n"
        "  * Score label: Attention(0=no hook,1=partial hook,2=strong hook), "
        "Branding(0=not visible,1=early but sparse,2=clearly visible throughout), "
        "Connection(0=no emotional story,1=some human element,2=strong emotional narrative), "
        "Direction(0=no CTA,1=branded closing,2=explicit CTA)\n"
        "  * Evidence: each timestamp followed by the observation VERBATIM from the JSON.\n"
        "  * Fix: the recommended fix, or 'None needed' if score is 2.\n\n"
        "SECTION 3 — Overall Score\n"
        "Write: 'Overall Score: [score]/100 — [band]' using the `score` field from the JSON. "
        "Never add up raw scores yourself.\n\n"
        "SECTION 4 — Brand Safety\n"
        "Always write this section. Check the `brand_safety` key in the JSON.\n"
        "If brand_safety.score = 2: Write '### Brand Safety: ✅ No Issues Detected' then one line "
        "from brand_safety.evidence describing what was checked.\n"
        "If brand_safety.score = 1: Write '### ⚠️ Brand Safety: Minor Concerns' then list each item "
        "from brand_safety.evidence as '- [timestamp] [observation]', followed by the fix.\n"
        "If brand_safety.score = 0: Write '### 🚨 Brand Safety: Violation Detected' then list each item "
        "from brand_safety.evidence as '- [timestamp] [observation]', followed by the fix.\n\n"
        "SECTION 5 — Raw JSON\n"
        "Write '### Raw JSON Output' then the full JSON in a ```json code block.\n\n"
        "When multiple videos were scored, repeat Sections 1–5 for each video, separated by a divider (---)."
    ),
    tools=[score_video_ad, score_multiple_videos, score_uploaded_video, load_artifacts_tool],
)

# App wraps the agent with SaveFilesAsArtifactsPlugin so that when a user
# drags/uploads a video file, the raw bytes are saved as an artifact and
# replaced with a text placeholder — instead of being sent inline to the model.
app = App(
    name="web_search_agent",
    root_agent=root_agent,
    plugins=[SaveFilesAsArtifactsPlugin()],
)
