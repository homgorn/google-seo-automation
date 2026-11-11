import sqlite3
conn = sqlite3.connect("data/wiki.db")
print("=== guides -> doc_id -> source (must MATCH!) ===")
rows = conn.execute(
    """SELECT g.doc_id, d.source, g.guide_type, g.title
       FROM guides g JOIN api_docs d ON d.id = g.doc_id
       ORDER BY d.source, g.title"""
).fetchall()
from collections import Counter
c = Counter(r[1] for r in rows)
for src, n in sorted(c.items()):
    print("  %-22s %d guides" % (src, n))
print()
print("=== MISMATCH CHECK ===")
# Ожидаемое соответствие: gsc->gsc, gtm->gtm, ga4->ga4_data, ads/aeo->google-apis-master
expected = {
    "gsc": "gsc",
    "gtm": "gtm",
    "ga4": "ga4_data",
    "ads": "google-apis-master",
    "aeo": "google-apis-master",
}
bad = 0
for gdoc_id, src, gtype, title in rows:
    # определяем feature по заголовку
    feat = None
    tl = title.lower()
    if "gsc" in tl or "sitemap" in tl:
        feat = "gsc"
    elif "gtm" in tl or "tag" in tl or "trigger" in tl or "version" in tl or "variable" in tl:
        feat = "gtm"
    elif "ga4" in tl or "key event" in tl or "bigquery export" in tl or "data stream" in tl:
        feat = "ga4"
    elif "ads" in tl or "budget" in tl or "keyword" in tl or "campaign lifecycle" in tl:
        feat = "ads"
    elif "aeo" in tl or "e-e-a-t" in tl or "schema" in tl or "citation" in tl or "content optimization" in tl or "competitor" in tl:
        feat = "aeo"
    if feat and feat in expected:
        exp = expected[feat]
        if src != exp:
            bad += 1
            print("  MISMATCH: guide='%s' feature=%s doc_id=%s source=%s (expected %s)" % (title[:45], feat, gdoc_id, src, exp))
print()
print("Mismatches:", bad)
print("Total guides:", len(rows))
