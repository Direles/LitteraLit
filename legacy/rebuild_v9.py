import fitz, json, sys, io, os, re
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

def clean_text(t):
    """Replace special Unicode chars that PDF base fonts can't render."""
    t = t.replace('\u201c', '"')  # left double quote
    t = t.replace('\u201d', '"')  # right double quote
    t = t.replace('\u2018', "'")  # left single quote
    t = t.replace('\u2019', "'")  # right single quote
    t = t.replace('\u2013', '-')  # en dash
    t = t.replace('\u2014', '--') # em dash
    t = t.replace('\u2026', '...') # ellipsis
    t = t.replace('\u00a0', ' ')  # non-breaking space
    t = t.replace('\u25a0', '')   # black square bullet
    # Remove other common problematic chars
    t = re.sub(r'[^\x20-\x7E\xA0-\xFF\u0152\u0153\u0160\u0161\u0178\u0192\u02C6\u02DC\u2010\u2012\u2020\u2021\u2022\u2030\u2032\u2033\u2039\u203A\u20AC\u2122]', '', t)
    return t

def sample_bg(pix, rect, scale=1.5):
    img = PILImage.frombytes("RGB", [pix.width, pix.height], pix.samples)
    x0, y0 = int(rect.x0*scale), int(rect.y0*scale)
    x1, y1 = int(rect.x1*scale), int(rect.y1*scale)
    w, h = img.width, img.height
    colors = []
    m = 5
    for x in range(max(0,x0-m), min(w,x1+m)):
        for y in range(max(0,y0-m-2), min(y0+1,h)):
            if 0<=x<w and 0<=y<h: colors.append(img.getpixel((x,y)))
    if not colors:
        return (255,255,255)
    return Counter(colors).most_common(1)[0][0]

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
        
        tra = clean_text(tra)  # CLEAN special chars
        
        sp0 = spans[0]
        rect = fitz.Rect(b['bbox'])
        
        overlaps = False
        for ir in img_rects:
            if rect.intersects(ir):
                inter = rect & ir
                if abs(inter) > 0.2 * abs(rect):
                    overlaps = True
                    break
        
        tbs.append({
            'rect': rect,
            'orig': content,
            'trans': clean_text(tra),
            'size': sp0['size'],
            'font': sp0.get('font',''),
            'color': sp0.get('color',0),
            'overlaps': overlaps,
        })
    
    if not tbs: continue
    
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5,1.5))
    
    tbs.sort(key=lambda x: x['rect'].y0)
    
    for i, tb in enumerate(tbs):
        mb = page.rect.y1
        for j in range(i+1, len(tbs)):
            o = tbs[j]
            if o['rect'].y0 > tb['rect'].y1 + 3:
                mb = min(mb, o['rect'].y0)
                break
        tb['max_y'] = mb - 3
    
    # 1. Remove original text
    for tb in tbs:
        r = tb['rect']
        if tb['overlaps']:
            bg = sample_bg(pix, r, 1.5)
            bg_n = (bg[0]/255, bg[1]/255, bg[2]/255)
            page.draw_rect(fitz.Rect(r.x0-3,r.y0-3,r.x1+5,r.y1+4),
                          color=None, fill=bg_n)
        else:
            page.add_redact_annot(
                fitz.Rect(r.x0, r.y0, r.x1, r.y1),
                fill=(1,1,1)
            )
    
    page.apply_redactions()
    
    # 2. Insert translated text
    for tb in tbs:
        rgb = to_rgb(tb['color'])
        if sum(rgb) == 0: rgb = (0,0,0)
        font = pf(tb['font'])
        
        avail_w = tb['rect'].width
        avail_h = tb['max_y'] - tb['rect'].y0
        
        rect = fitz.Rect(tb['rect'].x0, tb['rect'].y0,
                        tb['rect'].x0 + avail_w,
                        tb['rect'].y0 + avail_h)
        
        ok = False
        for scale in [1.0, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65]:
            fs = max(tb['size'] * scale, 6)
            rc = page.insert_textbox(rect, tb['trans'],
                                    fontname=font, fontsize=fs,
                                    color=rgb, align=0)
            if rc >= 0:
                ok = True
                break
        if not ok:
            page.insert_textbox(rect, tb['trans'],
                              fontname=font, fontsize=6,
                              color=rgb, align=0)
    
    if (pg_num+1) % 30 == 0:
        print(f"  {pg_num+1}/{TP}")

doc.save(OUT_PATH, deflate=True, garbage=4)
doc.close()
mb = os.path.getsize(OUT_PATH) / 2**20
print(f"\nPDF: {OUT_PATH} ({mb:.1f} MB)")
