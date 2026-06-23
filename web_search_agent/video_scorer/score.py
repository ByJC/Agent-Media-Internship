import math
import os

from pydantic import BaseModel
from google import genai
from google.genai import types

from .ingest import VideoData
from .prompts import CRITERION_PROMPTS

GRAB_WINDOW_SECONDS = 5


class CriterionResult(BaseModel):
    criterion_id: str
    score: int
    evidence: str | None = None
    fix: str | None = None


def score_criterion(video: VideoData, criterion_id: str = "YT-A1") -> CriterionResult:
    """Score one ABCD criterion using Gemini multimodal.

    Args:
        video: VideoData from ingest_video().
        criterion_id: Rubric criterion to score (default "YT-A1").

    Returns:
        CriterionResult with score (0/1/2), evidence, and fix.
    """
    prompt_text = CRITERION_PROMPTS.get(criterion_id)
    if not prompt_text:
        raise ValueError(f"Unknown criterion: {criterion_id}. Available: {list(CRITERION_PROMPTS)}")

    # Slice to grab window only
    grab_frame_count = math.ceil(GRAB_WINDOW_SECONDS * 1.0)
    grab_frames = video.frames[:grab_frame_count]

    if not grab_frames:
        raise ValueError("No frames extracted — check that ffmpeg is installed and the source is valid.")

    # Build parts: frames first, then prompt text
    parts = [types.Part.from_bytes(data=frame, mime_type="image/png") for frame in grab_frames]
    if video.transcript:
        parts.append(types.Part.from_text(text=f"Transcript of first {GRAB_WINDOW_SECONDS}s:\n{video.transcript[:500]}"))
    parts.append(types.Part.from_text(text=prompt_text))

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=parts,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=CriterionResult,
            temperature=0.1,
        ),
    )

    result = CriterionResult.model_validate_json(response.text)

    # Enforce contract: score < 2 must have evidence + fix
    if result.score < 2:
        assert result.evidence, f"Model returned score={result.score} without evidence for {criterion_id}"
        assert result.fix, f"Model returned score={result.score} without fix for {criterion_id}"

    return result
