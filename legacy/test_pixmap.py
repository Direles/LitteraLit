import fitz, io
from PIL import Image, ImageDraw

img = Image.new('RGB', (100, 100), color='red')
draw = ImageDraw.Draw(img)
draw.text((10, 40), "Test Italiano àèìòù", fill='white')

# Try method 1: save as PNG then load
buf = io.BytesIO()
img.save(buf, format='PNG')
buf.seek(0)
pix = fitz.Pixmap(buf.read())
print(f"Method 1 (PNG bytes): {pix.width}x{pix.height}")

# Try method 2: raw RGB bytes
raw = img.tobytes()
pix2 = fitz.Pixmap(fitz.csRGB, img.width, img.height, raw)
print(f"Method 2 (raw RGB): {pix2.width}x{pix2.height}")

# Create PDF
doc = fitz.open()
page = doc.new_page(width=300, height=300)
page.insert_image((0, 0, 300, 300), pixmap=pix)
doc.save(r'C:\Users\anton\Desktop\traduzione libri\test_output\test_pix.pdf')
doc.close()
print("PDF salvato con successo!")
