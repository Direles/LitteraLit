import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'C:\Users\anton\Desktop\traduzione libri\extracted_text.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Pagine totali: {len(data)}")
print(f"Prima pagina: {data[0]['page']}, blocchi: {len(data[0]['blocks'])}")

tb = [b for b in data[0]['blocks'] if b['type'] == 0]
print(f"Blocchi testo prima pagina: {len(tb)}")
print(f"\nTesto prima pagina:")
for b in tb[:5]:
    print(f"  [{b.get('font','?')} {b.get('size',0)}] {b['text'][:80]}")

# Count total chars
total = sum(len(b['text']) for page in data for b in page['blocks'] if b['type'] == 0)
print(f"\nTotale caratteri testo: {total}")

# Sample a page with lots of text
for p in data:
    tb = [b for b in p['blocks'] if b['type'] == 0]
    text_len = sum(len(b['text']) for b in tb)
    if text_len > 2000:
        print(f"\nPagina {p['page']}: {len(tb)} blocchi, {text_len} caratteri")
        for b in tb[:3]:
            print(f"  {b['text'][:100]}")
        break
