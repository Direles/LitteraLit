import fitz, json, sys, io, os
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from PIL import Image as PILImage

PDF_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf'
TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
OUT_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf'

with open(TR_PATH, 'r', encoding='utf-8') as f:
    translations = json.load(f)

doc = fitz.open(PDF_PATH)
TP = len(doc)

def pf(fn):
    n = fn.lower()
    if any(k in n for k in ['typewriter','courier','mono','ocr']): return 'cour'
    if any(k in n for k in ['serif','minion','times']): return 'tiro'
    return 'helv'

def to_rgb(c):
    return ((c>>16)&0xFF)/255, ((c>>8)&0xFF)/255, (c&0xFF)/255

def sample_bg_from_pix(pix, rect, scale=1.5):
    """Sample the most common color in pixels just outside the text rectangle."""
    img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
    x0 = int(rect.x0 * scale)
    y0 = int(rect.y0 * scale)
    x1 = int(rect.x1 * scale)
    y1 = int(rect.y1 * scale)
    w, h = img.width, img.height
    colors = []
    m = 4  # margin
    # Top strip
    for x in range(max(0,x0), min(w,x1)):
        for y in range(max(0,y0-m), min(y0,h)):
            if 0<=x<w and 0<=y<h:
                colors.append(img.getpixel((x,y)))
    # Left strip  
    for x in range(max(0,x0-m), min(x0,w)):
        for y in range(max(0,y0), min(h,y1)):
            if 0<=x<w and 0<=y<h:
                colors.append(img.getpixel((x,y)))
    if not colors:
        return (255, 255, 255)
    c = Counter(colors)
    return c.most_common(1)[0][0]

for pg_num in range(TP):
    page = doc[pg_num]
    blocks = page.get_text('dict')['blocks']
    
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
        
        sp0 = spans[0]
        rect = fitz.Rect(b['bbox'])
        
        overlaps = False
        for ir in img_rects:
            if rect.intersects(ir):
                inter = rect & ir
                if abs(inter) > 0.3 * abs(rect):
                    overlaps = True
                    break
        
        tbs.append({
            'rect': rect,
            'orig': content,
            'trans': tra,
            'size': sp0['size'],
            'font': sp0.get('font', ''),
            'color': sp0.get('color', 0),
            'overlaps': overlaps,
        })
    
    if not tbs: continue
    
    # Render once for bg sampling
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    
    # Sort top to bottom
    tbs.sort(key=lambda x: x['rect'].y0)
    
    # Max available bottom for each block
    for i, tb in enumerate(tbs):
        mb = page.rect.y1
        for j in range(i+1, len(tbs)):
            o = tbs[j]
            if o['rect'].y0 > tb['rect'].y1 + 2:
                mb = min(mb, o['rect'].y0)
                break
        tb['max_y'] = mb - 2
    
    # 1. Remove original text
    for tb in tbs:
        r = tb['rect']
        if tb['overlaps']:
            # Text on image: cover with background color, don't redact
            bg = sample_bg_from_pix(pix, r, 1.5)
            bg_n = (bg[0]/255, bg[1]/255, bg[2]/255)
            page.draw_rect(
                fitz.Rect(r.x0-2, r.y0-2, r.x1+4, r.y1+3),
                color=None, fill=bg_n
            )
        else:
            # Clean redaction
            page.add_redact_annot(
                fitz.Rect(r.x0, r.y0, r.x1, r.y1),
                fill=(1, 1, 1)
            )
    
    page.apply_redactions()
    
    # 2. Insert translated text
    for tb in tbs:
        rgb = to_rgb(tb['color'])
        font = pf(tb['font'])
        
        avail_w = tb['rect'].width
        avail_h = tb['max_y'] - tb['rect'].y0
        
        rect = fitz.Rect(tb['rect'].x0, tb['rect'].y0,
                        tb['rect'].x0 + avail_w,
                        tb['rect'].y0 + avail_h)
        
        for scale in [1.0, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65]:
            fs = max(tb['size'] * scale, 5.5)
            rc = page.insert_textbox(rect, tb['trans'],
                                    fontname=font, fontsize=fs,
                                    color=rgb, align=0)
            if rc >= 0: break
    
    if (pg_num+1) % 30 == 0:
        print(f"  {pg_num+1}/{TP}")

doc.save(OUT_PATH, deflate=True, garbage=4)
doc.close()
mb = os.path.getsize(OUT_PATH) / 2**20
print(f"\nPDF: {OUT_PATH} ({mb:.1f} MB)")
