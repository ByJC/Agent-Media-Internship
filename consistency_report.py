"""
Full consistency report: 5 videos × 3 runs.
Checks score stability AND evidence stability (same timestamps cited?).
Outputs terminal summary + report.html
"""
import time
from dotenv import load_dotenv
load_dotenv()

from web_search_agent.video_scorer import ingest_video, score_criterion, aggregate_scores


def _score_with_retry(video, criterion_id, votes, ad_type, max_retries=5, delay=30):
    for attempt in range(max_retries):
        try:
            return score_criterion(video, criterion_id=criterion_id, votes=votes, ad_type=ad_type)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"\n    [API error, retry {attempt+1}/{max_retries-1}, waiting {delay}s...]", end=" ", flush=True)
                time.sleep(delay)
            else:
                raise

URLS = [
    "https://www.youtube.com/watch?v=oQNhp46Y0Fg",
    "https://www.youtube.com/watch?v=PBrYMBacnyM",
    "https://www.youtube.com/watch?v=-8UPg6hyDBg",
    "https://www.youtube.com/watch?v=p-_qNvWqtXU",
    "https://www.youtube.com/watch?v=XZerw7F7yl0",
]

CRITERIA   = ["YT-A1", "YT-B1", "YT-C1", "YT-D1",
              "YT-E1-CONTENT", "YT-E1-CONTROVERSY", "YT-E1-COMPETITOR", "YT-E1-CLAIMS"]
LABELS     = {"YT-A1": "A-Attention", "YT-B1": "B-Branding",
              "YT-C1": "C-Connection", "YT-D1": "D-Direction",
              "YT-E1-CONTENT": "E-Content", "YT-E1-CONTROVERSY": "E-Controversy",
              "YT-E1-COMPETITOR": "E-Competitor", "YT-E1-CLAIMS": "E-Claims"}
RUNS       = 3
AD_TYPE    = "brand"


# ── data collection ───────────────────────────────────────────────────────────

def collect():
    """Returns list of per-video dicts with scores + evidence per run."""
    results = []
    for v_idx, url in enumerate(URLS, 1):
        print(f"\nVideo {v_idx}: {url}")
        print("  Ingesting...")
        video = ingest_video(url, sample_fps=1.0)
        print(f"  {len(video.frames)} frames, {video.duration:.0f}s")

        video_data = {"url": url, "runs": []}

        for run in range(1, RUNS + 1):
            print(f"  Run {run}/{RUNS}...", end=" ", flush=True)
            crit_results = [
                _score_with_retry(video, criterion_id="YT-A1", votes=3, ad_type=AD_TYPE),
                _score_with_retry(video, criterion_id="YT-B1", votes=3, ad_type=AD_TYPE),
                _score_with_retry(video, criterion_id="YT-C1", votes=3, ad_type=AD_TYPE),
                _score_with_retry(video, criterion_id="YT-D1", votes=3, ad_type=AD_TYPE),
            ]
            safety_results = [
                _score_with_retry(video, criterion_id="YT-E1-CONTENT",     votes=3, ad_type=AD_TYPE),
                _score_with_retry(video, criterion_id="YT-E1-CONTROVERSY", votes=3, ad_type=AD_TYPE),
                _score_with_retry(video, criterion_id="YT-E1-COMPETITOR",  votes=3, ad_type=AD_TYPE),
                _score_with_retry(video, criterion_id="YT-E1-CLAIMS",      votes=3, ad_type=AD_TYPE),
            ]
            ad_score = aggregate_scores(crit_results, video, source=url, ad_type=AD_TYPE)
            print(f"overall={ad_score.score}")

            run_data = {"overall": ad_score.score, "criteria": {}}
            for r in crit_results + safety_results:
                run_data["criteria"][r.criterion_id] = {
                    "score": r.score,
                    "timestamps": [ev.timestamp for ev in r.evidence],
                    "observations": [ev.observation for ev in r.evidence],
                }
            video_data["runs"].append(run_data)

        results.append(video_data)
    return results


# ── analysis ──────────────────────────────────────────────────────────────────

def _ts_to_sec(ts: str) -> int:
    parts = ts.split(":")
    return int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else int(parts[0])

def is_score_stable(video_data, cid):
    scores = [run["criteria"][cid]["score"] for run in video_data["runs"]]
    return len(set(scores)) == 1

def is_evidence_stable(video_data, cid, tolerance: int = 2):
    """Timestamps within ±tolerance seconds are treated as the same moment."""
    def fuzzy_set(timestamps):
        return frozenset((_ts_to_sec(ts) // tolerance) * tolerance for ts in timestamps)
    ts_sets = [fuzzy_set(run["criteria"][cid]["timestamps"]) for run in video_data["runs"]]
    return all(s == ts_sets[0] for s in ts_sets[1:])

def stable_icon(val):
    return "✅" if val else "❌"


# ── terminal summary ──────────────────────────────────────────────────────────

def print_summary(all_results):
    print("\n" + "═" * 100)
    print("CONSISTENCY REPORT — Scores + Evidence")
    print("═" * 100)

    header = f"  {'Video':<6} {'Criterion':<16} {'R1':>4} {'R2':>4} {'R3':>4}  {'Score':>7}  {'R1 Timestamps':<20} {'R2 Timestamps':<20} {'R3 Timestamps':<20}  {'Evidence':>9}"
    print(header)
    print("  " + "─" * (len(header) - 2))

    score_stab  = {cid: 0 for cid in CRITERIA}
    evid_stab   = {cid: 0 for cid in CRITERIA}

    for v_idx, vd in enumerate(all_results, 1):
        overalls = [r["overall"] for r in vd["runs"]]
        for cid in CRITERIA:
            scores = [r["criteria"][cid]["score"] for r in vd["runs"]]
            ts     = [", ".join(r["criteria"][cid]["timestamps"]) or "—" for r in vd["runs"]]
            ss = is_score_stable(vd, cid)
            es = is_evidence_stable(vd, cid)
            if ss: score_stab[cid] += 1
            if es: evid_stab[cid]  += 1
            print(f"  V{v_idx:<5} {LABELS[cid]:<16} {scores[0]:>4} {scores[1]:>4} {scores[2]:>4}  {stable_icon(ss):>7}  {ts[0]:<20} {ts[1]:<20} {ts[2]:<20}  {stable_icon(es):>9}")

        print(f"  {'':6} {'Overall':<16} {overalls[0]:>4.1f} {overalls[1]:>4.1f} {overalls[2]:>4.1f}")
        print()

    n = len(URLS)
    print("─" * 60)
    print(f"SUMMARY ({n} videos × {RUNS} runs)")
    print("─" * 60)
    print(f"  {'Criterion':<16} {'Score stable':>14}  {'Evidence stable':>16}")
    for cid in CRITERIA:
        sp = int(score_stab[cid] / n * 100)
        ep = int(evid_stab[cid]  / n * 100)
        print(f"  {LABELS[cid]:<16} {score_stab[cid]}/{n}  ({sp:>3}%)       {evid_stab[cid]}/{n}  ({ep:>3}%)")


# ── HTML report ───────────────────────────────────────────────────────────────

SCORE_COLOR = {2: "#15803D", 1: "#B45309", 0: "#B91C1C"}

def _score_cell(score):
    c = SCORE_COLOR.get(score, "#6B7280")
    return f'<td style="color:{c};font-weight:700;text-align:center">{score}</td>'

def _ts_cell(ts_list):
    if not ts_list:
        return '<td class="muted">—</td>'
    chips = "".join(f'<span class="ts-chip">{t}</span>' for t in ts_list)
    return f'<td>{chips}</td>'

def _stable_cell(val):
    icon = "✅" if val else "❌"
    bg   = "#F0FDF4" if val else "#FEF2F2"
    return f'<td style="background:{bg};text-align:center">{icon}</td>'

def _obs_rows(all_results):
    rows = ""
    for v_idx, vd in enumerate(all_results, 1):
        for cid in CRITERIA:
            for run_idx, run in enumerate(vd["runs"], 1):
                obs_list = run["criteria"][cid]["observations"]
                ts_list  = run["criteria"][cid]["timestamps"]
                for ts, obs in zip(ts_list, obs_list):
                    rows += f"""
                    <tr>
                        <td class="muted">V{v_idx}</td>
                        <td>{LABELS[cid]}</td>
                        <td class="muted" style="text-align:center">Run {run_idx}</td>
                        <td><span class="ts-chip">{ts}</span></td>
                        <td>{obs}</td>
                    </tr>"""
    return rows

def generate_html_report(all_results, output_path="consistency_report.html"):
    score_stab = {cid: 0 for cid in CRITERIA}
    evid_stab  = {cid: 0 for cid in CRITERIA}
    n = len(all_results)

    main_rows = ""
    for v_idx, vd in enumerate(all_results, 1):
        overalls = [r["overall"] for r in vd["runs"]]
        first_cid = True
        for cid in CRITERIA:
            scores = [r["criteria"][cid]["score"] for r in vd["runs"]]
            ts     = [r["criteria"][cid]["timestamps"] for r in vd["runs"]]
            ss = is_score_stable(vd, cid)
            es = is_evidence_stable(vd, cid)
            if ss: score_stab[cid] += 1
            if es: evid_stab[cid]  += 1

            v_cell = f'<td rowspan="8" class="video-cell">V{v_idx}<div class="video-url">{vd["url"].replace("https://www.youtube.com/watch?v=","")}</div></td>' if first_cid else ""
            first_cid = False

            main_rows += f"""
            <tr>
                {v_cell}
                <td class="criterion-cell">{LABELS[cid]}</td>
                {_score_cell(scores[0])}
                {_score_cell(scores[1])}
                {_score_cell(scores[2])}
                {_stable_cell(ss)}
                {_ts_cell(ts[0])}
                {_ts_cell(ts[1])}
                {_ts_cell(ts[2])}
                {_stable_cell(es)}
            </tr>"""

        main_rows += f"""
        <tr class="overall-row">
            <td class="criterion-cell muted">Overall</td>
            <td colspan="3" style="text-align:center;font-variant-numeric:tabular-nums">
                {overalls[0]:.1f} / {overalls[1]:.1f} / {overalls[2]:.1f}
            </td>
            <td></td><td colspan="3"></td><td></td>
        </tr>
        <tr class="spacer-row"><td colspan="10"></td></tr>"""

    summary_rows = ""
    for cid in CRITERIA:
        sp = int(score_stab[cid] / n * 100)
        ep = int(evid_stab[cid]  / n * 100)
        sc = "#15803D" if sp == 100 else "#B45309" if sp >= 60 else "#B91C1C"
        ec = "#15803D" if ep == 100 else "#B45309" if ep >= 60 else "#B91C1C"
        summary_rows += f"""
        <tr>
            <td>{LABELS[cid]}</td>
            <td style="color:{sc};font-weight:700;text-align:center">{score_stab[cid]}/{n} ({sp}%)</td>
            <td style="color:{ec};font-weight:700;text-align:center">{evid_stab[cid]}/{n} ({ep}%)</td>
        </tr>"""

    obs_rows = _obs_rows(all_results)

    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ABCDE Consistency Report</title>
<style>
  :root {{
    --ground: #F5F4F0; --surface: #fff; --text: #161514;
    --muted: #6B6660; --border: #DDDBD6; --accent: #1B44CE;
  }}
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: system-ui, -apple-system, sans-serif; background: var(--ground);
         color: var(--text); font-size: 13px; line-height: 1.5; padding: 32px 24px; }}
  .wrap {{ max-width: 1200px; margin: 0 auto; }}
  h1 {{ font-size: 22px; font-weight: 800; margin-bottom: 4px; }}
  .subtitle {{ font-size: 13px; color: var(--muted); margin-bottom: 32px; }}
  h2 {{ font-size: 11px; font-weight: 700; letter-spacing: .1em; text-transform: uppercase;
        color: var(--muted); margin: 32px 0 12px; }}
  .table-wrap {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; background: var(--surface);
           border: 1px solid var(--border); border-radius: 6px; overflow: hidden; }}
  th {{ background: #161514; color: #F5F4F0; font-size: 11px; font-weight: 700;
        letter-spacing: .06em; text-transform: uppercase; padding: 10px 12px;
        text-align: left; white-space: nowrap; }}
  td {{ padding: 8px 12px; border-bottom: 1px solid var(--border); vertical-align: top; }}
  .muted {{ color: var(--muted); }}
  .video-cell {{ font-weight: 700; font-size: 14px; vertical-align: middle;
                 border-right: 2px solid var(--border); white-space: nowrap; }}
  .video-url {{ font-family: monospace; font-size: 10px; color: var(--accent);
                font-weight: 400; margin-top: 2px; }}
  .criterion-cell {{ font-weight: 600; white-space: nowrap; }}
  .overall-row td {{ background: #F9F8F5; font-weight: 600; color: var(--muted); font-size: 12px; }}
  .spacer-row td {{ height: 8px; background: var(--ground); border: none; padding: 0; }}
  .ts-chip {{ display: inline-block; background: #EBF0FD; color: var(--accent);
              font-family: monospace; font-size: 11px; font-weight: 600;
              padding: 1px 6px; border-radius: 3px; margin: 1px 2px 1px 0; white-space: nowrap; }}
</style>
</head>
<body>
<div class="wrap">

  <h1>ABCDE Consistency Report</h1>
  <p class="subtitle">{n} videos × {RUNS} runs — brand rubric — score stability + evidence stability</p>

  <h2>Main Results</h2>
  <div class="table-wrap">
  <table>
    <thead>
      <tr>
        <th>Video</th>
        <th>Criterion</th>
        <th>R1 Score</th><th>R2 Score</th><th>R3 Score</th>
        <th>Score ✓</th>
        <th>R1 Timestamps</th><th>R2 Timestamps</th><th>R3 Timestamps</th>
        <th>Evidence ✓</th>
      </tr>
    </thead>
    <tbody>{main_rows}</tbody>
  </table>
  </div>

  <h2>Summary</h2>
  <div class="table-wrap">
  <table>
    <thead>
      <tr><th>Criterion</th><th>Score Stability</th><th>Evidence Stability</th></tr>
    </thead>
    <tbody>{summary_rows}</tbody>
  </table>
  </div>

  <h2>Evidence Observations (all runs)</h2>
  <div class="table-wrap">
  <table>
    <thead>
      <tr><th>Video</th><th>Criterion</th><th>Run</th><th>Timestamp</th><th>Observation</th></tr>
    </thead>
    <tbody>{obs_rows}</tbody>
  </table>
  </div>

</div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    all_results = collect()
    print_summary(all_results)
    path = generate_html_report(all_results)
    print(f"\nHTML report saved → {path}")
