import json, sys, os, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
EXTRACTED_PATH = r'C:\Users\anton\Desktop\traduzione libri\extracted_text.json'
OUT_DIR = r'C:\Users\anton\Desktop\traduzione libri'

with open(TR_PATH, 'r', encoding='utf-8') as f:
    tr = json.load(f)
with open(EXTRACTED_PATH, 'r', encoding='utf-8') as f:
    extracted = json.load(f)

# Create batches by page range
ranges = [
    (16, 35, "p16-35"),
    (36, 55, "p36-55"),
    (56, 80, "p56-80"),
    (83, 110, "p83-110"),
    (111, 140, "p111-140"),
    (141, 170, "p141-170"),
    (171, 200, "p171-200"),
    (201, 230, "p201-230"),
    (231, 260, "p231-260"),
    (261, 290, "p261-290"),
    (291, 324, "p291-324"),
]

for start, end, name in ranges:
    batch = {}
    for pg in range(start, end+1):
        if pg <= len(extracted):
            page_data = extracted[pg-1]
            for idx, b in enumerate(page_data['blocks']):
                if b['type'] == 0 and b['text'].strip():
                    key = f"p{pg}_b{idx}"
                    if key in tr and not tr[key]['translated']:
                        batch[key] = tr[key]
    
    if batch:
        out = os.path.join(OUT_DIR, f'batch_{name}.json')
        with open(out, 'w', encoding='utf-8') as f:
            json.dump(batch, f, ensure_ascii=False, indent=1)
        print(f"Batch {name}: {len(batch)} blocchi -> {out}")

print(f"\nTutti i batch creati. Totale blocchi non tradotti: {sum(1 for v in tr.values() if not v['translated'])}")
