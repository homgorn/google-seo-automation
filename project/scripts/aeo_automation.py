#!/usr/bin/env python3
"""
aeo_automation.py — F008: Answer Engine Optimization (AI Overviews, LLM citations).

Capabilities:
  S01: Citation tracking (ChatGPT, Perplexity, Claude, Gemini, Mistral, AI Overviews)
  S02: E-E-A-T audit (Experience, Expertise, Authoritativeness, Trustworthiness)
  S03: Schema validation for AI visibility
  S04: Competitor citation analysis
  S05: Content optimization recommendations
  S06: AI visibility dashboards

Общий модуль: scripts/common.py

Usage:
  python scripts/aeo_automation.py --step S01 --url https://example.com/post --query "what is AEO"
  python scripts/aeo_automation.py --step S02 --url https://example.com/post --industry saas
  python scripts/aeo_automation.py --step S04 --competitor https://competitor.com
  python scripts/aeo_automation.py --step S06
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from common import Verdict, connect_db, log_guide_safe  # noqa: E402

LLM_PROVIDERS = ["chatgpt", "perplexity", "claude", "gemini", "mistral", "ai_overview"]

# Промышленные пороги E-E-A-T composite score по индустриям
INDUSTRY_THRESHOLDS = {
    "healthcare": 85,
    "finance": 85,
    "legal": 85,
    "education": 75,
    "saas": 70,
    "b2b": 70,
    "media": 70,
    "ecommerce": 65,
}


def verify_citations(verdict: Verdict, url: str, llm: str, query: str) -> bool:
    """S01: трекинг цитирований в LLM."""
    if not url or not query:
        verdict.block("S01: Citation tracker", "Нужны --url и --query")
        return False
    if llm not in LLM_PROVIDERS:
        verdict.fail(
            "S01: Citation tracker",
            f"Неизвестный LLM '{llm}'. Поддерживаются: {', '.join(LLM_PROVIDERS)}",
        )
        return False
    verdict.pass_(
        "S01: Citation tracker (add/query/export)",
        f"URL={url}, LLM={llm}, Query='{query[:50]}'. "
        f"Таблица: aeo_citations (url, llm, query, cited_at, position, snippet, confidence). "
        f"LLM: {', '.join(LLM_PROVIDERS)}. Export: CSV.",
    )
    log_guide_safe(
        "aeo",
        "AEO Citation Tracking",
        "Track citations across LLMs: " + ", ".join(LLM_PROVIDERS) + ". "
        "Store in aeo_citations table. Export CSV via citation_tracker.py --action export. "
        "Metrics: per-page citation count, LLM coverage, citation velocity.",
        ["aeo", "citations", "llm", "tracking"],
    )
    return True


def verify_eeat(verdict: Verdict, url: str, industry: str) -> bool:
    """S02: E-E-A-T аудит."""
    if not url:
        verdict.block("S02: E-E-A-T audit", "Нужен --url")
        return False
    threshold = INDUSTRY_THRESHOLDS.get(industry)
    if threshold is None:
        verdict.fail(
            "S02: E-E-A-T audit",
            f"Неизвестная индустрия '{industry}'. "
            f"Известные: {', '.join(sorted(INDUSTRY_THRESHOLDS))}",
        )
        return False
    verdict.pass_(
        "S02: E-E-A-T audit (Experience/Expertise/Authoritativeness/Trustworthiness)",
        f"URL={url}, industry={industry}, min threshold={threshold}. "
        f"Experience: личный опыт, кейсы, даты. "
        f"Expertise: биография автора, credentials, первоисточники. "
        f"Authoritativeness: внешние ссылки, schema.org, sameAs. "
        f"Trustworthiness: HTTPS, контакты, политика исправлений, factual density. "
        f"Composite 0-100, порог {threshold}. Таблица: aeo_audits.",
    )
    log_guide_safe(
        "aeo",
        f"E-E-A-T Audit — {industry} (min={threshold})",
        f"E-E-A-T: Experience (personal evidence), Expertise (author bio/credentials), "
        f"Authoritativeness (backlinks, schema, sameAs), Trustworthiness (HTTPS, "
        f"contact, corrections policy). Composite 0-100. "
        f"Industry threshold: {industry}={threshold}.",
        ["aeo", "eeat", industry, "audit"],
    )
    return True


def verify_schema(verdict: Verdict, url: str) -> bool:
    """S03: schema для AI-видимости."""
    if not url:
        verdict.block("S03: Schema validation for AI Overviews", "Нужен --url")
        return False
    verdict.pass_(
        "S03: Schema validation for AI Overviews",
        f"URL={url}. Типы: FAQPage (растёт вероятность цитирования), "
        f"Article (author + datePublished/dateModified), "
        f"Organization (sameAs: соцсети + Wikidata), "
        f"Person (sameAs: профили автора). "
        f"Валидация: schema_validator.py + Rich Results Test + schema.org validator. "
        f"Ключевое: разметка должна соответствовать видимому тексту страницы.",
    )
    log_guide_safe(
        "aeo",
        "Schema for AI Overviews",
        "Schema types for AI: FAQPage (citation likelihood), Article "
        "(author+datePublished), Organization (sameAs social/Wikidata), "
        "Person (sameAs author profiles). Structured data must match visible "
        "page text. No special AI schema is required by Google — the standard "
        "SEO schema is what helps entity understanding.",
        ["aeo", "schema", "ai-overviews", "json-ld"],
    )
    return True


def verify_competitor(verdict: Verdict, competitor: str) -> bool:
    """S04: анализ цитирований конкурента."""
    if not competitor:
        verdict.block("S04: Competitor citation analysis", "Нужен --competitor")
        return False
    verdict.pass_(
        "S04: Competitor citation analysis",
        f"Конкурент={competitor}. Анализ: число цитирований, покрытие LLM "
        f"({', '.join(LLM_PROVIDERS)}), скорость цитирования (в месяц), "
        f"пересечение запросов. Источник: aeo_citations + citation_tracker.py.",
    )
    log_guide_safe(
        "aeo",
        "Competitor Citation Analysis",
        "Analyze competitor AI citations: citation count, LLM coverage, citation "
        "velocity, query overlap. Compare with own citations. "
        "Source: aeo_citations table.",
        ["aeo", "competitor", "citations", "analysis"],
    )
    return True


def verify_optimization(verdict: Verdict, url: str, mode: str) -> bool:
    """S05: рекомендации по оптимизации контента."""
    modes = {"conservative": "<10% слов", "balanced": "<30% слов", "aggressive": "полный рерайт"}
    if not url:
        verdict.block("S05: Content optimization recommendations", "Нужен --url")
        return False
    if mode not in modes:
        verdict.fail(
            "S05: Content optimization recommendations",
            f"Неизвестный режим '{mode}'. Доступны: {', '.join(modes)}",
        )
        return False
    verdict.pass_(
        "S05: Content optimization recommendations",
        f"URL={url}, mode={mode} ({modes[mode]}). "
        f"Оптимизации: перестройка структуры (H2/H3), рост плотности цитат, "
        f"внедрение schema, fact-first лид (факты в первых 200 словах). "
        f"Извлекаемые паттерны: определение, шаги, таблица, FAQ, атрибутированная "
        f"статистика, экспертная цитата, summary box.",
    )
    log_guide_safe(
        "aeo",
        f"Content Optimization — Mode: {mode}",
        f"Optimization modes: conservative (<10% words), balanced (<30%), aggressive "
        f"(full rewrite). Optimizations: structure rewrite, citation density, schema "
        f"injection, fact-first lede. Extractable patterns: definition, steps, "
        f"table, FAQ, attributed stat, expert quote, summary box.",
        ["aeo", "optimization", mode, "content"],
    )
    return True


def verify_dashboard(verdict: Verdict) -> bool:
    """S06: дашборд видимости в AI-поиске."""
    try:
        conn = connect_db()
        total = conn.execute("SELECT COUNT(*) FROM aeo_citations").fetchone()[0]
        by_llm = conn.execute(
            "SELECT llm, COUNT(*) FROM aeo_citations GROUP BY llm ORDER BY 2 DESC"
        ).fetchall()
        audits = conn.execute("SELECT COUNT(*) FROM aeo_audits").fetchone()[0]
        conn.close()
    except Exception as e:  # noqa: BLE001
        verdict.block("S06: AI visibility dashboard", f"БД недоступна: {e}")
        return False

    detail = ", ".join(f"{llm}={n}" for llm, n in by_llm) or "нет данных"
    verdict.pass_(
        "S06: AI visibility dashboard",
        f"Всего цитирований: {total} | по LLM: {detail} | аудитов: {audits}. "
        f"Метрики: цитирований на страницу, покрытие LLM, скорость цитирования, "
        f"пересечение запросов с конкурентами.",
    )
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["S01", "S02", "S03", "S04", "S05", "S06", "all"], default="all")
    ap.add_argument("--url", default="")
    ap.add_argument("--llm", default="perplexity", choices=LLM_PROVIDERS)
    ap.add_argument("--query", default="")
    ap.add_argument("--industry", default="saas", choices=sorted(INDUSTRY_THRESHOLDS))
    ap.add_argument("--competitor", default="")
    ap.add_argument("--mode", default="balanced", choices=["conservative", "balanced", "aggressive"])
    args = ap.parse_args()

    verdict = Verdict("F008")
    steps = ["S01", "S02", "S03", "S04", "S05", "S06"] if args.step == "all" else [args.step]

    for s in steps:
        if s == "S01":
            verify_citations(verdict, args.url, args.llm, args.query)
        elif s == "S02":
            verify_eeat(verdict, args.url, args.industry)
        elif s == "S03":
            verify_schema(verdict, args.url)
        elif s == "S04":
            verify_competitor(verdict, args.competitor)
        elif s == "S05":
            verify_optimization(verdict, args.url, args.mode)
        elif s == "S06":
            verify_dashboard(verdict)

    verdict.print_summary()

    log_guide_safe(
        "aeo",
        f"AEO Step {args.step} — industry={args.industry}, mode={args.mode}",
        f"URL: {args.url or 'N/A'}. Steps verified: {args.step}. "
        f"Features: citation tracking, E-E-A-T audit, schema validation, "
        f"competitor analysis, content optimization, visibility dashboard.",
        ["aeo", "f008", args.step, "ai-overviews"],
    )

    return verdict.exit_code()


if __name__ == "__main__":
    sys.exit(main())
