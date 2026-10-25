import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'C:\Users\anton\Desktop\traduzione libri\extracted_text.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open(r'C:\Users\anton\Desktop\traduzione libri\translations.json', 'r', encoding='utf-8') as f:
    tr = json.load(f)

# Find pages that need translation
pending_pages = []
for page_data in data:
    pg = page_data['page']
    for idx, b in enumerate(page_data['blocks']):
        if b['type'] == 0 and b['text'].strip():
            key = f"p{pg}_b{idx}"
            if not tr.get(key, {}).get('translated', ''):
                pending_pages.append(pg)
                break

pending_pages = sorted(set(pending_pages))
print(f"Pagine con blocchi non tradotti: {len(pending_pages)}")
print(f"Da pagina {pending_pages[0]} a pagina {pending_pages[-1]}")
print(f"\nPrime 10 pagine: {pending_pages[:10]}")

# Group in ranges
ranges = []
start = pending_pages[0]
end = pending_pages[0]
for p in pending_pages[1:]:
    if p == end + 1:
        end = p
    else:
        ranges.append((start, end))
        start = p
        end = p
ranges.append((start, end))

print(f"\nIntervalli di pagine non tradotte:")
for s, e in ranges:
    if s == e:
        print(f"  Pagina {s}")
    else:
        print(f"  Pagine {s}-{e}")
