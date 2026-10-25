import fitz, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

doc = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf')
page = doc[5]  # page 6
blocks = page.get_text('dict')['blocks']
print(f"Pagina 6 originale: {len(blocks)} blocchi")
for b in blocks:
    if b['type'] == 0:
        t = ""
        for l in b['lines']:
            for s in l['spans']:
                t += s['text']
        print(f"  TESTO: '{t.strip()[:100]}'")
    elif b['type'] == 1:
        print(f"  IMMAGINE: {b['bbox']}")
doc.close()
