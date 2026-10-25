import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'C:\Users\anton\Desktop\traduzione libri\extracted_text.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

pages_to_show = sys.argv[1] if len(sys.argv) > 1 else '1-5'

for part in pages_to_show.split(','):
    if '-' in part:
        start, end = map(int, part.split('-'))
        for pg in range(start, end+1):
            page_data = data[pg-1]
            print(f"\n{'='*60}")
            print(f"=== PAGINA {page_data['page']} ===")
            print(f"{'='*60}")
            for idx, b in enumerate(page_data['blocks']):
                if b['type'] == 0 and b['text'].strip():
                    print(f"\n[Blocco {idx}] ({b.get('font','?')} {b.get('size',0)})")
                    print(b['text'][:300])
    else:
        pg = int(part)
        page_data = data[pg-1]
        print(f"\n{'='*60}")
        print(f"=== PAGINA {page_data['page']} ===")
        print(f"{'='*60}")
        for idx, b in enumerate(page_data['blocks']):
            if b['type'] == 0 and b['text'].strip():
                print(f"\n[Blocco {idx}] ({b.get('font','?')} {b.get('size',0)})")
                print(b['text'][:300])
