#!/usr/bin/env python3
"""
f015_chromex.py — F015: Chrome UX + Core Web Vitals Monitoring on Cloudflare Pages.

Стратегия:
  - remote: PageSpeed Insights (PSI) API — реальные LCP/CLS/FCP/INP/TTFB,
    числа, которые можно проверять в тестах (а не парсить строки из логов).
  - analyze: Lighthouse через npx lighthouse — фулл-ран Web.dev metrics.
  Пороги (Stability Index, как в остальных модулях):
    LCP < 2500ms, CLS < 0.1, FCP < 2000ms, INP < 200ms, TTFB < 1800ms
  Отчёт: docs/reports/f015-<yyyymmdd>.md / f015-psi-<yyyymmdd>.md
"""

import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"
REPORT_DIR = PROJECT_ROOT / "docs" / "reports"

# Thresholds (worse = fail)
THRESHOLDS = {
    "LCP": 2500,     # ms (Stability Index guidance: 2500)
    "CLS": 0.1,      # (Stability Index guidance: 0.1)
    "FCP": 2000,     # ms
    "INP": 200,      # ms
    "TTFB": 1800,    # ms
}


def parse_psi_metrics(data: dict) -> dict:
    """Извлекает числовые метрики из PSI response. Все 0 если нет данных."""
    audits = data.get("lighthouseResult", {}).get("audits", {})

    def num(name):
        v = audits.get(name, {}).get("numericValue")
        return v if isinstance(v, (int, float)) else 0

    lcp = num("largest-contentful-paint")
    cls = audits.get("cumulative-layout-shift-semantic", {}).get("numericValue")
    if not isinstance(cls, (int, float)):
        cls = num("cumulative-layout-shift")
    inp = num("interaction-to-next-paint") or num("inp")

    return {
        "LCP": round(lcp, 1),
        "CLS": round(cls, 4),
        "FCP": round(num("first-contentful-paint"), 1),
        "INP": round(inp, 1),
        "TTFB": round(num("server-response-time"), 1),
    }


def run_psi(url: str, strategy: str = "mobile", retries: int = 3) -> dict:
    """PSI v5 — прямой вызов с retry при 429/5xx."""
    psi_url = (
        f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        f"?url={url}&strategy={strategy}"
    )
    for i in range(retries):
        try:
            with urllib.request.urlopen(psi_url, timeout=45) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and i < retries - 1:
                time.sleep(1.5 * (i + 1))
                continue
            return {"error": str(e)[:300]}
        except Exception as e:
            return {"error": str(e)[:300]}
    return {"error": "PSI failed"}


def run_lighthouse(url: str, budget: int = 30000) -> dict:
    """Lighthouse через npx lighthouse — если недоступен, результат ошибки."""
    import subprocess
    cmd = [
        "npx", "--yes", "lighthouse",
        f"--max-wait-for-load={budget}", "--output=json", "--quiet",
        url,
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    except Exception as e:
        return {"error": f"Lighthouse unavailable: {e}"}
    if r.returncode == 0 and r.stdout:
        try:
            data = json.loads(r.stdout)
            audits = data.get("audits", {})
            return {
                "LCP": (audits.get("largest-contentful-paint", {}).get("numericValue") or 0),
                "CLS": (audits.get("cumulative-layout-shift", {}).get("numericValue") or 0),
                "FCP": (audits.get("first-contentful-paint", {}).get("numericValue") or 0),
                "INP": (audits.get("interaction-to-next-paint", {}).get("numericValue")
                        or audits.get("inp", {}).get("numericValue") or 0),
                "TTFB": (audits.get("server-response-time", {}).get("numericValue") or 0),
            }
        except Exception:
            pass
    return {"error": (r.stderr or r.stdout or "lighthouse failed")[:300]}


def threshold_rows(url: str, metrics: dict) -> list[str]:
    """Проверка каждой метрики против порогов. Returns [(metric, actual, ok)]."""
    rows = []
    for metric, thr in THRESHOLDS.items():
        actual = metrics.get(metric, 0)
        unit = "ms" if metric in ("LCP", "FCP", "INP", "TTFB") else ""
        ok = actual < thr
        rows.append((metric, actual, ok, thr, unit))
    return rows


def write_psi_report(results: list[dict]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    t = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = REPORT_DIR / f"f015-psi-{t}.md"
    lines = [
        f"# F015 (PSI) — Core Web Vitals Dashboard — {t}",
        "",
        "| Page | LCP | CLS | FCP | INP | TTFB | All stable |",
        "|------|-----|-----|-----|-----|------|------------|",
    ]
    for r in results:
        m = r["metrics"]
        stable = all(v < THRESHOLDS[k] for k, v in m.items())
        lines.append(
            f"| {r['url']} | {m['LCP']} | {m['CLS']} | {m['FCP']} | "
            f"{m['INP']} | {m['TTFB']} | {'✅' if stable else '⚠️'} |"
        )
    lines += ["", "Thresholds: LCP < 2500ms, CLS < 0.1, FCP < 2000ms, INP < 200ms, TTFB < 1800ms"]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_lighthouse_report(results: list[dict]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    t = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = REPORT_DIR / f"f015-{t}.md"
    lines = [f"# F015 — Chrome UX + CWV — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}", ""]
    for r in results:
        lines += [
            f"- URL: {r['url']}",
            f"  - LCP: {r['metrics']['LCP']}ms",
            f"  - CLS: {r['metrics']['CLS']}",
            f"  - FCP: {r['metrics']['FCP']}ms",
            f"  - INP: {r['metrics']['INP']}ms",
            f"  - TTFB: {r['metrics']['TTFB']}ms",
        ]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def cmd_remote(args) -> int:
    """PSI для каждого URL — реальные метрики (network required)."""
    print("=== F015 Remote (PSI) — Core Web Vitals dashboard ===")
    results = []
    for url in args.page:
        data = run_psi(url, strategy=args.device)
        if "error" in data:
            print(f"  {url}: ERROR — {data['error']}")
            continue
        metrics = parse_psi_metrics(data)
        results.append({"url": url, "metrics": metrics})
        m = metrics
        print(f"  {url}: LCP={m['LCP']} CLS={m['CLS']} FCP={m['FCP']} "
              f"INP={m['INP']} TTFB={m['TTFB']}")

    if results:
        report = write_psi_report(results)
        print(f"Report: {report.relative_to(PROJECT_ROOT)}")
    return 0 if results else 2


def cmd_analyze(args) -> int:
    """Lighthouse — фулл-ран Web.dev metrics для страниц."""
    print("=== F015: Chrome UX + CWV Analysis (Lighthouse) ===")
    results = []
    errored = False
    for url in args.page:
        data = run_lighthouse(url, budget=args.budget_ms)
        if "error" in data:
            errored = True
            print(f"  {url}: Lighthouse error — {data['error']}")
            continue
        metrics = {
            "LCP": data.get("LCP", 0),
            "CLS": data.get("CLS", 0),
            "FCP": data.get("FCP", 0),
            "INP": data.get("INP", 0),
            "TTFB": data.get("TTFB", 0),
        }
        results.append({"url": url, "metrics": metrics})
        m = metrics
        stable = all(v < THRESHOLDS[k] for k, v in m.items())
        print(f"  {url}: LCP={m['LCP']} CLS={m['CLS']} FCP={m['FCP']} "
              f"INP={m['INP']} TTFB={m['TTFB']} stable={stable}")

    if errored or not results:
        return 2
    if results:
        report = write_lighthouse_report(results)
        print(f"Report: {report.relative_to(PROJECT_ROOT)}")
    return 0 if results else 1


def main():
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p1 = sub.add_parser("analyze", help="Lighthouse metrics (Network or Local)")
    p1.add_argument("--page", nargs="+", default=["http://localhost:3000/"])
    p1.add_argument("--budget-ms", type=int, default=30000)
    p1.add_argument("--timeout-s", type=int, default=180,
                    help="accepted for compatibility, lighthouse uses --max-wait-for-load")

    p2 = sub.add_parser("remote", help="PSI — real Core Web Vitals (network)")
    p2.add_argument("--page", nargs="+", default=["http://localhost:3000/"])
    p2.add_argument("--device", default="mobile")

    args = ap.parse_args()
    if args.cmd == "analyze":
        return cmd_analyze(args)
    if args.cmd == "remote":
        return cmd_remote(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
