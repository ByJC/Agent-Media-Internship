import sys
import os
import json
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
    return json.dumps(result, indent=2)


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
        "You can score video ads three ways:\n"
        "  1. YouTube URL — call score_video_ad with the URL as video_source.\n"
        "  2. Local file path — call score_video_ad with the absolute path as video_source.\n"
        "  3. Uploaded/dragged file — when the user's message contains "
        "[Uploaded Artifact: \"filename\"], extract the filename from that placeholder "
        "and IMMEDIATELY call score_uploaded_video with that exact filename. "
        "This placeholder tells you what was JUST uploaded — always use the filename "
        "from the CURRENT message, never from previous messages or conversation history. "
        "Do NOT call load_artifacts. Do NOT repeat or reference previous scoring results. "
        "Do NOT say you cannot process uploaded videos.\n\n"
        "After the tool returns, present the results in this exact order:\n\n"
        "SECTION 1 — Header\n"
        "Write a title line: '## Ad Effectiveness Analysis — [Brand/Ad Name]'\n"
        "Infer the brand or ad name from the Branding dimension's evidence observations in the JSON "
        "(they will mention the brand name or product). If unclear, use the video ID from the URL.\n\n"
        "SECTION 2 — ABCD Breakdown\n"
        "For each of the 4 dimensions (Attention, Branding, Connection, Direction) write:\n"
        "  * Score label using its scale: Attention(0=no hook,1=partial hook,2=strong hook), "
        "Branding(0=not visible,1=early but sparse,2=clearly visible throughout), "
        "Connection(0=no emotional story,1=some human element,2=strong emotional narrative), "
        "Direction(0=no CTA,1=branded closing,2=explicit CTA)\n"
        "  * Evidence: for each item in the evidence array, write the timestamp (e.g. 00:04) "
        "followed by the observation VERBATIM — copy the text exactly from the JSON, do not paraphrase.\n"
        "  * Fix: the recommended fix, or 'None needed' if score is 2.\n\n"
        "SECTION 3 — Overall Score\n"
        "Write: 'Overall Score: [score]/100 — [band]' where [score] is the exact value of the `score` "
        "field from the JSON (already normalised to 0–100). Never add up raw scores yourself.\n\n"
        "SECTION 4 — Raw JSON\n"
        "Write the heading '### Raw JSON Output' then show the full JSON exactly as returned by the tool "
        "in a ```json code block."
    ),
    tools=[score_video_ad, score_uploaded_video, load_artifacts_tool],
)

# App wraps the agent with SaveFilesAsArtifactsPlugin so that when a user
# drags/uploads a video file, the raw bytes are saved as an artifact and
# replaced with a text placeholder — instead of being sent inline to the model.
app = App(
    name="web_search_agent",
    root_agent=root_agent,
    plugins=[SaveFilesAsArtifactsPlugin()],
)
