import fitz, json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PDF_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf'
TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
OUT_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf'

with open(TR_PATH, 'r', encoding='utf-8') as f:
    translations = json.load(f)

doc = fitz.open(PDF_PATH)
total_pages = len(doc)

def get_pymupdf_font(font_name):
    name = font_name.lower()
    if any(k in name for k in ['typewriter', 'courier', 'mono', 'ocr']):
        return 'cour'
    elif any(k in name for k in ['serif', 'minion', 'times', 'myriad']):
        return 'tiro'
    return 'helv'

def rgb_from_int(c):
    return ((c >> 16) & 0xFF) / 255, ((c >> 8) & 0xFF) / 255, (c & 0xFF) / 255

for page_num in range(total_pages):
    page = doc[page_num]
    blocks = page.get_text('dict')['blocks']
    
    # Collect data for text blocks before redaction
    text_blocks = []
    for idx, b in enumerate(blocks):
        if b['type'] != 0:
            continue
        full_text = ""
        for line in b['lines']:
            for span in line['spans']:
                full_text += span['text']
        if not full_text.strip():
            continue
        
        key = f"p{page_num+1}_b{idx}"
        translated = translations.get(key, {}).get('translated', '')
        if not translated:
            continue
        
        first_span = b['lines'][0]['spans'][0]
        text_blocks.append({
            'idx': idx,
            'bbox': b['bbox'],
            'translated': translated,
            'orig_size': first_span['size'],
            'font': first_span.get('font', 'helv'),
            'color': first_span.get('color', 0),
        })
    
    if not text_blocks:
        continue
    
    # Step 1: Redact (remove original text + fill with white)
    for tb in text_blocks:
        bbox = tb['bbox']
        r = fitz.Rect(bbox[0] - 1, bbox[1] - 1, bbox[2] + 1, bbox[3] + 1)
        page.add_redact_annot(r, fill=(1, 1, 1))
    
    page.apply_redactions()
    
    # Step 2: Insert translated text
    for tb in text_blocks:
        bbox = tb['bbox']
        orig_size = tb['orig_size']
        color_rgb = rgb_from_int(tb['color'])
        if color_rgb == (1, 1, 1):  # white text -> black
            color_rgb = (0, 0, 0)
        
        font = get_pymupdf_font(tb['font'])
        
        # Calculate textbox dimensions with room for Italian text
        box_w = (bbox[2] - bbox[0]) * 1.15  # 15% wider
        box_h = (bbox[3] - bbox[1]) * 1.5   # 50% taller
        rect = fitz.Rect(bbox[0], bbox[1], bbox[0] + box_w, bbox[1] + box_h)
        
        # Try inserting with decreasing font sizes
        done = False
        for scale in [0.9, 0.8, 0.7, 0.6]:
            rc = page.insert_textbox(rect, tb['translated'],
                                    fontname=font,
                                    fontsize=orig_size * scale,
                                    color=color_rgb,
                                    align=0)
            if rc >= 0:
                done = True
                break
        
        if not done:
            # Last resort with minimum size
            page.insert_textbox(rect, tb['translated'],
                              fontname=font,
                              fontsize=max(orig_size * 0.5, 5),
                              color=color_rgb)
    
    if (page_num + 1) % 25 == 0:
        print(f"Processate {page_num + 1}/{total_pages} pagine...")

OUT_PATH_TEMP = OUT_PATH
doc.save(OUT_PATH_TEMP, deflate=True, garbage=4)
doc.close()

print(f"\nPDF creato: {OUT_PATH_TEMP}")
print(f"Pagine processate: {total_pages}")

size_mb = os.path.getsize(OUT_PATH_TEMP) / 1024 / 1024
print(f"Dimensione: {size_mb:.1f} MB")
