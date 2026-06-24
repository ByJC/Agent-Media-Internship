import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

from web_search_agent.video_scorer import ingest_video, score_criterion, aggregate_scores


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="YouTube URL or local file path")
    parser.add_argument("--ad-type", default="brand", choices=["brand", "direct_response"],
                        help="Rubric to use: 'brand' (default) or 'direct_response'")
    args = parser.parse_args()

    print(f"Ingesting: {args.source}")

    video = ingest_video(args.source, sample_fps=1.0)
    print(f"Ingested: {len(video.frames)} frames, duration={video.duration:.1f}s, "
          f"aspect={video.aspect_ratio}, audio={video.has_audio}")

    print(f"Scoring ABCD ({args.ad_type} rubric)...\n")
    results = [
        score_criterion(video, criterion_id="YT-A1", votes=3, ad_type=args.ad_type),
        score_criterion(video, criterion_id="YT-B1", ad_type=args.ad_type),
        score_criterion(video, criterion_id="YT-C1", ad_type=args.ad_type),
        score_criterion(video, criterion_id="YT-D1", ad_type=args.ad_type),
    ]
    ad_score = aggregate_scores(results, video, source=args.source, ad_type=args.ad_type)

    print(ad_score.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
