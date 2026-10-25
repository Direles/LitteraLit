import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'

with open(TR_PATH, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Read translations JSON from stdin or from a temp file
update_path = sys.argv[1] if len(sys.argv) > 1 else None
if update_path:
    with open(update_path, 'r', encoding='utf-8') as f:
        updates = json.load(f)
else:
    updates = json.load(sys.stdin)

count = 0
for key, val in updates.items():
    if key in data and val.get('translated'):
        data[key]['translated'] = val['translated']
        count += 1

with open(TR_PATH, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=1)

print(f"Aggiornate {count} traduzioni. Restanti: {sum(1 for v in data.values() if not v['translated'])}")
