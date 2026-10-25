import fitz, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image, ImageDraw, ImageFont

PDF_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf'
TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
OUT_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf'
FONT_PATH = "C:\\Windows\\Fonts\\arial.ttf"
DPI = 200

with open(TR_PATH, 'r', encoding='utf-8') as f:
    translations = json.load(f)

doc = fitz.open(PDF_PATH)
new_doc = fitz.open()
zoom = DPI / 72

def hex_from_color(color_int):
    if color_int == 16777215:
        return '#000000'
    return f'#{color_int:06x}'

total_pages = len(doc)
processed = 0

for page_num in range(total_pages):
    page = doc[page_num]
    page_rect = page.rect

    # Render page as image at DPI
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    draw = ImageDraw.Draw(img)
    scale_x = img.width / page_rect.width
    scale_y = img.height / page_rect.height

    blocks = page.get_text('dict')['blocks']

    # First pass: cover text areas with white
    for idx, b in enumerate(blocks):
        if b['type'] != 0:
            continue
        full_text = ""
        for line in b['lines']:
            for span in line['spans']:
                full_text += span['text']
        full_text = full_text.strip()
        if not full_text:
            continue

        bbox = b['bbox']
        x0 = int(bbox[0] * scale_x) - 2
        y0 = int(bbox[1] * scale_y) - 2
        x1 = int(bbox[2] * scale_x) + 2
        y1 = int(bbox[3] * scale_y) + 2
        draw.rectangle([x0, y0, x1, y1], fill='white')

    # Second pass: add translated text
    for idx, b in enumerate(blocks):
        if b['type'] != 0:
            continue
        key = f"p{page_num+1}_b{idx}"

        full_text = ""
        for line in b['lines']:
            for span in line['spans']:
                full_text += span['text']
        full_text = full_text.strip()
        if not full_text:
            continue

        translated = translations.get(key, {}).get('translated', '')
        text_to_show = translated if translated else full_text

        bbox = b['bbox']
        x0 = int(bbox[0] * scale_x)
        y0 = int(bbox[1] * scale_y)

        first_span = b['lines'][0]['spans'][0]
        font_size = first_span['size'] * scale_y * 0.75
        color = first_span.get('color', 0)

        try:
            font = ImageFont.truetype(FONT_PATH, max(int(font_size), 6))
        except:
            font = ImageFont.load_default()

        text_color = hex_from_color(color)
        if text_color == '#ffffff':
            text_color = '#000000'

        lines_text = text_to_show.split('\n')
        y_pos = y0
        line_height = int(font_size * 1.4)

        for line_text in lines_text:
            if line_text.strip():
                draw.text((x0, y_pos), line_text, fill=text_color, font=font)
            y_pos += line_height

    # Convert PIL image to bytes and insert into new PDF
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    img_pix = fitz.Pixmap(img_bytes.read())
    new_page = new_doc.new_page(width=page_rect.width, height=page_rect.height)
    new_page.insert_image(page_rect, pixmap=img_pix)

    processed += 1
    if processed % 20 == 0:
        print(f"Processate {processed}/{total_pages} pagine...")

new_doc.save(OUT_PATH)
new_doc.close()
doc.close()
print(f"\nPDF creato: {OUT_PATH}")
print(f"Pagine processate: {processed}")
