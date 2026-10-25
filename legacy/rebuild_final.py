import fitz, json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PDF_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf'
TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
OUT_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf'

with open(TR_PATH, 'r', encoding='utf-8') as f:
    translations = json.load(f)

doc = fitz.open(PDF_PATH)
total_pages = len(doc)

def pick_font(font_name):
    name = font_name.lower()
    if any(k in name for k in ['typewriter', 'courier', 'mono', 'ocr']):
        return 'cour'
    if any(k in name for k in ['serif', 'minion', 'times']):
        return 'tiro'
    return 'helv'

def to_rgb(c):
    return ((c>>16)&0xFF)/255.0, ((c>>8)&0xFF)/255.0, (c&0xFF)/255.0

def calc_scale(orig_len, trans_len):
    """Calculate font scale so translated text fits approximately same area."""
    if orig_len == 0:
        return 1.0
    ratio = trans_len / orig_len
    if ratio <= 1.05:
        return 1.0
    if ratio <= 1.15:
        return 0.97
    if ratio <= 1.30:
        return 0.92
    if ratio <= 1.50:
        return 0.86
    if ratio <= 1.80:
        return 0.80
    return 0.74

for page_num in range(total_pages):
    page = doc[page_num]
    blocks = page.get_text('dict')['blocks']
    
    # Gather text blocks with translation data
    tbs = []
    for idx, b in enumerate(blocks):
        if b['type'] != 0:
            continue
        content = ""
        spans = []
        for line in b['lines']:
            for sp in line['spans']:
                content += sp['text']
                spans.append(sp)
            content += "\n"
        content = content.strip()
        if not content:
            continue
        
        key = f"p{page_num+1}_b{idx}"
        tra = translations.get(key, {}).get('translated', '')
        if not tra:
            continue
        
        sp0 = spans[0]
        bbox = b['bbox']
        
        # Alignment: calculate block center vs page center
        block_cx = (bbox[0] + bbox[2]) / 2
        page_cx = (page.rect[0] + page.rect[2]) / 2
        diff = abs(block_cx - page_cx)
        
        if page_num < 5 and diff < 35:  # Title pages
            align = 1
        elif diff < 15:  # Truly centered
            align = 1
        elif block_cx > page_cx + 100:
            align = 2
        else:
            align = 0
        
        tbs.append({
            'idx': idx,
            'bbox': bbox,
            'orig': content,
            'trans': tra,
            'size': sp0['size'],
            'font': sp0.get('font', ''),
            'color': sp0.get('color', 0),
            'align': align,
        })
    
    if not tbs:
        continue
    
    # 1. Cover original text with white rectangles
    for tb in tbs:
        bbox = tb['bbox']
        page.draw_rect(
            fitz.Rect(bbox[0]-3, bbox[1]-2, bbox[2]+6, bbox[3]+3),
            color=None, fill=(1, 1, 1)
        )
    
    # 2. Insert translated text
    for tb in tbs:
        bbox = tb['bbox']
        rgb = to_rgb(tb['color'])
        font = pick_font(tb['font'])
        
        scale = calc_scale(len(tb['orig']), len(tb['trans']))
        fs = max(tb['size'] * scale, 5.5)
        
        w = (bbox[2] - bbox[0]) * 1.12
        h = (bbox[3] - bbox[1]) * 1.8
        rect = fitz.Rect(bbox[0], bbox[1], bbox[0]+w, bbox[1]+h)
        
        ok = False
        for mul in [1.0, 0.90, 0.82, 0.74, 0.66]:
            rc = page.insert_textbox(rect, tb['trans'],
                                    fontname=font,
                                    fontsize=fs * mul,
                                    color=rgb,
                                    align=tb['align'])
            if rc >= 0:
                ok = True
                break
    
    if (page_num+1) % 30 == 0:
        print(f"  {page_num+1}/{total_pages}")

doc.save(OUT_PATH, deflate=True, garbage=4)
doc.close()

mb = os.path.getsize(OUT_PATH) / 2**20
print(f"PDF: {OUT_PATH}")
print(f"Size: {mb:.1f} MB | Pages: {total_pages}")
