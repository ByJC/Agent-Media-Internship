import base64
import math
import os
from collections import Counter

from pydantic import BaseModel
from google import genai
from google.genai import types

from .ingest import VideoData
from .prompts import get_prompt

GRAB_WINDOW_SECONDS = 5

# Criteria that only need the first 5s; others use the full video
GRAB_WINDOW_CRITERIA = {"YT-A1"}

# (dimension_name, weight) — weights don't need to sum to 1; they're normalised at aggregation
DIMENSION_WEIGHTS: dict[str, tuple[str, float]] = {
    "YT-A1": ("Attention",  0.30),
    "YT-B1": ("Branding",   0.25),
    "YT-C1": ("Connection", 0.20),
    "YT-D1": ("Direction",  0.25),
}

# Brand awareness ads: branding/connection matter more; explicit CTAs less expected
DIMENSION_WEIGHTS_BRAND: dict[str, tuple[str, float]] = {
    "YT-A1": ("Attention",  0.25),
    "YT-B1": ("Branding",   0.30),
    "YT-C1": ("Connection", 0.25),
    "YT-D1": ("Direction",  0.20),
}

# Edit these thresholds to change band boundaries (score is 0–100)
BAND_THRESHOLDS = {
    "strong":   80,
    "adequate": 60,
    "weak":     40,
    # below 40 → "poor"
}


class EvidenceItem(BaseModel):
    timestamp: str
    observation: str
    frame_b64: str | None = None


class CriterionResult(BaseModel):
    criterion_id: str
    score: int
    evidence: list[EvidenceItem] = []
    fix: str | None = None


class DimensionResult(BaseModel):
    name: str
    criterion_id: str
    weight: float
    raw_score: int
    pct: float
    evidence: list[EvidenceItem] = []
    fix: str | None = None


class AdScore(BaseModel):
    platform: str
    source: str
    duration_seconds: float
    ad_type: str
    score: float
    band: str
    dimensions: list[DimensionResult]
    top_fixes: list[str]


def _ts_to_seconds(ts: str) -> int:
    """Parse 'MM:SS' timestamp to integer seconds."""
    parts = ts.split(":")
    return int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else int(parts[0])


def _sample_frames(frames: list[bytes], max_frames: int) -> list[bytes]:
    """Pick max_frames evenly spaced across the full frame list."""
    if len(frames) <= max_frames:
        return frames
    step = len(frames) / max_frames
    return [frames[int(i * step)] for i in range(max_frames)]


def _band(score: float) -> str:
    for band_name, threshold in BAND_THRESHOLDS.items():
        if score >= threshold:
            return band_name
    return "poor"


def _merge_evidence_from_votes(mode_results: list, tolerance: int = 2) -> list:
    """Merge evidence from all mode-score results, deduplicating timestamps within ±tolerance seconds."""
    seen_buckets: set[int] = set()
    merged = []
    for r in mode_results:
        for ev in r.evidence:
            sec = _ts_to_seconds(ev.timestamp)
            bucket = (sec // tolerance) * tolerance
            if bucket not in seen_buckets:
                seen_buckets.add(bucket)
                merged.append(ev)
    merged.sort(key=lambda e: _ts_to_seconds(e.timestamp))
    return merged


def score_criterion(video: VideoData, criterion_id: str = "YT-A1", votes: int = 1, ad_type: str = "brand") -> CriterionResult:
    """Score one ABCD criterion using Gemini multimodal.

    Args:
        video: VideoData from ingest_video().
        criterion_id: Rubric criterion to score (default "YT-A1").
        votes: Number of independent scoring calls; final score is the mode. Use votes=3
               for volatile criteria (e.g. YT-A1) to guarantee stability.
        ad_type: "brand" or "direct_response". Selects the appropriate prompt variant.

    Returns:
        CriterionResult with score (0/1/2), evidence, and fix.
    """
    prompt_text = get_prompt(criterion_id, ad_type)
    if not prompt_text:
        raise ValueError(f"Unknown criterion: {criterion_id}.")

    # A1 only needs the grab window; B1/C1/D1 need the full video
    if criterion_id in GRAB_WINDOW_CRITERIA:
        frames = video.frames[:math.ceil(GRAB_WINDOW_SECONDS)]
    else:
        frames = video.frames

    if not frames:
        raise ValueError("No frames extracted — check that ffmpeg is installed and the source is valid.")

    # B/C/D: evenly sample up to 30 frames across the full video
    # A1: already sliced to grab window, no sampling needed
    if criterion_id not in GRAB_WINDOW_CRITERIA:
        frames = _sample_frames(frames, 30)

    # Build parts: frames first, then transcript, then prompt
    parts = [types.Part.from_bytes(data=frame, mime_type="image/png") for frame in frames]
    if video.transcript:
        parts.append(types.Part.from_text(text=f"Video transcript:\n{video.transcript[:1000]}"))
    parts.append(types.Part.from_text(text=prompt_text))

    client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

    def _call_once() -> CriterionResult:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=parts,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CriterionResult,
                temperature=0.0,
            ),
        )
        result = CriterionResult.model_validate_json(response.text)
        if not result.evidence:
            result.evidence = [EvidenceItem(timestamp="00:00", observation="No evidence returned by model.")]
        if result.score < 2 and not result.fix:
            result.fix = "Review this criterion and add improvements to reach a score of 2."
        # Enrich each evidence item with the actual video frame
        for ev in result.evidence:
            try:
                idx = _ts_to_seconds(ev.timestamp)
                if 0 <= idx < len(video.frames):
                    ev.frame_b64 = base64.b64encode(video.frames[idx]).decode()
            except (ValueError, IndexError):
                pass
        return result

    if votes == 1:
        return _call_once()

    # Majority vote: run `votes` times, return a result whose score matches the mode.
    # On a tie, the lower (more conservative) score wins.
    all_results = [_call_once() for _ in range(votes)]
    scores = [r.score for r in all_results]
    mode_score = Counter(scores).most_common(1)[0][0]
    mode_results = [r for r in all_results if r.score == mode_score]
    base = mode_results[0]
    return CriterionResult(
        criterion_id=base.criterion_id,
        score=base.score,
        evidence=_merge_evidence_from_votes(mode_results),
        fix=base.fix,
    )


def aggregate_scores(
    results: list[CriterionResult],
    video: VideoData,
    source: str,
    platform: str = "youtube",
    ad_type: str = "brand",
) -> AdScore:
    """Aggregate per-criterion results into a single AdScore.

    Args:
        results: List of CriterionResult from score_criterion().
        video: VideoData used for metadata (duration).
        source: Original video URL or file path.
        platform: Platform key (default "youtube").
        ad_type: "brand" or "direct_response". Selects dimension weights.

    Returns:
        AdScore with normalized 0-100 score, band, dimensions, and top_fixes.
    """
    results_by_id = {r.criterion_id: r for r in results}
    weights = DIMENSION_WEIGHTS_BRAND if ad_type == "brand" else DIMENSION_WEIGHTS

    dimensions: list[DimensionResult] = []
    total_weight = 0.0

    for criterion_id, (name, weight) in weights.items():
        if criterion_id not in results_by_id:
            continue
        r = results_by_id[criterion_id]
        pct = (r.score / 2) * 100
        dimensions.append(DimensionResult(
            name=name,
            criterion_id=criterion_id,
            weight=weight,
            raw_score=r.score,
            pct=pct,
            evidence=r.evidence,
            fix=r.fix,
        ))
        total_weight += weight

    # Normalise weights and compute overall score
    overall = sum(d.pct * (d.weight / total_weight) for d in dimensions)
    overall = round(overall, 1)

    # Rank fixes by impact: (2 - raw_score) × weight, descending
    fixable = [d for d in dimensions if d.raw_score < 2 and d.fix]
    fixable.sort(key=lambda d: (2 - d.raw_score) * d.weight, reverse=True)
    top_fixes = [f"{d.fix} ({d.criterion_id})" for d in fixable]

    return AdScore(
        platform=platform,
        source=source,
        duration_seconds=round(video.duration, 1),
        ad_type=ad_type,
        score=overall,
        band=_band(overall),
        dimensions=dimensions,
        top_fixes=top_fixes,
    )
