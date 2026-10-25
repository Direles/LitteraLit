import fitz, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Compare original vs translated page 2 (a text-heavy page)
orig = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf')
trans = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf')

# Save preview images
for idx, label in [(1, 'originale'), (1, 'tradotto')]:
    pass

# Save sample pages as PNG for visual comparison
page_orig = orig[1]
pix_orig = page_orig.get_pixmap(matrix=fitz.Matrix(2, 2))
pix_orig.save(r'C:\Users\anton\Desktop\traduzione libri\test_output\pagina2_originale.png')

page_trans = trans[1]
pix_trans = page_trans.get_pixmap(matrix=fitz.Matrix(2, 2))
pix_trans.save(r'C:\Users\anton\Desktop\traduzione libri\test_output\pagina2_tradotto.png')

print("Immagini salvate in test_output/")

# Also save a few more key pages
for pg in [0, 6, 10]:
    page_orig = orig[pg]
    pix_orig = page_orig.get_pixmap(matrix=fitz.Matrix(2, 2))
    pix_orig.save(rf'C:\Users\anton\Desktop\traduzione libri\test_output\pagina{pg+1}_originale.png')
    
    page_trans = trans[pg]
    pix_trans = page_trans.get_pixmap(matrix=fitz.Matrix(2, 2))
    pix_trans.save(rf'C:\Users\anton\Desktop\traduzione libri\test_output\pagina{pg+1}_tradotto.png')
    print(f"Pagina {pg+1} salvata")

orig.close()
trans.close()
print("\nCompletato!")
