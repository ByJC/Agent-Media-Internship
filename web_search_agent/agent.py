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
        "After the tool returns, present the results in two parts:\n\n"
        "PART 1 — show the full raw JSON output exactly as returned by the tool, "
        "wrapped in a ```json code block.\n\n"
        "PART 2 — below the JSON, write a structured breakdown with these exact rules:\n"
        "- For each of the 4 dimensions (Attention, Branding, Connection, Direction), write:\n"
        "  * Score label: Attention(0=no hook,1=partial hook,2=strong hook), "
        "Branding(0=not visible,1=early but sparse,2=clearly visible throughout), "
        "Connection(0=no emotional story,1=some human element,2=strong emotional narrative), "
        "Direction(0=no CTA,1=branded closing,2=explicit CTA)\n"
        "  * Evidence: quote each item from the evidence array VERBATIM — "
        "for each item write the timestamp (e.g. 00:04) followed by the observation exactly as it appears in the JSON. "
        "Do NOT paraphrase or summarise — copy the observation text directly.\n"
        "  * Fix: state the recommended fix if one exists, or 'None needed' if score is 2.\n"
        "- End with: 'Overall Score: [score field value]/100 — [band]' "
        "where [score field value] is the exact number from the JSON `score` field (it is already out of 100). "
        "Do NOT add up raw scores yourself — always use the `score` field from the JSON."
    ),
    tools=[score_video_ad],
)
