import fitz, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image, ImageDraw

img = Image.new('RGB', (400, 400), color='lightgray')
draw = ImageDraw.Draw(img)
draw.text((50, 180), "Test Italiano àèìòù", fill='black')

buf = io.BytesIO()
img.save(buf, format='PNG')
buf.seek(0)
pix = fitz.Pixmap(buf.read())
print(f"Pixmap from bytes: {pix.width}x{pix.height}")

doc = fitz.open()
page = doc.new_page(width=400, height=400)
page.insert_image((0, 0, 400, 400), pixmap=pix)
doc.save(r'C:\Users\anton\Desktop\traduzione libri\test_output\test_pix2.pdf')
doc.close()
print("PDF salvato con successo!")
