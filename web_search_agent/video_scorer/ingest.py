import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class VideoData:
    frames: list[bytes] = field(default_factory=list)
    transcript: str = ""
    duration: float = 0.0
    aspect_ratio: str = ""
    has_audio: bool = False


def _is_youtube_url(source: str) -> bool:
    return bool(re.match(r"https?://(www\.)?(youtube\.com|youtu\.be)/", source))


def _get_video_metadata(path: str) -> tuple[float, str, bool]:
    """Return (duration_seconds, aspect_ratio, has_audio) via ffprobe."""
    import json

    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-show_format", path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    info = json.loads(result.stdout)
    duration = float(info.get("format", {}).get("duration", 0))

    width = height = 0
    has_audio = False
    for stream in info.get("streams", []):
        if stream.get("codec_type") == "video" and not width:
            width = stream.get("width", 0)
            height = stream.get("height", 0)
        if stream.get("codec_type") == "audio":
            has_audio = True

    aspect_ratio = f"{width}:{height}" if width and height else "unknown"
    return duration, aspect_ratio, has_audio


def _extract_frames(video_path: str, sample_fps: float, tmp_dir: str) -> list[bytes]:
    """Run ffmpeg to extract frames, return list of PNG bytes."""
    output_pattern = str(Path(tmp_dir) / "frame_%04d.png")
    subprocess.run(
        [
            "ffmpeg", "-i", video_path,
            "-vf", f"fps={sample_fps}",
            "-q:v", "2",
            output_pattern,
            "-y",
        ],
        capture_output=True,
        check=True,
    )
    frame_files = sorted(Path(tmp_dir).glob("frame_*.png"))
    return [f.read_bytes() for f in frame_files]


def _fetch_youtube_transcript(url: str) -> str:
    """Fetch captions from YouTube via youtube-transcript-api."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        video_id = re.search(r"(?:v=|youtu\.be/)([A-Za-z0-9_-]{11})", url)
        if not video_id:
            return ""
        snippets = YouTubeTranscriptApi.get_transcript(video_id.group(1))
        return " ".join(s["text"] for s in snippets)
    except Exception:
        return ""


def ingest_video(source: str, sample_fps: float = 1.0) -> VideoData:
    """Ingest a local video file or YouTube URL into frames + transcript.

    Args:
        source: Local file path or YouTube URL.
        sample_fps: Frames to extract per second (default 1.0).

    Returns:
        VideoData with frames as PNG bytes, transcript, and metadata.
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        if _is_youtube_url(source):
            video_path = str(Path(tmp_dir) / "video.mp4")
            subprocess.run(
                [
                    "yt-dlp",
                    "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "--merge-output-format", "mp4",
                    "-o", video_path,
                    source,
                ],
                capture_output=True,
                check=True,
            )
            transcript = _fetch_youtube_transcript(source)
        else:
            video_path = source
            transcript = ""

        duration, aspect_ratio, has_audio = _get_video_metadata(video_path)
        frames = _extract_frames(video_path, sample_fps, tmp_dir)

        return VideoData(
            frames=frames,
            transcript=transcript,
            duration=duration,
            aspect_ratio=aspect_ratio,
            has_audio=has_audio,
        )
