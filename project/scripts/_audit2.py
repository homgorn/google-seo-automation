import sqlite3
import os
import re

conn = sqlite3.connect("data/wiki.db")

print("=== ACTUAL doc_id -> source ===")
for r in conn.execute("SELECT id, source, category FROM api_docs ORDER BY id"):
    print("  id=%-3d source=%-22s cat=%s" % r)

print()
print("=== guides schema ===")
row = conn.execute("SELECT sql FROM sqlite_master WHERE name='guides'").fetchone()
print(row[0] if row else "NOT FOUND")

print()
print("=== guides rows (doc_id, guide_type, title) ===")
for r in conn.execute("SELECT doc_id, guide_type, title FROM guides LIMIT 25"):
    print("  doc_id=%-3d [%s] %s" % r)

print()
print("guides total rows:", conn.execute("SELECT COUNT(*) FROM guides").fetchone()[0])
dupes = conn.execute(
    "SELECT doc_id, title, COUNT(*) c FROM guides GROUP BY doc_id, title HAVING c > 1"
).fetchall()
print("duplicate (doc_id,title) groups:", len(dupes))
for d in dupes[:5]:
    print("   ", d)

print()
print("=== ENV VARS READ BY SCRIPTS vs .env.example ===")
read_vars = set()
for f in sorted(os.listdir("scripts")):
    if not f.endswith(".py"):
        continue
    text = open(os.path.join("scripts", f), encoding="utf-8").read()
    for m in re.finditer(r"os\.getenv\(\s*[\"']([A-Z_]+)[\"']", text):
        read_vars.add(m.group(1))
    for m in re.finditer(r"os\.environ(?:\.get)?\(\s*[\"']([A-Z_]+)[\"']", text):
        read_vars.add(m.group(1))

example = open(".env.example", encoding="utf-8").read()
declared = set(re.findall(r"^([A-Z_][A-Z0-9_]*)=", example, re.MULTILINE))

print("READ by code but NOT in .env.example:", sorted(read_vars - declared) or "none")
print()
print("In .env.example but NEVER read by code:", sorted(declared - read_vars) or "none")
print()
print("Read by code:", sorted(read_vars))
