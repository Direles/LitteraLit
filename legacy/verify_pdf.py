import fitz, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PDF_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf'

doc = fitz.open(PDF_PATH)
print(f"Pagine: {len(doc)}")

# Check a few pages
for pg in [0, 1, 4, 15, 50]:
    page = doc[pg]
    # Extract text from image - PyMuPDF will try OCR but won't find text in images
    text = page.get_text()
    text_len = len(text.strip())
    print(f"Pagina {pg+1}: {text_len} caratteri (testo da OCR/immagine)")

# Check images on each page
for pg in [0, 1]:
    page = doc[pg]
    images = page.get_images()
    print(f"Pagina {pg+1}: {len(images)} immagini incorporate")

# File info
import os
size_mb = os.path.getsize(PDF_PATH) / 1024 / 1024
print(f"\nDimensione file: {size_mb:.1f} MB")

doc.close()
print("\nPDF verificato con successo!")
