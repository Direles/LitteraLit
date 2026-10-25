"""
High-quality PDF translation using image rendering approach.
Renders each page at 300 DPI, precisely covers text with background color,
and renders translated text with PIL at the exact positions.
"""
import fitz, json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image, ImageDraw, ImageFont
from collections import Counter

PDF_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf'
TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
OUT_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf'
DPI = 300

# Load fonts
FONT_REGULAR = "C:\\Windows\\Fonts\\calibri.ttf"
FONT_BOLD    = "C:\\Windows\\Fonts\\calibrib.ttf"
FONT_MONO    = "C:\\Windows\\Fonts\\consola.ttf"
FONT_SERIF   = "C:\\Windows\\Fonts\\georgia.ttf"

with open(TR_PATH, 'r', encoding='utf-8') as f:
    translations = json.load(f)

doc = fitz.open(PDF_PATH)
total_pages = len(doc)
zoom = DPI / 72.0

def get_font_for_block(span_font, font_size_px):
    """Pick the best font and size for the block."""
    name = span_font.lower()
    fs = max(int(font_size_px), 6)
    try:
        if any(k in name for k in ['typewriter', 'courier', 'mono', 'ocr']):
            return ImageFont.truetype(FONT_MONO, fs) if os.path.exists(FONT_MONO) else ImageFont.load_default()
        elif any(k in name for k in ['serif', 'minion', 'times']):
            return ImageFont.truetype(FONT_SERIF, fs) if os.path.exists(FONT_SERIF) else ImageFont.load_default()
        elif 'bold' in name or 'heavy' in name or 'black' in name or 'semibold' in name:
            return ImageFont.truetype(FONT_BOLD, fs) if os.path.exists(FONT_BOLD) else ImageFont.truetype(FONT_REGULAR, fs)
        else:
            return ImageFont.truetype(FONT_REGULAR, fs) if os.path.exists(FONT_REGULAR) else ImageFont.load_default()
    except:
        return ImageFont.load_default()

def get_background_color(img, bbox_scaled):
    """Sample the most common color in the area around the text block."""
    x0, y0, x1, y1 = bbox_scaled
    w, h = img.width, img.height
    colors = []
    
    # Sample pixels just outside the bounding box (top and left edges)
    margin = 2
    for x in range(max(0, x0 - 5), min(w, x1 + 1)):
        for y in range(max(0, y0 - 5), min(y0, h)):
            if 0 <= x < w and 0 <= y < h:
                colors.append(img.getpixel((x, y)))
    for x in range(max(0, x0 - 5), min(x0, w)):
        for y in range(max(0, y0), min(h, y1 + 1)):
            if 0 <= x < w and 0 <= y < h:
                colors.append(img.getpixel((x, y)))
    
    if not colors:
        return (255, 255, 255)
    
    # Most common color
    counter = Counter(colors)
    return counter.most_common(1)[0][0]

def calc_font_scale_v2(original_text, translated_text, block_width_px, font_size_px, font):
    """Calculate optimal font size to fit translated text."""
    if not original_text:
        return font_size_px
    
    # Measure original text width at original size
    try:
        orig_bbox = font.getbbox(original_text.replace('\n', ' '))
        orig_w = orig_bbox[2] - orig_bbox[0]
    except:
        return font_size_px * 0.85
    
    # Measure translated text
    try:
        trans_bbox = font.getbbox(translated_text.replace('\n', ' '))
        trans_w = trans_bbox[2] - trans_bbox[0]
    except:
        return font_size_px * 0.85
    
    if orig_w == 0:
        return font_size_px
    
    scale = orig_w / trans_w
    # Clamp scale
    scale = max(0.55, min(1.0, scale * 1.05))  # slight extra reduction
    return font_size_px * scale

for page_num in range(total_pages):
    page = doc[page_num]
    page_rect = page.rect
    
    # Render page as image
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    draw = ImageDraw.Draw(img)
    scale_x = img.width / page_rect.width
    scale_y = img.height / page_rect.height
    
    blocks = page.get_text('dict')['blocks']
    
    # Collect text blocks data
    text_blocks = []
    for idx, b in enumerate(blocks):
        if b['type'] != 0:
            continue
        content = ""
        first_span = None
        for line in b['lines']:
            for sp in line['spans']:
                content += sp['text']
                if first_span is None:
                    first_span = sp
        content = content.strip()
        if not content:
            continue
        
        key = f"p{page_num+1}_b{idx}"
        tra = translations.get(key, {}).get('translated', '')
        if not tra:
            continue
        
        bbox = b['bbox']
        # Scale bbox to image coords
        sx0 = int(bbox[0] * scale_x)
        sy0 = int(bbox[1] * scale_y)
        sx1 = int(bbox[2] * scale_x)
        sy1 = int(bbox[3] * scale_y)
        
        text_blocks.append({
            'bbox': bbox,
            'sbbox': (sx0, sy0, sx1, sy1),
            'orig': content,
            'trans': tra,
            'size_px': first_span['size'] * scale_y,
            'font_name': first_span.get('font', ''),
            'color': first_span.get('color', 0),
        })
    
    if not text_blocks:
        continue
    
    # 1. Cover text areas with background color
    for tb in text_blocks:
        sbbox = tb['sbbox']
        bg = get_background_color(img, sbbox)
        draw.rectangle([sbbox[0]-3, sbbox[1]-2, sbbox[2]+4, sbbox[3]+3], fill=bg)
    
    # 2. Draw translated text
    for tb in text_blocks:
        sbbox = tb['sbbox']
        sx0, sy0, sx1, sy1 = sbbox
        
        # Get font
        font_size_px = tb['size_px']
        font = get_font_for_block(tb['font_name'], font_size_px)
        
        # Calculate optimal font size
        optimal_size = calc_font_scale_v2(tb['orig'], tb['trans'], sx1 - sx0, font_size_px, font)
        font = get_font_for_block(tb['font_name'], optimal_size)
        
        # Text color
        color_int = tb['color']
        if color_int == 16777215:  # white
            text_rgb = (0, 0, 0)
        else:
            text_rgb = ((color_int>>16)&0xFF, (color_int>>8)&0xFF, color_int&0xFF)
        
        # Draw text line by line within the block
        block_w = sx1 - sx0 + 10  # slightly wider
        text = tb['trans']
        lines = text.split('\n')
        
        y = sy0
        for line in lines:
            if not line.strip():
                y += int(font_size_px * 0.8)
                continue
            
            # Word wrap: split long lines
            words = line.split(' ')
            current_line = ""
            
            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                try:
                    test_bbox = font.getbbox(test_line)
                    test_w = test_bbox[2] - test_bbox[0]
                except:
                    test_w = len(test_line) * font_size_px * 0.5
                
                if test_w > block_w and current_line:
                    draw.text((sx0, y), current_line, fill=text_rgb, font=font)
                    y += int(font_size_px * 1.35)
                    current_line = word
                else:
                    current_line = test_line
            
            if current_line:
                draw.text((sx0, y), current_line, fill=text_rgb, font=font)
                y += int(font_size_px * 1.35)
    
    # 3. Create PDF page from image
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    img_pix = fitz.Pixmap(buf.read())
    new_page = doc.new_page(pno=page_num, width=page_rect.width, height=page_rect.height)
    new_page.insert_image(page_rect, pixmap=img_pix)
    
    if (page_num+1) % 20 == 0:
        print(f"  {page_num+1}/{total_pages}")

OUT_PATH2 = OUT_PATH.replace('.pdf', '_HQ.pdf')
doc.save(OUT_PATH2, deflate=True, garbage=4)
doc.close()

mb = os.path.getsize(OUT_PATH2) / 2**20
print(f"PDF HQ: {OUT_PATH2} ({mb:.1f} MB)")
