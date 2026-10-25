import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'C:\Users\anton\Desktop\traduzione libri\extracted_text.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

translations = {}
total_chars = 0

for page in data:
    pg = page['page']
    for idx, b in enumerate(page['blocks']):
        if b['type'] == 0 and b['text'].strip():
            key = f"p{pg}_b{idx}"
            translations[key] = {
                'original': b['text'],
                'translated': ''
            }
            total_chars += len(b['text'])

with open(r'C:\Users\anton\Desktop\traduzione libri\translations.json', 'w', encoding='utf-8') as f:
    json.dump(translations, f, ensure_ascii=False, indent=1)

print(f"Template creato: {len(translations)} blocchi di testo, {total_chars} caratteri")
print(f"File: translations.json")
