import fitz, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image, ImageDraw

# Create a simple test image
img = Image.new('RGB', (400, 400), color='lightgray')
draw = ImageDraw.Draw(img)
draw.text((50, 180), "Test Italiano àèìòù", fill='black')

# Method: use raw RGB bytes
raw = img.tobytes()  # Returns RGBRGB...
print(f"Image size: {img.size}, raw bytes len: {len(raw)}")

# Create Pixmap from raw bytes
pix = fitz.Pixmap(fitz.csRGB, img.width, img.height, raw)
print(f"Pixmap: {pix.width}x{pix.height}, n={pix.n}")

# Save directly (debug)
pix.save(r'C:\Users\anton\Desktop\traduzione libri\test_output\test_pixmap.png')
print("Pixmap saved as PNG")

# Create PDF
doc = fitz.open()
page = doc.new_page(width=400, height=400)
page.insert_image((0, 0, 400, 400), pixmap=pix)
doc.save(r'C:\Users\anton\Desktop\traduzione libri\test_output\test_pix.pdf')
doc.close()
print("PDF salvato con successo!")
