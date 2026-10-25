import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'C:\Users\anton\Desktop\traduzione libri\extracted_text.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Show pages that still need translation
with open(r'C:\Users\anton\Desktop\traduzione libri\translations.json', 'r', encoding='utf-8') as f:
    tr = json.load(f)

# For each page, check if any blocks still need translation
for page_data in data:
    pg = page_data['page']
    needs_translation = False
    page_text = f"\n{'='*60}\n=== PAGINA {pg} ===\n{'='*60}\n"
    
    for idx, b in enumerate(page_data['blocks']):
        if b['type'] == 0 and b['text'].strip():
            key = f"p{pg}_b{idx}"
            orig = b['text']
            translated = tr.get(key, {}).get('translated', '')
            
            if not translated:
                needs_translation = True
                page_text += f"\n--- Blocco {idx} ---\n{orig}\n"
    
    if needs_translation:
        print(page_text)
