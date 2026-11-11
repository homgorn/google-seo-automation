import json
from collections import Counter

f = json.load(open('feature_list.json', encoding='utf-8'))
print("FEATURES:", len(f))
print("Categories:", dict(Counter(x['category'] for x in f)))
print("Passes=true:", sum(1 for x in f if x['passes']))
print()
print("STEPS PER FEATURE:")
for x in f:
    print(f"  {x['id']} [{x['category']:12s}] p={x['priority']} steps={len(x['steps']):2d} - {x['description'][:66]}")
print()
print("FIELDS PRESENT:", sorted(set().union(*[set(x.keys()) for x in f])))
print()
print("SDD GAP ANALYSIS:")
need = ['acceptance_criteria', 'requirements', 'spec', 'depends_on', 'blocked_by',
        'estimate', 'test_refs', 'verifier', 'sub_tasks', 'risk']
for field in need:
    present = sum(1 for x in f if field in x)
    print(f"  {field:22s} present in {present}/{len(f)}")
print()
print("SCRIPTS vs STEPS:")
import os
scripts = sorted(s for s in os.listdir('scripts') if s.endswith('.py'))
for s in scripts:
    print(f"  {s}")
print()
print("TESTS:")
for s in os.listdir('tests'):
    print(f"  {s}")
