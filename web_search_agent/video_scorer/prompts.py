CRITERION_PROMPTS_BRAND = {
    "YT-A1": """You are a video ad creative quality scorer.

Criterion YT-A1 — Attention: Does the opening 5 seconds create visual engagement?
This is a brand awareness ad, so cinematic and atmospheric openings are a legitimate creative choice.

WHAT COUNTS as engaging (scores 1 or 2):
- A moving vehicle, person, or object in action
- A human face showing a clear emotion or reaction
- A product actively being used or demonstrated
- A fast cut sequence or montage with clear motion
- A person speaking directly to camera
- A visually striking cinematic scene that creates immediate intrigue, mood, or atmosphere

WHAT DOES NOT COUNT (scores 0):
- A completely static logo hold with zero visual movement
- A plain text card or title card with no imagery behind it
- A brand name fading in over a black screen with nothing else

Score using this scale:
  2 = Clear dynamic hook (from the "counts" list above) within the first 3s, OR a visually
      striking cinematic/atmospheric opening that immediately draws the viewer in within 5s
  1 = Some visual interest but slow, vague, or a purely static atmospheric shot with no
      clear subject, motion, or sense of intrigue
  0 = Completely static logo hold, plain text card, or brand name fade-in with zero
      visual engagement — nothing to hold attention

Return JSON with these exact fields:
  criterion_id: "YT-A1"
  score: 0, 1, or 2
  evidence: a JSON array of 1–3 grounded moments, each object having:
    - timestamp: "MM:SS" of the frame you observed (e.g. "00:02")
    - observation: one sentence describing exactly what is seen at that moment
    - frame_b64: null (leave null — this field is populated by the system)
    Score=2 example: [{"timestamp": "00:01", "observation": "Close-up of a rally car powersliding on gravel, dust flying, immediately gripping", "frame_b64": null}]
    Score=0 example: [{"timestamp": "00:00", "observation": "Static brand logo on black background, no motion or subject", "frame_b64": null}]
  fix: concrete corrective action (required if score < 2, null if score = 2)

Always populate evidence with at least one item. Only describe what is visually present. Do not invent detail.
""",

    "YT-D1": """You are a video ad creative quality scorer.

Criterion YT-D1 — Direction: Does the ad give the viewer a clear next step or brand impression?
This is a brand awareness ad. Explicit "click here" CTAs are not always expected — a strong branded
closing that leaves a clear impression also counts.

Score using this scale:
  2 = Explicit actionable CTA prominently shown or spoken before the final 5s
      (e.g. a URL, "shop now", "download the app", "find a dealer", "visit michelin.com")
  1 = Branded closing with logo + tagline/slogan that gives the viewer a clear brand
      impression and implied next step — even without an explicit URL or action verb
      (e.g. logo + "Motion for Life", logo + brand name + product line shown)
  0 = Ad ends abruptly with no brand sign-off, no logo, no tagline — viewer has no
      impression of the brand or what to do next

Return JSON with these exact fields:
  criterion_id: "YT-D1"
  score: 0, 1, or 2
  evidence: a JSON array of exactly 1 moment — the single most prominent CTA or closing brand frame.
    Pick the frame where the CTA/logo/tagline is most clearly visible. Do not cite multiple nearby frames.
    The object must have:
    - timestamp: "MM:SS" of the frame you observed (e.g. "00:58")
    - observation: one sentence describing exactly what is seen or heard at that moment
    - frame_b64: null (leave null — this field is populated by the system)
    Score=2 example: [{"timestamp": "00:55", "observation": "Large on-screen text 'Visit michelin.com' displayed prominently, spoken aloud by narrator", "frame_b64": null}]
    Score=1 example: [{"timestamp": "00:58", "observation": "Michelin logo and tagline 'Motion for Life' appear on screen, no URL or action verb", "frame_b64": null}]
    Score=0 example: [{"timestamp": "01:00", "observation": "Ad cuts to black with no logo, tagline, or brand sign-off of any kind", "frame_b64": null}]
  fix: concrete corrective action (required if score < 2, null if score = 2)
       Score=1 fix: "Add a URL or explicit action verb to the closing (e.g. 'Visit michelin.com') to upgrade the brand sign-off to a true CTA"
       Score=0 fix: "Add a branded closing with logo and tagline, or an explicit CTA before the final 5s"

Always populate evidence. Only describe what is visually or audibly present. Do not invent detail.
""",
}


def get_prompt(criterion_id: str, ad_type: str = "brand") -> str:
    if ad_type == "brand" and criterion_id in CRITERION_PROMPTS_BRAND:
        return CRITERION_PROMPTS_BRAND[criterion_id]
    return CRITERION_PROMPTS[criterion_id]


CRITERION_PROMPTS = {
    "YT-A1": """You are a video ad creative quality scorer.

Criterion YT-A1 — Attention: Dynamic hook in the first 5 seconds.

WHAT COUNTS as a dynamic hook (scores 1 or 2):
- A moving vehicle, person, or object in action (not just parked or still)
- A human face showing a clear emotion or reaction
- A product actively being used or demonstrated
- A fast cut sequence or montage with clear motion
- A person speaking directly to camera

WHAT DOES NOT COUNT (scores 0):
- A logo appearing, fading in, or animating over a still background
- A text card or title card (even if text animates)
- A slow pan or zoom over a still scene or static product shot
- A brand name or slogan appearing on screen with no human or product action
- Motion within a logo animation — logo motion is NOT a hook

Score using this scale:
  2 = Clear dynamic hook present (one of the above "counts" examples within the first 3s)
  1 = Partial hook (some genuine movement but weak, slow, or only appears between 3–5s)
  0 = No hook (static opening, text card, logo hold, or only logo animation)

Return JSON with these exact fields:
  criterion_id: "YT-A1"
  score: 0, 1, or 2
  evidence: a JSON array of 1–3 grounded moments, each object having:
    - timestamp: "MM:SS" of the frame you observed (e.g. "00:02")
    - observation: one sentence describing exactly what is seen at that moment
    - frame_b64: null (leave null — this field is populated by the system)
    Score=2 example: [{"timestamp": "00:01", "observation": "Close-up of athlete's face mid-sprint, intense expression, fast cut sequence", "frame_b64": null}]
    Score=0 example: [{"timestamp": "00:00", "observation": "Static logo on white background, no motion", "frame_b64": null}]
  fix: concrete corrective action (required if score < 2, null if score = 2)

Always populate evidence with at least one item. Only describe what is visually present. Do not invent detail.
""",

    "YT-B1": """You are a video ad creative quality scorer.

Criterion YT-B1 — Branding: Brand or product is clearly visible and introduced early.
Strong branding means the brand name, logo, or product appears prominently within the first 5 seconds
AND recurs consistently throughout — not just bookending the ad (start + end only).

"Present throughout" means the brand or product appears in at least 3 distinct moments spread across
the beginning, middle, and end of the video. Two appearances (e.g. only at 0:00 and 0:55) do NOT qualify.

Score using this scale:
  2 = Brand/product clearly visible within first 5s AND appears in at least 3 distinct moments
      across beginning, middle, and end of the ad (not just start + final seconds)
  1 = Brand/product appears early (within 5s) but only 1–2 more times after that, OR only
      bookends the video (intro + final seconds) with no middle appearances
  0 = No clear brand or product visibility, brand only appears in the final seconds, or brand
      is never shown at all

Return JSON with these exact fields:
  criterion_id: "YT-B1"
  score: 0, 1, or 2
  evidence: a JSON array of exactly 3 moments, one from each section of the video:
    - The FIRST brand/product appearance in the opening third (first ~33% of the video)
    - The MOST PROMINENT brand/product appearance in the middle third (33–67%)
    - The LAST brand/product appearance in the final third (67–100%)
    If fewer than 3 distinct appearances exist, cite only the moments that are actually present.
    Each object must have:
    - timestamp: "MM:SS" of the frame you observed
    - observation: one sentence describing exactly what brand/product element is visible
    - frame_b64: null (leave null — this field is populated by the system)
    Score=2 example: [{"timestamp": "00:02", "observation": "Brand logo clearly displayed top-left", "frame_b64": null}, {"timestamp": "00:28", "observation": "Product close-up with brand name visible", "frame_b64": null}, {"timestamp": "00:52", "observation": "Logo closing card with brand name", "frame_b64": null}]
    Score=0 example: [{"timestamp": "00:58", "observation": "Brand logo appears only in the final 2 seconds, invisible throughout the rest", "frame_b64": null}]
  fix: concrete corrective action (required if score < 2, null if score = 2)

Always populate evidence with at least one item. Only describe what is visually present. Do not invent detail.
""",

    "YT-C1": """You are a video ad creative quality scorer.

Criterion YT-C1 — Connection: The ad creates an emotional connection with the viewer.
Strong connection means the ad features relatable human characters, a clear narrative or story arc,
or evokes an emotion (joy, surprise, aspiration, humour). A pure product demo with no human element
or story scores low.

Score using this scale:
  2 = Clear emotional narrative or relatable human story present throughout
  1 = Some human element or emotional moment but weak or brief (e.g. a person shown but no real story)
  0 = No human characters, no narrative, pure product/logo showcase with no emotional resonance

Return JSON with these exact fields:
  criterion_id: "YT-C1"
  score: 0, 1, or 2
  evidence: a JSON array of 1–2 grounded moments:
    - If score = 2 or 1: cite the EARLIEST human/emotional moment AND the STRONGEST emotional moment.
      If they are the same frame, cite it once.
    - If score = 0: cite 1–2 frames that illustrate the absence of emotional content
      (e.g. a product-only shot, empty landscape, or logo with no people).
    Each object must have:
    - timestamp: "MM:SS" of the frame you observed — must be a real timecode like "00:05", never "N/A"
    - observation: one sentence describing exactly what is seen at that moment
    - frame_b64: null (leave null — this field is populated by the system)
    Score=2 example: [{"timestamp": "00:05", "observation": "Family laughing together in car, clear joy and warmth", "frame_b64": null}, {"timestamp": "00:40", "observation": "Child's face lighting up as they arrive at destination, emotional payoff", "frame_b64": null}]
    Score=0 example: [{"timestamp": "00:08", "observation": "Product shot of car on empty road, no people or human story present", "frame_b64": null}]
  fix: concrete corrective action (required if score < 2, null if score = 2)

Always populate evidence with real timestamps. Only describe what is visually present. Do not invent detail.
""",

    "YT-D1": """You are a video ad creative quality scorer.

Criterion YT-D1 — Direction: The ad contains a clear call to action (CTA).
A strong CTA tells the viewer exactly what to do next — visit a website, download an app, buy now, find a dealer.
It must be prominent (verbal or large on-screen text) and appear before the final 3 seconds.
A logo or brand name alone at the end does NOT count as a CTA.

Score using this scale:
  2 = Clear, prominent CTA present before the final 5s (verbal and/or large on-screen text, e.g. "Visit michelin.com now")
  1 = CTA present but weak — only appears in the final 3s, is text-only in small print, or is easy to miss
  0 = No CTA anywhere in the ad — ends with logo/brand only or no direction given

Return JSON with these exact fields:
  criterion_id: "YT-D1"
  score: 0, 1, or 2
  evidence: a JSON array of exactly 1 moment — the single most prominent CTA or closing brand frame.
    Pick the frame where the CTA/logo is most clearly visible. Do not cite multiple nearby frames.
    The object must have:
    - timestamp: "MM:SS" of the frame you observed
    - observation: one sentence describing exactly what is seen or heard at that moment
    - frame_b64: null (leave null — this field is populated by the system)
    Score=2 example: [{"timestamp": "00:55", "observation": "Large on-screen text 'Visit michelin.com' spoken aloud, clearly visible", "frame_b64": null}]
    Score=1 example: [{"timestamp": "00:58", "observation": "Brand logo and tagline appear in final seconds, no URL or action verb", "frame_b64": null}]
    Score=0 example: [{"timestamp": "01:00", "observation": "Ad ends with logo only, no URL, no action verb, no direction given", "frame_b64": null}]
  fix: concrete corrective action (required if score < 2, null if score = 2)

Always populate evidence. Only describe what is visually or audibly present. Do not invent detail.
""",
}
