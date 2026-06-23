import sys
from dotenv import load_dotenv

load_dotenv()

from web_search_agent.video_scorer import ingest_video, score_criterion


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <youtube_url_or_local_path>")
        sys.exit(1)

    source = sys.argv[1]
    print(f"Ingesting: {source}")

    video = ingest_video(source, sample_fps=1.0)
    print(f"Ingested: {len(video.frames)} frames, duration={video.duration:.1f}s, "
          f"aspect={video.aspect_ratio}, audio={video.has_audio}")

    print("Scoring YT-A1 (Attention — hook in first 5s)...")
    result = score_criterion(video, criterion_id="YT-A1")

    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
