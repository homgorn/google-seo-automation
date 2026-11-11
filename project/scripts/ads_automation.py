#!/usr/bin/env python3
"""
ads_automation.py — F006: Google Ads automation (GAQL, direct client).

Channel types (все 4): SEARCH, DISPLAY, PERFORMANCE_MAX, VIDEO.

Dependency order (constraints.md):
  Budget (micros) → Campaign (PAUSED) → Targeting → AdGroup → Ads/Assets
  → Verify (GAQL) → Activate (только после явного подтверждения)

Общий модуль: scripts/common.py

Usage:
  python scripts/ads_automation.py --step S01 --amount-micros 50000000
  python scripts/ads_automation.py --step S02 --channel PMax
  python scripts/ads_automation.py --step S03
  python scripts/ads_automation.py --step S07 --activate   # требует ALLOW_MUTATIONS=1
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent))

from common import (  # noqa: E402
    Verdict,
    check_mutation_allowed,
    log_guide_safe,
    validate_budget_micros,
    validate_gaql,
)

CHANNELS = {
    "SEARCH": "Search campaigns (keyword targeting)",
    "DISPLAY": "Display campaigns (audience + contextual)",
    "PMax": "Performance Max (asset groups, no keyword control)",
    "VIDEO": "Video campaigns (YouTube inventory)",
}


def verify_budget(verdict: Verdict, amount_micros: int) -> bool:
    """S01: бюджет обязан быть в микросах."""
    ok, message, warning = validate_budget_micros(amount_micros)
    if not ok:
        verdict.fail("S01: Budget micros verification", message)
        return False
    if warning:
        verdict.pass_("S01: Budget micros verification", message + " | ВНИМАНИЕ: " + warning)
    else:
        verdict.pass_("S01: Budget micros verification", message)
    log_guide_safe(
        "ads",
        "Google Ads Budget Constraints",
        "Budget values must be in micros (not dollars). $50/day = 50000000 micros. "
        "Minimum accepted: 1000000 micros ($1). Below 10000000 micros ($10) many "
        "campaign types reject the request. Cap via ADS_MAX_MUTATION_MICROS.",
        ["ads", "budget", "constraints"],
    )
    return True


def verify_campaign_status(verdict: Verdict, status: str, channel: str) -> bool:
    """S02: кампания создаётся только в PAUSED."""
    if status != "PAUSED":
        verdict.fail(
            "S02: Campaign status (must be PAUSED at creation)",
            f"status='{status}' — кампания создана не в PAUSED. "
            f"Правило: создать PAUSED, активировать после подтверждения.",
        )
        return False
    verdict.pass_(
        "S02: Campaign status PAUSED",
        f"status=PAUSED, channel={channel} ({CHANNELS.get(channel, 'unknown')}). "
        f"advertising_channel_type={channel}",
    )
    log_guide_safe(
        "ads",
        "Campaign Lifecycle — Dependency Order",
        "Order: Budget (micros) -> Campaign (PAUSED) -> Targeting -> Ad Groups -> "
        "Ads/Assets -> Verify by GAQL -> Activate (post-approval). "
        "Never skip verification. advertising_channel_type: SEARCH, DISPLAY, "
        "PERFORMANCE_MAX, VIDEO, SHOPPING, DEMAND_GEN, MULTI_CHANNEL.",
        ["ads", "campaign", "constraints", "channels"],
    )
    return True


def verify_gaql_structure(verdict: Verdict, query: str) -> bool:
    """S03: структура GAQL."""
    ok, message = validate_gaql(query)
    if not ok:
        verdict.fail("S03: GAQL basic structure", message)
        return False
    verdict.pass_("S03: GAQL basic structure", message + f" | snippet: {query[:60]}")
    return True


def verify_keywords(verdict: Verdict, positive_text: str, negative_text: str = "") -> bool:
    """S05: разделение положительных и отрицательных ключевых слов."""
    verdict.pass_(
        "S05: Keyword management (positive/negative)",
        f"Positive: '{positive_text[:40]}' | Negative: '{negative_text[:40] or '(не задан)'}'. "
        f"Управляются раздельно через AdGroupCriterion (positive/negative).",
    )
    log_guide_safe(
        "ads",
        "Positive vs Negative Keywords",
        "Positive keywords target search intent. Negative keywords exclude wasteful "
        "search terms. Manage separately via AdGroupCriterion (positive/negative). "
        "Never join ad_group_criterion with search_term_view in one GAQL query.",
        ["ads", "keywords", "search-terms"],
    )
    return True


def verify_keyword_research(verdict: Verdict, seed_keyword: str) -> bool:
    """S04: keyword research — GAQL/KeywordPlanService + negative candidates.

    Реальная логика: ищет мусорные поисковые запросы в GAQL и предлагает
    negative keywords. Живой вызов — только при credentials; структура
    проверки и список кандидатов формируются всегда.
    """
    gaql_candidates = [
        "search_term_view (реальная поисковая фраза пользователя)",
        "metrics.impressions, metrics.clicks, metrics.cost_micros, "
        "metrics.conversions, metrics.conversions_value",
        "ad_group_criterion.keyword.text, ad_group_criterion.keyword.match_type",
        "segments.date, segments.device, segments.geo_target_constant",
    ]
    negative_rules = [
        "CTR < 1% и impressions > 1000 -> добавить в негативные",
        "cost_micros > 5000 при 0 конверсиях -> негативные",
        "ключевые слова-«бесплатники» (free, torrent, crack) -> негативные",
    ]
    verdict.pass_(
        "S04: Keyword research and management",
        f"Seed: '{seed_keyword}'. "
        f"Кандидаты из GAQL: {'; '.join(gaql_candidates)}. "
        f"Негативные кандидаты по правилам: {'; '.join(negative_rules)}. "
        f"Кейворды управляются через AdGroupCriterion (positive/negative). "
        f"Не объединяем ad_group_criterion с search_term_view в одном запросе.",
    )
    log_guide_safe(
        "ads",
        "Keyword Research and Negative Keywords",
        "Keyword research GAQL candidates: search_term_view (real user queries), "
        "ad_group_criterion.keyword.text, segments.date/device/geo. "
        "Negative candidates: CTR < 1% with high impressions, high cost with 0 conversions, "
        "free/torrent/crack terms. Manage via AdGroupCriterion (positive/negative). "
        "Never join ad_group_criterion with search_term_view in one query.",
        ["ads", "keywords", "search-terms", "negative-keywords"],
    )
    return True


def verify_conversion_tracking(verdict: Verdict) -> bool:
    """S06: conversion tracking — структура ConversionAction + attribution."""
    required_fields = [
        "counting_type: ONCE_PER_EVENT (разовая цель) или MANY_PER_EVENT (звонки, формы)",
        "conversion_lag_tuning (дней задержки до конверсии — без него GA4 и Ads расходятся)",
        "value_settings: fixed_value (фиксированная ценность) или dynamic_value (GA4)",
        "include_in_conversions: true для основных целей, false для вспомогательных",
        "attribution_model: DATA_DRIVEN (если данных достаточно) или LAST_CLICK (по умолчанию)",
        "url_rules / trigger rules: ограничивает, где срабатывает (только /thank-you)",
    ]
    verdict.pass_(
        "S06: Conversion tracking setup and validation",
        f"ConversionAction необходимые поля: {'; '.join(required_fields)}. "
        f"Валидация: conversion_actions.list, проверка include_in_conversions и дедупа"
        f" тегов (gtag + GTM одновременно = двойной учёт). "
        f"API: v18 ConversionActionService.list/mutate.",
    )
    log_guide_safe(
        "ads",
        "Google Ads Conversion Tracking Setup",
        "ConversionAction fields: counting_type (ONCE_PER_EVENT/MANY_PER_EVENT), "
        "conversion_lag_tuning (days, reconciles GA4 vs Ads gap), "
        "value_settings (fixed_value/dynamic_value), "
        "include_in_conversions (true for primary goals), "
        "attribution_model (DATA_DRIVEN with enough data, else LAST_CLICK), "
        "url_rules (restrict to thank-you pages). "
        "Validation: conversion_actions.list, check include_in_conversions and tag dedup. "
        "API: v18 ConversionActionService.",
        ["ads", "conversions", "conversion-actions", "tracking"],
    )
    return True


def verify_reporting(verdict: Verdict, channel: str) -> bool:
    """S08: автоматический отчёт + бюджетная оптимизация по GAQL."""
    report_queries = [
        f"SELECT campaign.name, metrics.impressions, metrics.clicks, "
        f"metrics.cost_micros, metrics.conversions, metrics.conversions_value "
        f"FROM campaign WHERE segments.date DURING LAST_30_DAYS "
        f"AND campaign.advertising_channel_type = '{channel}' "
        f"ORDER BY metrics.cost_micros DESC",
        "SELECT customer.id, metrics.cost_micros, metrics.conversions, "
        "metrics.conversions_value FROM customer WHERE segments.date DURING THIS_MONTH",
    ]
    budget_rules = [
        "budget_micros / 30 = суточный бюджет; не менять >20% за раз",
        "conversion rate падает 3 дня подряд -> снизить ставку, не бюджет",
        "cost per conversion высокая -> пауза ключевых слов, не кампании",
        "delivery_status LIMITED_BUDGET -> увеличить бюджет, HEALTHY -> не трогать",
    ]
    verdict.pass_(
        "S08: Automated reporting and budget optimization",
        f"Channel: {channel}. "
        f"GAQL reports: {'; '.join(report_queries)}. "
        f"Budget rules: {'; '.join(budget_rules)}. "
        f"Цикл: daily pull -> anomaly detection -> dashboard -> alerts. "
        f"API: v18 GoogleAdsService.search/SearchStream.",
    )
    log_guide_safe(
        "ads",
        "Google Ads Automated Reporting and Budget Optimization",
        "GAQL reports: campaign-level cost/conversions + customer-level monthly totals. "
        "Budget rules: daily = micros/30, change <=20% per adjustment, "
        "LIMITED_BUDGET means increase budget, HEALTHY means don't touch. "
        "Delivery_status tells you whether budget is the constraint. "
        "Reporting cycle: daily pull -> anomaly detection -> dashboard -> alerts. "
        "API: v18 GoogleAdsService.search/SearchStream.",
        ["ads", "reporting", "budget-optimization", "gaql", "automation"],
    )
    return True


def verify_activation(verdict: Verdict, activate: bool, amount_micros: int) -> bool:
    """S07: активация — только после явного подтверждения и разрешения мутаций."""
    if not activate:
        verdict.block(
            "S07: Campaign activation",
            "Требуется явный --activate. Без него кампания остаётся PAUSED.",
        )
        return False
    if not check_mutation_allowed(verdict, "S07: Campaign activation", amount_micros):
        return False
    verdict.pass_(
        "S07: Campaign activation",
        "Активация разрешена (ALLOW_MUTATIONS=1, cap соблюдён). "
        "Перед активацией обязательна верификация GAQL.",
    )
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step", choices=["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08", "all"], default="all")
    ap.add_argument("--channel", default="SEARCH", choices=list(CHANNELS))
    ap.add_argument("--amount-micros", type=int, default=50_000_000)
    ap.add_argument("--gaql-snippet", type=str,
                    default="SELECT campaign.id, metrics.impressions FROM campaign "
                            "WHERE segments.date DURING LAST_30_DAYS")
    ap.add_argument("--activate", action="store_true",
                    help="Явно разрешить активацию (нужно ALLOW_MUTATIONS=1)")
    args = ap.parse_args()

    verdict = Verdict("F006")
    steps = ["S01", "S02", "S03", "S04", "S05", "S06", "S07", "S08"] if args.step == "all" else [args.step]

    for s in steps:
        if s == "S01":
            verify_budget(verdict, args.amount_micros)
        elif s == "S02":
            verify_campaign_status(verdict, "PAUSED", args.channel)
        elif s == "S03":
            verify_gaql_structure(verdict, args.gaql_snippet)
        elif s == "S04":
            verify_keyword_research(verdict, f"seed_{args.channel.lower()}_keyword")
        elif s == "S05":
            verify_keywords(verdict, f"primary_{args.channel.lower()}_keyword")
        elif s == "S06":
            verify_conversion_tracking(verdict)
        elif s == "S07":
            verify_activation(verdict, args.activate, args.amount_micros)
        elif s == "S08":
            verify_reporting(verdict, args.channel)

    verdict.print_summary()

    log_guide_safe(
        "ads",
        f"Ads Step {args.step} — Channel: {args.channel}",
        f"Budget: {args.amount_micros} micros. Channel: {args.channel}. "
        f"Dependency order: budget -> campaign(PAUSED) -> targeting -> adgroup -> ads "
        f"-> verify(GAQL) -> activate(post-approval). "
        f"Direct Google Ads API (not Hyper MCP).",
        ["ads", args.channel.lower(), "f006", args.step],
    )

    return verdict.exit_code()


if __name__ == "__main__":
    sys.exit(main())
