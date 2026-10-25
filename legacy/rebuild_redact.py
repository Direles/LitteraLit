import fitz, json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PDF_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf'
TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
OUT_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO_v2.pdf'

with open(TR_PATH, 'r', encoding='utf-8') as f:
    translations = json.load(f)

doc = fitz.open(PDF_PATH)
total_pages = len(doc)

def pick_font(font_name):
    n = font_name.lower()
    if any(k in n for k in ['typewriter', 'courier', 'mono', 'ocr']):
        return 'cour'
    if any(k in n for k in ['serif', 'minion', 'times']):
        return 'tiro'
    return 'helv'

def to_rgb(c):
    r = (c >> 16) & 0xFF
    g = (c >> 8) & 0xFF
    b = c & 0xFF
    return r/255, g/255, b/255

for page_num in range(total_pages):
    page = doc[page_num]
    blocks = page.get_text('dict')['blocks']
    pw = page.rect.width
    pcx = pw / 2
    
    # Collect text blocks
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
        
        # Alignment
        bcx = (bbox[0] + bbox[2]) / 2
        if abs(bcx - pcx) < 20:
            align = 1
        elif bcx > pcx + 80:
            align = 2
        else:
            align = 0
        
        tbs.append({
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
    
    # Step 1: Mark text areas for redaction (exact bbox, white fill)
    for tb in tbs:
        bbox = tb['bbox']
        page.add_redact_annot(
            fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3]),
            fill=(1, 1, 1)
        )
    
    # Step 2: Apply redactions (physically removes original text)
    page.apply_redactions()
    
    # Step 3: Insert translated text
    for tb in tbs:
        bbox = tb['bbox']
        rgb = to_rgb(tb['color'])
        font = pick_font(tb['font'])
        
        orig_w = bbox[2] - bbox[0]
        orig_h = bbox[3] - bbox[1]
        orig_len = len(tb['orig'])
        trans_len = len(tb['trans'])
        
        # Calculate width: original width * 1.3 or based on text length
        ratio = trans_len / max(orig_len, 1)
        
        # Give more width for Italian text
        if ratio > 1.3:
            box_w = orig_w * 1.5
        elif ratio > 1.1:
            box_w = orig_w * 1.35
        else:
            box_w = orig_w * 1.2
        
        # Give ample height for wrapping
        box_h = orig_h * 2.5
        
        # Don't exceed page boundaries
        max_w = page.rect.width - bbox[0] - 5
        box_w = min(box_w, max_w)
        
        rect = fitz.Rect(bbox[0], bbox[1], bbox[0] + box_w, bbox[1] + box_h)
        
        # Font size: try original first, then reduce
        for scale in [0.95, 0.88, 0.82, 0.75, 0.68, 0.62]:
            fs = max(tb['size'] * scale, 5.5)
            rc = page.insert_textbox(
                rect, tb['trans'],
                fontname=font,
                fontsize=fs,
                color=rgb,
                align=tb['align']
            )
            if rc >= 0:
                break
    
    if (page_num+1) % 30 == 0:
        print(f"  {page_num+1}/{total_pages}")

doc.save(OUT_PATH, deflate=True, garbage=4)
doc.close()

mb = os.path.getsize(OUT_PATH) / 2**20
print(f"PDF: {OUT_PATH}")
print(f"Size: {mb:.1f} MB | Pages: {total_pages}")
