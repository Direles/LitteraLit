import fitz, json, sys, io, os, re
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image, ImageDraw, ImageFont

PDF_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf'
TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
OUT_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf'

FONTS = {
    'regular': 'C:/Windows/Fonts/calibri.ttf',
    'bold': 'C:/Windows/Fonts/calibrib.ttf',
    'mono': 'C:/Windows/Fonts/consola.ttf',
    'serif': 'C:/Windows/Fonts/georgia.ttf',
}

with open(TR_PATH, 'r', encoding='utf-8') as f:
    translations = json.load(f)

doc = fitz.open(PDF_PATH)
TP = len(doc)
new_doc = fitz.open()
ZOOM = 300/72  # 300 DPI

def clean_text(t):
    t = t.replace('\u201c','"').replace('\u201d','"').replace('\u2018',"'").replace('\u2019',"'")
    t = t.replace('\u2013','-').replace('\u2014','--').replace('\u2026','...')
    t = t.replace('\u00a0',' ').replace('\u25a0','')
    # Keep only printable Latin-1 + common Unicode
    t = re.sub(r'[^\x20-\x7E\xA0-\xFF\u0152\u0153\u0160\u0161\u0178\u0192\u02C6\u02DC\u2010\u2012\u2020\u2021\u2022\u2030\u2032\u2033\u2039\u203A\u20AC\u2122]', '', t)
    return t

def pick_font(fn, px_size):
    n = fn.lower()
    fs = max(int(px_size), 6)
    try:
        if any(k in n for k in ['typewriter','courier','mono','ocr']):
            return ImageFont.truetype(FONTS['mono'], fs)
        elif any(k in n for k in ['serif','minion','times']):
            return ImageFont.truetype(FONTS['serif'], fs)
        elif 'bold' in n or 'semibold' in n or 'heavy' in n:
            return ImageFont.truetype(FONTS['bold'], fs)
        else:
            return ImageFont.truetype(FONTS['regular'], fs)
    except:
        return ImageFont.load_default()

def sample_bg(img, sx0, sy0, sx1, sy1):
    w, h = img.width, img.height
    colors = []
    m = 6
    for x in range(max(0,sx0-m), min(w,sx1+m), 2):
        for y in range(max(0,sy0-m-3), min(sy0+1,h), 2):
            if 0<=x<w and 0<=y<h: colors.append(img.getpixel((x,y)))
    if not colors:
        return (255,255,255)
    return Counter(colors).most_common(1)[0][0]

def wrap_text(text, font, max_width):
    """Wrap text to fit within max_width pixels."""
    words = text.split(' ')
    lines = []
    current = ""
    for word in words:
        test = current + (" " if current else "") + word
        try: bbox = font.getbbox(test)
        except: bbox = [0,0,len(test)*10,20]
        w = bbox[2] - bbox[0]
        if w > max_width and current:
            lines.append(current)
            current = word
        else:
            current = test
    if current:
        lines.append(current)
    return lines

for pg_num in range(TP):
    page = doc[pg_num]
    page_rect = page.rect
    blocks = page.get_text('dict')['blocks']
    
    # Render page image
    pix = page.get_pixmap(matrix=fitz.Matrix(ZOOM, ZOOM))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    draw = ImageDraw.Draw(img)
    sx = img.width / page_rect.width   # scale x
    sy = img.height / page_rect.height  # scale y
    
    img_rects = []
    tbs = []
    
    for idx, b in enumerate(blocks):
        if b['type'] == 1:
            img_rects.append(fitz.Rect(b['bbox']))
            continue
        
        content = ""
        spans = []
        for line in b['lines']:
            for sp in line['spans']:
                content += sp['text']
                spans.append(sp)
            content += "\n"
        content = content.strip()
        if not content: continue
        
        key = f"p{pg_num+1}_b{idx}"
        tra = translations.get(key, {}).get('translated', '')
        if not tra: continue
        tra = clean_text(tra)
        
        sp0 = spans[0]
        rect = fitz.Rect(b['bbox'])
        
        overlaps = False
        for ir in img_rects:
            if rect.intersects(ir):
                inter = rect & ir
                if abs(inter) > 0.2 * abs(rect):
                    overlaps = True
                    break
        
        # Scaled coordinates
        sx0 = int(rect.x0 * sx)
        sy0 = int(rect.y0 * sy)
        sx1 = int(rect.x1 * sx)
        sy1 = int(rect.y1 * sy)
        
        tbs.append({
            'sx0': sx0, 'sy0': sy0, 'sx1': sx1, 'sy1': sy1,
            'orig': content, 'trans': tra,
            'size_pt': sp0['size'],
            'font': sp0.get('font',''),
            'color': sp0.get('color',0),
            'overlaps': overlaps,
        })
    
    if not tbs: 
        # Add page as-is
        new_page = new_doc.new_page(width=page_rect.width, height=page_rect.height)
        buf = io.BytesIO()
        img.save(buf, format='PNG')
        buf.seek(0)
        new_page.insert_image(page_rect, pixmap=fitz.Pixmap(buf.read()))
        continue
    
    # Sort by Y
    tbs.sort(key=lambda x: x['sy0'])
    
    for i, tb in enumerate(tbs):
        mb = img.height
        for j in range(i+1, len(tbs)):
            o = tbs[j]
            if o['sy0'] > tb['sy1'] + 5:
                mb = min(mb, o['sy0'])
                break
        tb['max_y'] = mb - 3
    
    # 1. Cover text with background color
    for tb in tbs:
        sx0, sy0, sx1, sy1 = tb['sx0'], tb['sy0'], tb['sx1'], tb['sy1']
        bg = sample_bg(img, sx0, sy0, sx1, sy1)
        draw.rectangle([sx0-3, sy0-3, sx1+5, sy1+4], fill=bg)
    
    # 2. Draw translated text line by line with precise spacing
    for tb in tbs:
        sx0, sy0, sx1, sy1 = tb['sx0'], tb['sy0'], tb['sx1'], tb['sy1']
        
        px_size = tb['size_pt'] * sy  # convert pt to pixels
        font = pick_font(tb['font'], px_size)
        
        color_int = tb['color']
        if color_int == 16777215: color_int = 0
        text_rgb = ((color_int>>16)&0xFF, (color_int>>8)&0xFF, color_int&0xFF)
        
        avail_w = sx1 - sx0 + 10
        avail_h = tb['max_y'] - sy0
        
        # Wrap text
        lines = []
        for paragraph in tb['trans'].split('\n'):
            if paragraph.strip():
                lines.extend(wrap_text(paragraph, font, avail_w))
            else:
                lines.append('')
        
        # Calculate font size needed to fit all lines
        line_height = int(px_size * 1.25)
        needed_h = len(lines) * line_height
        
        # Scale down if needed
        if needed_h > avail_h and px_size > 6:
            scale = min(1.0, avail_h / needed_h) * 0.95
            new_px = max(int(px_size * scale), 6)
            font = pick_font(tb['font'], new_px)
            line_height = int(new_px * 1.25)
            
            # Re-wrap with new font
            lines = []
            for paragraph in tb['trans'].split('\n'):
                if paragraph.strip():
                    lines.extend(wrap_text(paragraph, font, avail_w))
                else:
                    lines.append('')
        
        # Draw each line
        y = sy0
        for line in lines:
            if line.strip():
                draw.text((sx0, y), line, fill=text_rgb, font=font)
            y += line_height
    
    # Create PDF page
    buf = io.BytesIO()
    img.save(buf, format='PNG', optimize=True)
    buf.seek(0)
    pix_out = fitz.Pixmap(buf.read())
    new_page = new_doc.new_page(width=page_rect.width, height=page_rect.height)
    new_page.insert_image(page_rect, pixmap=pix_out)
    
    if (pg_num+1) % 25 == 0:
        print(f"  {pg_num+1}/{TP}")

new_doc.save(OUT_PATH, deflate=True, garbage=4)
new_doc.close()
doc.close()
mb = os.path.getsize(OUT_PATH) / 2**20
print(f"\nPDF: {OUT_PATH} ({mb:.1f} MB)")
