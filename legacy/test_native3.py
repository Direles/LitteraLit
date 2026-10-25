import fitz, json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
OUT = r'C:\Users\anton\Desktop\traduzione libri\test_output\test_native3.pdf'

with open(TR_PATH, 'r', encoding='utf-8') as f:
    translations = json.load(f)

doc = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf')

page = doc[1]
blocks = page.get_text('dict')['blocks']

# STEP 1: Mark text blocks for redaction
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
    page.add_redact_annot(bbox, fill=(1, 1, 1))  # white fill after redaction

# STEP 2: Apply redactions (removes original text, fills with white)
page.apply_redactions()

# STEP 3: Insert translated text
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
    if r_val == 0 and g_val == 0 and b_val == 0:
        pass  # keep black
    
    # Find font from original
    font_name = first_span.get('font', '').lower()
    if 'typewriter' in font_name or 'courier' in font_name or 'ocr' in font_name:
        pymupdf_font = 'cour'
    elif 'serif' in font_name or 'minion' in font_name or 'times' in font_name:
        pymupdf_font = 'tiro'
    else:
        pymupdf_font = 'helv'
    
    # Textbox with word wrap
    # Give some room to grow
    width = bbox[2] - bbox[0] + 10
    height = bbox[3] - bbox[1] + 40
    rect = fitz.Rect(bbox[0], bbox[1], bbox[0] + width, bbox[1] + height)
    
    rc = page.insert_textbox(rect, translated,
                            fontname=pymupdf_font,
                            fontsize=orig_size * 0.85,
                            color=(r_val/255, g_val/255, b_val/255),
                            align=0)
    
    # If doesn't fit, try smaller
    if rc < 0:
        # Try with smaller font
        for factor in [0.75, 0.65, 0.55]:
            rc = page.insert_textbox(rect, translated,
                                    fontname=pymupdf_font,
                                    fontsize=orig_size * factor,
                                    color=(r_val/255, g_val/255, b_val/255))
            if rc >= 0:
                break

# Save as single page PDF
new_doc = fitz.open()
new_doc.insert_pdf(doc, from_page=1, to_page=1)
new_doc.save(OUT, deflate=True)
new_doc.close()
doc.close()

print(f"Salvato: {OUT} ({os.path.getsize(OUT)/1024:.1f} KB)")

# Verify extracted text is now Italian
verify = fitz.open(OUT)
vpage = verify[0]
extracted = vpage.get_text()
print(f"\nTesto estratto dopo redazione:")
print(extracted[:600])
verify.close()
