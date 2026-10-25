import fitz, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "C:\\Windows\\Fonts\\arial.ttf"
OUT = r'C:\Users\anton\Desktop\traduzione libri\test_output'
os.makedirs(OUT, exist_ok=True)

doc = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf')
page = doc[1]  # Page 2
page_rect = page.rect

# Render page at 300 DPI
zoom = 300 / 72
pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
draw = ImageDraw.Draw(img)
scale_x = img.width / page_rect.width
scale_y = img.height / page_rect.height

blocks = page.get_text('dict')['blocks']
text_blocks = [b for b in blocks if b['type'] == 0]

# Cover all text regions with white and add placeholder
for i, b in enumerate(text_blocks):
    full_text = ""
    for line in b['lines']:
        for span in line['spans']:
            full_text += span['text']
    full_text = full_text.strip()
    if not full_text:
        continue
    
    bbox = b['bbox']
    x0 = int(bbox[0] * scale_x) - 1
    y0 = int(bbox[1] * scale_y) - 1
    x1 = int(bbox[2] * scale_x) + 1
    y1 = int(bbox[3] * scale_y) + 1
    
    # Cover with white
    draw.rectangle([x0, y0, x1, y1], fill='white')
    
    # Get font info
    first_span = b['lines'][0]['spans'][0]
    font_size = max(first_span['size'] * scale_y * 0.8, 6)
    color_hex = f"#{first_span['color']:06x}"
    
    try:
        font = ImageFont.truetype(FONT_PATH, int(font_size))
    except:
        font = ImageFont.load_default()
    
    # Write placeholder Italian text
    placeholder = f"[IT] {full_text[:50].rstrip(chr(10))}"
    draw.text((x0, y0), placeholder, fill=color_hex, font=font)

img.save(os.path.join(OUT, 'page2_test.png'))
print(f"Saved test to {os.path.join(OUT, 'page2_test.png')}")
print(f"Image size: {img.size}")
print(f"Processed {len(text_blocks)} text blocks")

doc.close()
