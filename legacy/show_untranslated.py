import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'C:\Users\anton\Desktop\traduzione libri\translations.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Show first N untranslated or all
batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 50
count = 0
output = {}

for key, val in data.items():
    if not val['translated']:
        output[key] = val
        count += 1
        if count >= batch_size:
            break

# Output as JSON for easy copying
print(json.dumps(output, ensure_ascii=False, indent=1))
print(f"\n--- Mostrati {count} blocchi. Rimasti: {sum(1 for v in data.values() if not v['translated'])} ---", file=sys.stderr)
