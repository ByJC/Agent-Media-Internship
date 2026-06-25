from .score import AdScore


_SCORE_COLOR = {2: "#15803D", 1: "#B45309", 0: "#B91C1C"}
_SCORE_LABEL = {2: "Strong", 1: "Partial", 0: "Weak"}
_BAND_COLOR  = {"strong": "#15803D", "adequate": "#1B44CE", "weak": "#B45309", "poor": "#B91C1C"}


def generate_report(ad_score: AdScore, output_path: str = "report.html") -> str:
    html = _build_html(ad_score)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


def _evidence_strip(evidence_items) -> str:
    if not evidence_items:
        return ""
    items_html = ""
    for ev in evidence_items:
        if ev.frame_b64:
            img_tag = (
                f'<img src="data:image/png;base64,{ev.frame_b64}" '
                f'alt="{ev.timestamp}" loading="lazy">'
            )
        else:
            img_tag = '<div class="frame-placeholder">No frame</div>'
        items_html += f"""
        <div class="frame-item">
            <div class="frame-wrap">{img_tag}</div>
            <span class="timecode">{ev.timestamp}</span>
            <p class="obs">{ev.observation}</p>
        </div>"""
    return f'<div class="evidence-strip">{items_html}</div>'


def _dimension_card(dim) -> str:
    color = _SCORE_COLOR.get(dim.raw_score, "#6B7280")
    label = _SCORE_LABEL.get(dim.raw_score, "—")
    dots = "".join(
        f'<span class="dot filled" style="background:{color}"></span>' if i < dim.raw_score
        else '<span class="dot"></span>'
        for i in range(2)
    )
    strip = _evidence_strip(dim.evidence)
    fix_html = f'<div class="fix-block"><strong>Fix:</strong> {dim.fix}</div>' if dim.fix else ""
    pct = int(dim.pct)
    return f"""
    <div class="card">
        <div class="card-header">
            <div class="criterion-label">
                <span class="criterion-letter">{dim.name[0]}</span>
                <span class="criterion-name">{dim.name}</span>
            </div>
            <div class="score-badge" style="color:{color}; border-color:{color}">
                {dots}
                <span class="score-num">{dim.raw_score}/2</span>
                <span class="score-label">{label}</span>
                <span class="score-pct">{pct}%</span>
            </div>
        </div>
        {strip}
        {fix_html}
    </div>"""


def _top_fixes(fixes: list[str]) -> str:
    if not fixes:
        return ""
    items = "".join(f'<li>{fix}</li>' for fix in fixes)
    return f"""
    <section class="fixes-section">
        <h2 class="section-title">Top Fixes — Ranked by Impact</h2>
        <ol class="fixes-list">{items}</ol>
    </section>"""


def _build_html(ad_score: AdScore) -> str:
    band_color = _BAND_COLOR.get(ad_score.band, "#6B7280")
    cards_html = "\n".join(_dimension_card(d) for d in ad_score.dimensions)
    fixes_html = _top_fixes(ad_score.top_fixes)
    short_source = ad_score.source.replace("https://www.youtube.com/watch?v=", "youtu.be/")

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ABCD Score Report</title>
<style>
  :root {{
    --ground:   #F5F4F0;
    --surface:  #FFFFFF;
    --text:     #161514;
    --muted:    #6B6660;
    --border:   #DDDBD6;
    --accent:   #1B44CE;
    --amber:    #C96B0F;
    --green:    #15803D;
    --red:      #B91C1C;
    --radius:   6px;
  }}

  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: system-ui, -apple-system, sans-serif;
    background: var(--ground);
    color: var(--text);
    font-size: 14px;
    line-height: 1.5;
    padding: 32px 24px;
  }}

  .report-wrap {{
    max-width: 960px;
    margin: 0 auto;
  }}

  /* ── Header ── */
  .report-header {{
    display: flex;
    align-items: flex-end;
    justify-content: space-between;
    padding-bottom: 20px;
    border-bottom: 2px solid var(--text);
    margin-bottom: 32px;
    gap: 24px;
  }}

  .score-hero {{
    display: flex;
    align-items: baseline;
    gap: 12px;
  }}

  .score-big {{
    font-size: 72px;
    font-weight: 800;
    line-height: 1;
    font-variant-numeric: tabular-nums;
    letter-spacing: -2px;
  }}

  .score-meta {{
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}

  .band-badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #fff;
  }}

  .score-label-text {{
    font-size: 13px;
    color: var(--muted);
  }}

  .header-right {{
    text-align: right;
  }}

  .report-title {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 4px;
  }}

  .source-url {{
    font-family: 'Menlo', 'Consolas', monospace;
    font-size: 12px;
    color: var(--accent);
    word-break: break-all;
  }}

  .ad-type-tag {{
    margin-top: 6px;
    font-size: 11px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
  }}

  /* ── Criterion grid ── */
  .grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 32px;
  }}

  @media (max-width: 640px) {{
    .grid {{ grid-template-columns: 1fr; }}
    .report-header {{ flex-direction: column; align-items: flex-start; }}
    .header-right {{ text-align: left; }}
  }}

  .card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px;
    overflow: hidden;
  }}

  .card-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 14px;
    gap: 8px;
  }}

  .criterion-label {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}

  .criterion-letter {{
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--text);
    color: var(--ground);
    font-size: 13px;
    font-weight: 800;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }}

  .criterion-name {{
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }}

  .score-badge {{
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    border: 1.5px solid;
    border-radius: 4px;
    white-space: nowrap;
    flex-shrink: 0;
  }}

  .dot {{
    width: 8px;
    height: 8px;
    border-radius: 50%;
    border: 1.5px solid currentColor;
    flex-shrink: 0;
  }}

  .dot.filled {{
    border: none;
  }}

  .score-num {{
    font-size: 13px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
  }}

  .score-label {{
    font-size: 11px;
    font-weight: 500;
    opacity: 0.8;
  }}

  .score-pct {{
    font-size: 11px;
    font-family: 'Menlo', 'Consolas', monospace;
    opacity: 0.7;
    margin-left: 2px;
  }}

  /* ── Evidence film strip ── */
  .evidence-strip {{
    display: flex;
    gap: 10px;
    overflow-x: auto;
    padding-bottom: 8px;
    margin-bottom: 12px;
    scrollbar-width: thin;
    scrollbar-color: var(--border) transparent;
  }}

  .frame-item {{
    flex-shrink: 0;
    width: 140px;
  }}

  .frame-wrap {{
    background: #161514;
    border-radius: 4px;
    overflow: hidden;
    width: 140px;
    height: 79px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 4px;
    position: relative;
  }}

  .frame-wrap img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }}

  .frame-placeholder {{
    font-size: 10px;
    color: #6B6660;
  }}

  .timecode {{
    font-family: 'Menlo', 'Consolas', monospace;
    font-size: 11px;
    font-weight: 600;
    color: var(--accent);
    display: block;
    margin-bottom: 3px;
  }}

  .obs {{
    font-size: 11px;
    color: var(--muted);
    line-height: 1.4;
  }}

  /* ── Fix block ── */
  .fix-block {{
    margin-top: 10px;
    padding: 10px 12px;
    background: #FEF3E2;
    border-left: 3px solid var(--amber);
    border-radius: 0 4px 4px 0;
    font-size: 12px;
    line-height: 1.5;
    color: #7C3A0A;
  }}

  .fix-block strong {{
    font-weight: 700;
    margin-right: 4px;
  }}

  /* ── Top fixes ── */
  .fixes-section {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 20px;
  }}

  .section-title {{
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 14px;
  }}

  .fixes-list {{
    padding-left: 18px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}

  .fixes-list li {{
    font-size: 13px;
    line-height: 1.5;
    color: var(--text);
  }}

  @media print {{
    body {{ background: #fff; padding: 16px; }}
    .card {{ break-inside: avoid; }}
  }}

  @media (prefers-reduced-motion: reduce) {{
    * {{ animation: none !important; transition: none !important; }}
  }}
</style>
</head>
<body>
<div class="report-wrap">

  <header class="report-header">
    <div class="score-hero">
      <span class="score-big" style="color:{band_color}">{ad_score.score}</span>
      <div class="score-meta">
        <span class="band-badge" style="background:{band_color}">{ad_score.band.upper()}</span>
        <span class="score-label-text">out of 100</span>
      </div>
    </div>
    <div class="header-right">
      <div class="report-title">ABCD Creative Score</div>
      <div class="source-url">{short_source}</div>
      <div class="ad-type-tag">{ad_score.ad_type.replace("_", " ")} rubric · {ad_score.duration_seconds:.0f}s</div>
    </div>
  </header>

  <div class="grid">
    {cards_html}
  </div>

  {fixes_html}

</div>
</body>
</html>"""
