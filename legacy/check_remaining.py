import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'C:\Users\anton\Desktop\traduzione libri\translations.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

remaining = {k: v for k, v in d.items() if not v['translated']}
print(f"Rimasti: {len(remaining)}")
for k, v in remaining.items():
    print(f"\n--- {k} ---")
    print(v['original'][:300])
