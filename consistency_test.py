from dotenv import load_dotenv
load_dotenv()

from web_search_agent.video_scorer import ingest_video, score_criterion, aggregate_scores

URLS = [
    "https://www.youtube.com/watch?v=oQNhp46Y0Fg",
    "https://www.youtube.com/watch?v=PBrYMBacnyM",
    "https://www.youtube.com/watch?v=-8UPg6hyDBg",
    "https://www.youtube.com/watch?v=p-_qNvWqtXU",
    "https://www.youtube.com/watch?v=XZerw7F7yl0",
]

CRITERIA = ["YT-A1", "YT-B1", "YT-C1", "YT-D1"]
LABELS   = {"YT-A1": "A-Attention", "YT-B1": "B-Branding",
            "YT-C1": "C-Connection", "YT-D1": "D-Direction"}
RUNS = 3


def run_consistency_test():
    # stability_counts[cid] = number of videos where criterion was stable
    stability_counts = {cid: 0 for cid in CRITERIA}

    for video_idx, url in enumerate(URLS, 1):
        print(f"\nVideo {video_idx}: {url}")
        print("  Ingesting (download once)...")
        video = ingest_video(url, sample_fps=1.0)
        print(f"  Ingested: {len(video.frames)} frames, {video.duration:.0f}s")

        # scores[cid] = [score_run1, score_run2, score_run3]
        scores = {cid: [] for cid in CRITERIA}
        overall_scores = []

        for run in range(1, RUNS + 1):
            print(f"  Run {run}/{RUNS}...", end=" ", flush=True)
            results = [score_criterion(video, criterion_id=cid) for cid in CRITERIA]
            ad_score = aggregate_scores(results, video, source=url)
            for r in results:
                scores[r.criterion_id].append(r.score)
            overall_scores.append(ad_score.score)
            print(f"overall={ad_score.score}")

        # Print table
        print()
        header = f"  {'Criterion':<16} {'Run1':>5} {'Run2':>5} {'Run3':>5}  {'Stable?':>8}"
        print(header)
        print("  " + "-" * (len(header) - 2))
        for cid in CRITERIA:
            runs = scores[cid]
            stable = "✅" if len(set(runs)) == 1 else "❌"
            if len(set(runs)) == 1:
                stability_counts[cid] += 1
            print(f"  {LABELS[cid]:<16} {runs[0]:>5} {runs[1]:>5} {runs[2]:>5}  {stable:>8}")
        print(f"  {'Overall':<16} {overall_scores[0]:>5.1f} {overall_scores[1]:>5.1f} {overall_scores[2]:>5.1f}")

    # Summary
    n = len(URLS)
    print(f"\n{'─'*55}")
    print(f"SUMMARY ({n} videos × {RUNS} runs)")
    print(f"{'─'*55}")
    for cid in CRITERIA:
        count = stability_counts[cid]
        pct = int(count / n * 100)
        bar = "█" * count + "░" * (n - count)
        print(f"  {LABELS[cid]:<16} stable in {count}/{n} videos  ({pct:>3}%)  {bar}")


if __name__ == "__main__":
    run_consistency_test()
