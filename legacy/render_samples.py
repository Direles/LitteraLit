import fitz, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

OUT = r'C:\Users\anton\Desktop\traduzione libri\test_output'

orig = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf')
trans = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf')

mat = fitz.Matrix(2.5, 2.5)  # ~250 DPI for clear preview

for pg in [1, 2, 6, 15, 30, 100]:
    page_orig = orig[pg]
    page_trans = trans[pg]
    
    pix_orig = page_orig.get_pixmap(matrix=mat)
    pix_trans = page_trans.get_pixmap(matrix=mat)
    
    pix_orig.save(os.path.join(OUT, f'orig_pg{pg+1}.png'))
    pix_trans.save(os.path.join(OUT, f'trad_pg{pg+1}.png'))

orig.close()
trans.close()
print(f"Salvate {6*2} immagini in {OUT}")
print("Apri le immagini per confrontare originale (orig_pg*.png) vs tradotto (trad_pg*.png)")
