import fitz, json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
OUT = r'C:\Users\anton\Desktop\traduzione libri\test_output\test_native2.pdf'

with open(TR_PATH, 'r', encoding='utf-8') as f:
    translations = json.load(f)

doc = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf')

# Work on page 2 only
page = doc[1]
blocks = page.get_text('dict')['blocks']

print(f"Blocchi totali: {len(blocks)}")

# First pass: draw white rectangles over text areas
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
    r = fitz.Rect(bbox[0] - 2, bbox[1] - 1, bbox[2] + 4, bbox[3] + 2)
    page.draw_rect(r, color=None, fill=(1, 1, 1))

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
    
    key = f"p2_b{idx}"
    translated = translations.get(key, {}).get('translated', '')
    if not translated:
        continue
    
    bbox = b['bbox']
    first_span = b['lines'][0]['spans'][0]
    orig_size = first_span['size']
    
    color = first_span.get('color', 0)
    r_val = (color >> 16) & 0xFF
    g_val = (color >> 8) & 0xFF
    b_val = color & 0xFF
    if r_val + g_val + b_val == 0:  # pure black
        r_val = g_val = b_val = 0
    
    font_name = first_span.get('font', '').lower()
    if 'typewriter' in font_name or 'courier' in font_name or 'ocr' in font_name:
        pymupdf_font = 'cour'
    elif 'serif' in font_name or 'minion' in font_name or 'times' in font_name:
        pymupdf_font = 'tiro'
    elif 'myriad' in font_name:
        pymupdf_font = 'helv'
    elif 'guardian' in font_name:
        pymupdf_font = 'helv'
    else:
        pymupdf_font = 'helv'
    
    # Allow text to extend further down
    extra_height = 30
    rect = fitz.Rect(bbox[0], bbox[1], bbox[2] + 10, bbox[3] + extra_height)
    
    # Try inserting; if overflow, reduce font
    rc = page.insert_textbox(rect, translated,
                            fontname=pymupdf_font,
                            fontsize=orig_size * 0.85,
                            color=(r_val/255, g_val/255, b_val/255),
                            align=0)
    import fitz as f
    if rc < 0:
        # Smaller font
        page.insert_textbox(rect, translated,
                           fontname=pymupdf_font,
                           fontsize=orig_size * 0.7,
                           color=(r_val/255, g_val/255, b_val/255))
    
    if idx < 3:
        print(f"Blocco {idx}: '{text[:40]}' -> '{translated[:40]}' (size {orig_size}->{orig_size*0.85:.1f}, font={pymupdf_font})")

# Save only this page as a new PDF
new_doc = fitz.open()
new_doc.insert_pdf(doc, from_page=1, to_page=1)
new_doc.save(OUT, deflate=True)
new_doc.close()
doc.close()

print(f"\nTest salvato: {OUT}")
print(f"Dimensione: {os.path.getsize(OUT)/1024:.1f} KB")

# Verify the text was actually written
verify = fitz.open(OUT)
vpage = verify[0]
print(f"\nTesto estratto dalla pagina modificata:")
print(vpage.get_text()[:500])
verify.close()
