import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from google.adk.agents import Agent


def score_video_ad(youtube_url: str, ad_type: str = "brand") -> str:
    """Score a YouTube video ad against ABCD criteria: Attention (YT-A1), Branding (YT-B1), Connection (YT-C1), Direction (YT-D1).

    Args:
        youtube_url: The full YouTube URL of the video ad to score (e.g. https://www.youtube.com/watch?v=...).
        ad_type: "brand" for brand awareness ads (default), "direct_response" for performance/DR ads.

    Returns:
        A JSON string with per-criterion scores (0-2), evidence timestamps, and fix recommendations.
    """
    from web_search_agent.video_scorer import ingest_video, score_criterion, aggregate_scores

    video = ingest_video(youtube_url, sample_fps=1.0)

    results = [
        score_criterion(video, criterion_id="YT-A1", votes=3, ad_type=ad_type),
        score_criterion(video, criterion_id="YT-B1", votes=3, ad_type=ad_type),
        score_criterion(video, criterion_id="YT-C1", votes=3, ad_type=ad_type),
        score_criterion(video, criterion_id="YT-D1", votes=3, ad_type=ad_type),
    ]
    ad_score = aggregate_scores(results, video, source=youtube_url, ad_type=ad_type)

    # Strip frame_b64 before returning — base64 PNG data is too large for the agent context window
    result = ad_score.model_dump()
    for dim in result["dimensions"]:
        for ev in dim["evidence"]:
            ev.pop("frame_b64", None)
    return json.dumps(result, indent=2)


root_agent = Agent(
    name="web_search_agent",
    model="gemini-2.5-flash",
    description="An agent that scores YouTube video ads against the ABCD creative rubric.",
    instruction=(
        "You are a video ad creative quality assistant. "
        "Whenever the user shares a YouTube URL, immediately call score_video_ad with that URL. "
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
    tools=[score_video_ad],
)
