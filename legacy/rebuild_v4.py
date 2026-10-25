import fitz, json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PDF_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf'
TR_PATH = r'C:\Users\anton\Desktop\traduzione libri\translations.json'
OUT_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf'

with open(TR_PATH, 'r', encoding='utf-8') as f:
    translations = json.load(f)

doc = fitz.open(PDF_PATH)
total_pages = len(doc)
print(f"PDF originale: {os.path.getsize(PDF_PATH)/1024/1024:.1f} MB")

def get_font(font_name):
    name = font_name.lower()
    if any(k in name for k in ['typewriter', 'courier', 'mono', 'ocr']):
        return 'cour'
    if any(k in name for k in ['serif', 'minion', 'times']):
        return 'tiro'
    return 'helv'

def clr(c):
    return ((c>>16)&0xFF)/255, ((c>>8)&0xFF)/255, (c&0xFF)/255

for page_num in range(total_pages):
    page = doc[page_num]
    blocks = page.get_text('dict')['blocks']
    
    # Collect text blocks info
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
        t = translations.get(key, {}).get('translated', '')
        if not t:
            continue
        text_blocks.append({
            'bbox': b['bbox'],
            'text': t,
            'size': b['lines'][0]['spans'][0]['size'],
            'font': b['lines'][0]['spans'][0].get('font','helv'),
            'color': b['lines'][0]['spans'][0].get('color',0),
        })
    
    if not text_blocks:
        continue
    
    # Step 1: Cover original text with white rectangles
    for tb in text_blocks:
        bbox = tb['bbox']
        page.draw_rect(
            fitz.Rect(bbox[0]-2, bbox[1]-2, bbox[2]+4, bbox[3]+2),
            color=None, fill=(1,1,1), fill_opacity=1
        )
    
    # Step 2: Insert translated text
    for tb in text_blocks:
        bbox = tb['bbox']
        rgb = clr(tb['color'])
        if rgb == (1,1,1):
            rgb = (0,0,0)
        
        font = get_font(tb['font'])
        
        # Wider textbox for Italian (which is typically longer)
        w = (bbox[2] - bbox[0]) * 1.2
        h = (bbox[3] - bbox[1]) * 1.4
        rect = fitz.Rect(bbox[0], bbox[1], bbox[0]+w, bbox[1]+h)
        
        for scale in [1.0, 0.9, 0.8, 0.7, 0.6]:
            rc = page.insert_textbox(rect, tb['text'],
                                   fontname=font,
                                   fontsize=tb['size']*scale,
                                   color=rgb, align=0)
            if rc >= 0:
                break
    
    if (page_num+1) % 25 == 0:
        print(f"Processate {page_num+1}/{total_pages} pagine...")

doc.save(OUT_PATH, deflate=True, garbage=3)
doc.close()

size_mb = os.path.getsize(OUT_PATH) / 1024 / 1024
print(f"\nPDF creato: {OUT_PATH} ({size_mb:.1f} MB)")
print(f"Pagine: {total_pages}")
