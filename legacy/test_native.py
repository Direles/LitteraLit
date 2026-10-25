import fitz, json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PDF_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf'
TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
OUT = r'C:\Users\anton\Desktop\traduzione libri\test_output\test_native.pdf'

with open(TR_PATH, 'r', encoding='utf-8') as f:
    translations = json.load(f)

doc = fitz.open(PDF_PATH)

# Test on page 2 (index 1) - rich text page
page = doc[1]
blocks = page.get_text('dict')['blocks']

# First pass: draw white rectangles over text
for idx, b in enumerate(blocks):
    if b['type'] != 0:
        continue
    text = ""
    for line in b['lines']:
        for span in line['spans']:
            text += span['text']
    if not text.strip():
        continue
    
    bbox = b['bbox']
    # Slightly expand the rectangle to ensure full coverage
    r = fitz.Rect(bbox[0] - 2, bbox[1] - 1, bbox[2] + 2, bbox[3] + 1)
    page.draw_rect(r, color=None, fill=(1, 1, 1))  # white fill

# Second pass: insert translated text
for idx, b in enumerate(blocks):
    if b['type'] != 0:
        continue
    text = ""
    for line in b['lines']:
        for span in line['spans']:
            text += span['text']
    if not text.strip():
        continue
    
    key = f"p{2}_b{idx}"  # page 2
    translated = translations.get(key, {}).get('translated', '')
    if not translated:
        continue
    
    bbox = b['bbox']
    
    # Get original font size
    first_span = b['lines'][0]['spans'][0]
    orig_size = first_span['size']
    
    # Calculate translation scale factor (Italian is ~15% longer)
    orig_chars = len(text)
    trans_chars = len(translated)
    scale_factor = min(1.2, max(0.6, orig_chars / max(trans_chars, 1)))  # shrink font if needed
    new_size = orig_size * scale_factor
    
    # Color from original
    color = first_span.get('color', 0)
    r_val = (color >> 16) & 0xFF
    g_val = (color >> 8) & 0xFF
    b_val = color & 0xFF
    
    # Determine font family
    font_name = first_span.get('font', '').lower()
    if 'typewriter' in font_name or 'courier' in font_name or 'mono' in font_name:
        pymupdf_font = 'cour'
    elif 'serif' in font_name or 'minion' in font_name or 'times' in font_name or 'myriad' in font_name:
        pymupdf_font = 'tiro'
    else:
        pymupdf_font = 'helv'
    
    # Use insert_textbox for automatic wrapping
    rect = fitz.Rect(bbox[0], bbox[1], bbox[2], bbox[3] + 50)  # give extra height
    rc = page.insert_textbox(rect, translated, 
                              fontname=pymupdf_font, 
                              fontsize=new_size,
                              color=(r_val/255, g_val/255, b_val/255),
                              align=0)
    
    if rc < 0:  # text didn't fit, try with smaller font
        page.insert_textbox(rect, translated,
                           fontname=pymupdf_font,
                           fontsize=new_size * 0.8,
                           color=(r_val/255, g_val/255, b_val/255))

doc.save(OUT, deflate=True)
doc.close()
print(f"Test salvato: {OUT}")
print(f"Dimensione: {os.path.getsize(OUT)/1024:.1f} KB")
print("Apri il file per verificare la formattazione.")
