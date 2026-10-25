import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
BATCH_SIZE = 150

with open(TR_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

untranslated = {k: v for k, v in data.items() if not v['translated']}
print(f"Blocchi non tradotti: {len(untranslated)}")

# Figure out which batch number we're on
import glob, os
existing = [f for f in os.listdir(os.path.dirname(TR_PATH)) if f.startswith('batch_') and f.endswith('.json') and 'DONE' not in f]
batch_num = max([int(f.split('_')[1].split('.')[0]) for f in existing], default=0) + 1

count = 0
batch = {}
for key, val in untranslated.items():
    batch[key] = val
    count += 1
    if count >= BATCH_SIZE:
        break

batch_path = os.path.join(os.path.dirname(TR_PATH), f'batch_{batch_num:03d}.json')
with open(batch_path, 'w', encoding='utf-8') as f:
    json.dump(batch, f, ensure_ascii=False, indent=1)

print(f"Batch {batch_num}: {batch_path}")
print(f"Blocchi in questo batch: {len(batch)}")

# Show first 3 blocks for reference
for i, (k, v) in enumerate(list(batch.items())[:3]):
    print(f"\n--- {k} ---")
    print(v['original'][:200])
