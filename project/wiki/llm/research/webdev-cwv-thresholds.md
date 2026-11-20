# F015 — Chrome UX + Core Web Vitals Monitoring (Thresholds, Definitions)

Source: web.dev articles (see links below). Fetched: 2026-11-19.

Key thresholds (from web.dev):

- **INP:** good = ≤ 200 ms; improve = 200–500 ms; poor > 500 ms.
  Source: https://web.dev/articles/inp — "An INP below or at 200 milliseconds means a page has good responsiveness."
- **CLS:** good = ≤ 0.1; improve = 0.1–0.25; poor > 0.25.
  Source: https://web.dev/articles/cls — "A good threshold to measure is the 75th percentile... CLS score of 0.1 or less."
- **FCP** (web.dev/articles/fcp): good ≤ 2 s.
- **LCP**: guidance: target p75 < 2.5 s (good), Lighthouse flags at > 2500 ms commonly used as "good";
  Stability Index: < 2500 ms pass. (Compile both: script threshold = 2500.)

## Definitions

- **INP** = time from interaction start to next frame paint. Observes ALL interactions (click/tap/keypress).
  "interaction latency consists of the single longest duration of a group of event handlers that drive the interaction,
  from the time the user begins the interaction to the moment the browser is next able to paint a frame."
  (web.dev/articles/inp)
- **CLS** = max session window of layout shifts (1s gap, max 5s window). Impact fraction × distance fraction.
  (web.dev/articles/cls — "CLS is a measure of the largest burst of layout shift scores for every unexpected layout shift
  that occurs during the entire lifecycle of a page.")
- Stability Index definitions: `hadRecentInput` excluded within 500 ms.

## Also fetched

- INP: input delay + processing duration + presentation delay. 75th percentile per field.
- "best way to measure: real field data via CrUX/PSI/RUM".

## Links

- https://web.dev/articles/inp
- https://web.dev/articles/cls
- https://web.dev/articles/vitals (overview)
