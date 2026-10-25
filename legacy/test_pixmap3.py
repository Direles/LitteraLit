import fitz, io, os, sys, tempfile
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image, ImageDraw

img = Image.new('RGB', (400, 400), color='lightgray')
draw = ImageDraw.Draw(img)
draw.text((50, 180), "Test Italiano àèìòù", fill='black')

# Save to temp file and open with fitz.Pixmap
tmp = r'C:\Users\anton\Desktop\traduzione libri\test_output\temp.png'
img.save(tmp)
pix = fitz.Pixmap(tmp)
print(f"Pixmap: {pix.width}x{pix.height}")

doc = fitz.open()
page = doc.new_page(width=400, height=400)
page.insert_image((0, 0, 400, 400), pixmap=pix)
doc.save(r'C:\Users\anton\Desktop\traduzione libri\test_output\test_pix.pdf')
doc.close()
os.remove(tmp)
print("PDF salvato con successo!")
