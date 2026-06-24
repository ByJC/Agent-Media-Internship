import sys
import os
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
        score_criterion(video, criterion_id="YT-B1", ad_type=ad_type),
        score_criterion(video, criterion_id="YT-C1", ad_type=ad_type),
        score_criterion(video, criterion_id="YT-D1", ad_type=ad_type),
    ]
    ad_score = aggregate_scores(results, video, source=youtube_url, ad_type=ad_type)

    return ad_score.model_dump_json(indent=2)


root_agent = Agent(
    name="web_search_agent",
    model="gemini-2.5-flash",
    description="An agent that scores YouTube video ads against the ABCD creative rubric.",
    instruction=(
        "You are a video ad creative quality assistant. "
        "Whenever the user shares a YouTube URL, immediately call score_video_ad with that URL. "
        "After the tool returns, explain each dimension's result in plain English using its own scale: "
        "Attention (0=no hook, 1=partial hook, 2=strong hook), "
        "Branding (0=not visible, 1=partially visible, 2=clearly visible throughout), "
        "Connection (0=no emotional story, 1=some human element, 2=strong emotional narrative), "
        "Direction (0=no CTA, 1=weak/late CTA, 2=clear prominent CTA). "
        "For each dimension state the score label, the evidence, and the recommended fix."
    ),
    tools=[score_video_ad],
)
