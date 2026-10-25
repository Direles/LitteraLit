import fitz, json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PDF_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf'
TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
OUT_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf'

with open(TR_PATH, 'r', encoding='utf-8') as f:
    translations = json.load(f)

doc = fitz.open(PDF_PATH)
total_pages = len(doc)

def get_font(font_name):
    name = font_name.lower()
    if any(k in name for k in ['typewriter', 'courier', 'mono', 'ocr']):
        return 'cour'
    if any(k in name for k in ['serif', 'minion', 'times']):
        return 'tiro'
    return 'helv'

def clr(c):
    return ((c>>16)&0xFF)/255, ((c>>8)&0xFF)/255, (c&0xFF)/255

def is_light(rgb):
    """Check if color is light (close to white)"""
    luminance = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    return luminance > 0.7

# Pre-calculate page background colors by sampling corners
PAGE_BG = {}
print("Campionamento sfondi pagina...")
for pg in range(total_pages):
    page = doc[pg]
    pix = page.get_pixmap(dpi=72)
    # Sample 4 corners to determine page bg color
    w, h = pix.width, pix.height
    corners = [(2, 2), (w-3, 2), (2, h-3), (w-3, h-3)]
    samples = []
    for cx, cy in corners:
        offset = (cy * w + cx) * pix.n
        if pix.n >= 3:
            samples.append((pix.samples[offset], pix.samples[offset+1], pix.samples[offset+2]))
    # Average the corner samples
    avg = tuple(sum(s[i] for s in samples)//len(samples)/255.0 for i in range(3))
    PAGE_BG[pg] = avg

print(f"Sfondi campionati per {len(PAGE_BG)} pagine")

for page_num in range(total_pages):
    page = doc[page_num]
    blocks = page.get_text('dict')['blocks']
    page_rect = page.rect
    bg_color = PAGE_BG.get(page_num, (1, 1, 1))
    
    # Collect text blocks data
    text_blocks = []
    for idx, b in enumerate(blocks):
        if b['type'] != 0:
            continue
        full_text = ""
        spans_info = []
        for line in b['lines']:
            line_text = ""
            for span in line['spans']:
                line_text += span['text']
                spans_info.append(span)
            full_text += line_text + "\n"
        if not full_text.strip():
            continue
        
        key = f"p{page_num+1}_b{idx}"
        t = translations.get(key, {}).get('translated', '')
        if not t:
            continue
        
        # Calculate center positions to detect alignment
        first_span = spans_info[0]
        bbox = b['bbox']
        block_center = (bbox[0] + bbox[2]) / 2
        page_center = (page_rect[0] + page_rect[2]) / 2
        span_center = (first_span['bbox'][0] + first_span['bbox'][2]) / 2
        
        # Detect alignment
        if abs(block_center - page_center) < 20:  # roughly centered
            align = 1  # center
        elif abs(block_center - (page_center * 1.8)) < 30:  # right side
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
    
    # Step 1: Cover original text with background-colored rectangles
    for tb in text_blocks:
        bbox = tb['bbox']
        r = fitz.Rect(bbox[0]-3, bbox[1]-2, bbox[2]+5, bbox[3]+3)
        
        # Use sampled page background color, but if page bg is white, use pure white
        if is_light(bg_color):
            fill_color = (1, 1, 1)  # pure white
        else:
            fill_color = bg_color
        
        page.draw_rect(r, color=None, fill=fill_color)
    
    # Step 2: Insert translated text
    for tb in text_blocks:
        bbox = tb['bbox']
        rgb = clr(tb['color'])
        if rgb == (1, 1, 1) or (rgb[0] > 0.9 and rgb[1] > 0.9 and rgb[2] > 0.9):
            # White/light text on dark bg - use original color instead of converting to black
            pass
        
        font = get_font(tb['font'])
        
        # Calculate optimal font size
        orig_len = len(tb['orig_text'])
        trans_len = len(tb['text'])
        
        # Italian is typically ~15-20% longer. Calculate scale.
        if orig_len > 0:
            ratio = trans_len / max(orig_len, 1)
        else:
            ratio = 1.0
        
        # Base scale based on length ratio
        if ratio <= 1.0:
            base_scale = 1.0
        elif ratio <= 1.15:
            base_scale = 0.95
        elif ratio <= 1.3:
            base_scale = 0.88
        elif ratio <= 1.5:
            base_scale = 0.82
        else:
            base_scale = 0.75
        
        # Textbox size with some room
        w = (bbox[2] - bbox[0]) * 1.1
        h = (bbox[3] - bbox[1]) * 1.5
        rect = fitz.Rect(bbox[0], bbox[1], bbox[0] + w, bbox[1] + h)
        
        # Try inserting with the calculated scale
        font_size = tb['size'] * base_scale
        rc = page.insert_textbox(rect, tb['text'],
                                fontname=font,
                                fontsize=font_size,
                                color=rgb,
                                align=tb['align'])
        
        # If doesn't fit, try slightly smaller
        if rc < 0:
            for scale_factor in [0.85, 0.75, 0.65, 0.55]:
                rc = page.insert_textbox(rect, tb['text'],
                                        fontname=font,
                                        fontsize=tb['size'] * scale_factor,
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
