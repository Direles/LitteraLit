import fitz, json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PDF_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf'
TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
OUT_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf'

with open(TR_PATH, 'r', encoding='utf-8') as f:
    translations = json.load(f)

doc = fitz.open(PDF_PATH)

def pick_font(fn):
    n = fn.lower()
    if any(k in n for k in ['typewriter','courier','mono','ocr']): return 'cour'
    if any(k in n for k in ['serif','minion','times']): return 'tiro'
    return 'helv'

def to_rgb(c):
    return ((c>>16)&0xFF)/255, ((c>>8)&0xFF)/255, (c&0xFF)/255

for pg_num in range(len(doc)):
    page = doc[pg_num]
    blocks = page.get_text('dict')['blocks']
    
    # Collect text blocks with full data
    tbs = []
    for idx, b in enumerate(blocks):
        if b['type'] != 0: continue
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
        bbox = b['bbox']
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        
        tbs.append({
            'bbox': bbox,
            'w': w, 'h': h,
            'y0': bbox[1], 'y1': bbox[3],
            'x0': bbox[0], 'x1': bbox[2],
            'orig': content,
            'trans': tra,
            'size': sp0['size'],
            'font': sp0.get('font', ''),
            'color': sp0.get('color', 0),
        })
    
    if not tbs: continue
    
    # Sort by vertical position (top to bottom)
    tbs.sort(key=lambda x: x['y0'])
    
    # Calculate available vertical space for each block
    page_bottom = page.rect[3]
    for i, tb in enumerate(tbs):
        # Find next block that's significantly below this one
        # (different row, not same line in different column)
        next_y = page_bottom
        for j in range(i+1, len(tbs)):
            other = tbs[j]
            # If the other block starts below this block's end, it's the next row
            if other['y0'] > tb['y1'] + 2:
                next_y = min(next_y, other['y0'])
                break
        tb['max_bottom'] = next_y - 2  # small margin
    
    # 1. Redact original text
    for tb in tbs:
        bbox = tb['bbox']
        page.add_redact_annot(fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3]), fill=(1,1,1))
    
    page.apply_redactions()
    
    # 2. Insert translated text with proper sizing
    for tb in tbs:
        rgb = to_rgb(tb['color'])
        font = pick_font(tb['font'])
        
        # Available space for this block
        avail_w = tb['w']
        avail_h = tb['max_bottom'] - tb['y0']  # how much vertical space we have
        
        # Textbox rect: use original width, constrain height to available space
        rect = fitz.Rect(tb['x0'], tb['y0'], tb['x0'] + avail_w, tb['y0'] + avail_h)
        
        # Try increasingly smaller font sizes until text fits
        best_rc = -1
        best_size = tb['size'] * 0.65  # fallback
        
        for scale in [1.0, 0.95, 0.90, 0.85, 0.80, 0.75, 0.70, 0.65, 0.60, 0.55]:
            fs = max(tb['size'] * scale, 5.5)
            rc = page.insert_textbox(rect, tb['trans'],
                                    fontname=font, fontsize=fs,
                                    color=rgb, align=0)
            if rc >= 0:  # all text fit
                best_size = fs
                best_rc = rc
                break
            # If rc < 0, text didn't fit - try smaller
        
        # If even smallest didn't fit, use the smallest
        if best_rc < 0:
            page.insert_textbox(rect, tb['trans'],
                               fontname=font, fontsize=5.5,
                               color=rgb, align=0)
    
    if (pg_num+1) % 30 == 0:
        print(f"  {pg_num+1}/{len(doc)}")

doc.save(OUT_PATH, deflate=True, garbage=4)
doc.close()
mb = os.path.getsize(OUT_PATH) / 2**20
print(f"\nPDF: {OUT_PATH} ({mb:.1f} MB)")
