import fitz, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

doc = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf')
with open(r'C:\Users\anton\Desktop\traduzione libri\translations.json', 'r', encoding='utf-8') as f:
    tr = json.load(f)

# Check key pages
for pg in [1, 2, 15, 29, 59, 99]:
    page = doc[pg]
    text = page.get_text()
    acc = sum(1 for c in text if c in 'àèéìòù')
    eng = sum(text.lower().count(w) for w in [' the ', ' and ', ' development '])
    ita = sum(text.lower().count(w) for w in [' lo ', ' il ', ' la ', ' sviluppo ', ' prodotto '])
    lines = [l for l in text.split('\n') if l.strip()]
    print(f"Pg {pg+1}: {len(lines)} righe, acc={acc}, ENG={eng}, ITA={ita}")
    for l in lines[:3]:
        print(f"  {l[:120]}")
    print()

# Verify images are preserved: count images per page
for pg in [0, 1, 15]:
    page = doc[pg]
    imgs = page.get_images()
    print(f"Pg {pg+1}: immagini = {len(imgs)}")

# Count blocks that overlap images  
orig = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf')
# Check cover page for image overlap
page0 = orig[0]
blocks0 = page0.get_text('dict')['blocks']
img0 = [b for b in blocks0 if b['type']==1]
txt0 = [b for b in blocks0 if b['type']==0]
print(f"\nCover page: {len(txt0)} text blocks, {len(img0)} images")
for tb in txt0:
    for line in tb['lines']:
        for sp in line['spans']:
            pass
    bbox = tb['bbox']
    print(f"  Text at {[round(c,1) for c in bbox]}")
for ib in img0:
    print(f"  Image at {[round(c,1) for c in ib['bbox']]}")

orig.close()
doc.close()
