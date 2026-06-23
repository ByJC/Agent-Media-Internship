import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from google.adk.agents import Agent


def score_video_ad(youtube_url: str) -> str:
    """Score a YouTube video ad against the ABCD creative rubric (criterion YT-A1: hook in first 5s).

    Args:
        youtube_url: The full YouTube URL of the video ad to score (e.g. https://www.youtube.com/watch?v=...).

    Returns:
        A JSON string with score (0-2), evidence timestamp, and a fix recommendation if score < 2.
    """
    from web_search_agent.video_scorer import ingest_video, score_criterion
    video = ingest_video(youtube_url, sample_fps=1.0)
    result = score_criterion(video, criterion_id="YT-A1")
    return result.model_dump_json(indent=2)


root_agent = Agent(
    name="web_search_agent",
    model="gemini-2.5-flash",
    description="An agent that scores YouTube video ads against the ABCD creative rubric.",
    instruction=(
        "You are a video ad creative quality assistant. "
        "Whenever the user shares a YouTube URL, immediately call score_video_ad with that URL. "
        "After the tool returns, explain the result in plain English: "
        "the score (0=no hook, 1=partial hook, 2=strong hook), the evidence, and the recommended fix."
    ),
    tools=[score_video_ad],
)
