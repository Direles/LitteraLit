import fitz, json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PDF_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf'
TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
OUT_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf'

FONT_MAP = {
    'guardiansans': 'C:/Windows/Fonts/calibri.ttf',
    'urwtypewriter': 'C:/Windows/Fonts/consola.ttf',
    'minionpro': 'C:/Windows/Fonts/georgia.ttf',
    'myriadpro': 'C:/Windows/Fonts/segoeui.ttf',
    'helvetica': 'C:/Windows/Fonts/arial.ttf',
}

with open(TR_PATH, 'r', encoding='utf-8') as f:
    translations = json.load(f)

doc = fitz.open(PDF_PATH)
total_pages = len(doc)

def get_system_font(font_name):
    """Map original font to a similar system font."""
    name = font_name.lower()
    for key, path in FONT_MAP.items():
        if key in name and os.path.exists(path):
            return path
    # Default to Arial
    return 'C:/Windows/Fonts/arial.ttf'

def clr(c):
    return ((c>>16)&0xFF)/255, ((c>>8)&0xFF)/255, (c&0xFF)/255

# Track embedded fonts to avoid re-embedding
embedded_fonts = {}

for page_num in range(total_pages):
    page = doc[page_num]
    blocks = page.get_text('dict')['blocks']
    page_rect = page.rect
    page_width = page_rect[2] - page_rect[0]
    
    # Collect text blocks
    text_blocks = []
    for idx, b in enumerate(blocks):
        if b['type'] != 0:
            continue
        full_text = ""
        spans_info = []
        for line in b['lines']:
            for span in line['spans']:
                full_text += span['text']
                spans_info.append(span)
        if not full_text.strip():
            continue
        
        key = f"p{page_num+1}_b{idx}"
        t = translations.get(key, {}).get('translated', '')
        if not t:
            continue
        
        first_span = spans_info[0]
        bbox = b['bbox']
        block_center = (bbox[0] + bbox[2]) / 2
        page_center = page_width / 2
        
        # Detect alignment
        if abs(block_center - page_center) < 25:
            align = 1  # center
        elif block_center > page_center + 80:
            align = 2  # right
        else:
            align = 0  # left
        
        text_blocks.append({
            'bbox': bbox,
            'text': t,
            'orig_text': full_text.strip(),
            'size': first_span['size'],
            'font': first_span.get('font', 'helv'),
            'color': first_span.get('color', 0),
            'align': align,
        })
    
    if not text_blocks:
        continue
    
    # Step 1: Cover original text with white
    for tb in text_blocks:
        bbox = tb['bbox']
        page.draw_rect(
            fitz.Rect(bbox[0]-3, bbox[1]-2, bbox[2]+5, bbox[3]+3),
            color=None, fill=(1, 1, 1)
        )
    
    # Step 2: Insert translated text with embedded fonts
    for tb in text_blocks:
        bbox = tb['bbox']
        rgb = clr(tb['color'])
        
        # Get system font path
        font_path = get_system_font(tb['font'])
        font_basename = os.path.basename(font_path).replace('.ttf', '')
        
        # Embed font (lazy - only once per font)
        if font_path not in embedded_fonts:
            try:
                embedded_fonts[font_path] = page.insert_font(
                    fontname=font_basename,
                    fontfile=font_path
                )
            except Exception:
                embedded_fonts[font_path] = 'helv'  # fallback
        
        font_ref = embedded_fonts[font_path]
        
        # Calculate optimal font size based on text length
        orig_len = len(tb['orig_text'])
        trans_len = len(tb['text'])
        ratio = trans_len / max(orig_len, 1)
        
        if ratio <= 1.0:
            scale = 1.0
        elif ratio <= 1.2:
            scale = 0.95
        elif ratio <= 1.4:
            scale = 0.88
        elif ratio <= 1.7:
            scale = 0.80
        else:
            scale = 0.72
        
        font_size = max(tb['size'] * scale, 5)
        
        w = (bbox[2] - bbox[0]) * 1.1
        h = (bbox[3] - bbox[1]) * 1.5
        rect = fitz.Rect(bbox[0], bbox[1], bbox[0] + w, bbox[1] + h)
        
        rc = page.insert_textbox(rect, tb['text'],
                                fontname=font_ref,
                                fontsize=font_size,
                                color=rgb,
                                align=tb['align'])
        
        if rc < 0:
            for s in [0.85, 0.75, 0.65, 0.55]:
                rc = page.insert_textbox(rect, tb['text'],
                                        fontname=font_ref,
                                        fontsize=tb['size'] * s,
                                        color=rgb,
                                        align=tb['align'])
                if rc >= 0:
                    break
    
    if (page_num+1) % 25 == 0:
        print(f"Processate {page_num+1}/{total_pages} pagine...")

doc.save(OUT_PATH, deflate=True, garbage=3)
doc.close()

size_mb = os.path.getsize(OUT_PATH) / 1024 / 1024
print(f"\nPDF creato: {OUT_PATH} ({size_mb:.1f} MB)")
print(f"Pagine: {total_pages}")
print(f"Font incorporati: {len(embedded_fonts)}")
