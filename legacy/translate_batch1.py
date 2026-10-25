import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
BATCH_PATH = r'C:\Users\anton\Desktop\traduzione libri\traduzioni_batch1.json'

with open(TR_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Find untranslated blocks
untranslated = {k: v for k, v in data.items() if not v['translated']}
print(f"Blocchi non tradotti: {len(untranslated)}")

# Save a batch file for me to work with
count = 0
batch = {}
for key, val in untranslated.items():
    # Extract page number for ordering
    batch[key] = val
    count += 1
    if count >= 100:
        break

with open(BATCH_PATH, 'w', encoding='utf-8') as f:
    json.dump(batch, f, ensure_ascii=False, indent=1)

print(f"Batch salvato: {BATCH_PATH}")
print(f"Blocchi in questo batch: {len(batch)}")
print("\nPrimi 5 blocchi:")
for i, (k, v) in enumerate(list(batch.items())[:5]):
    print(f"\n--- {k} ---")
    print(v['original'][:200])
