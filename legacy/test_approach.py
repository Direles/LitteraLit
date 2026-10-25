import fitz
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

doc = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf')

for page_num in [0, 1, 2]:
    page = doc[page_num]
    blocks = page.get_text('dict')['blocks']
    
    print(f"\n=== PAGINA {page_num+1} ===")
    
    text_blocks = []
    image_blocks = []
    for b in blocks:
        if b['type'] == 0:
            text_blocks.append(b)
        elif b['type'] == 1:
            image_blocks.append(b)
    
    print(f"Blocchi di testo: {len(text_blocks)}, Blocchi immagine: {len(image_blocks)}")
    
    for i, b in enumerate(text_blocks):
        bbox = b['bbox']
        full_text = ""
        for line in b['lines']:
            for span in line['spans']:
                full_text += span['text']
            full_text += "\n"
        
        first_span = b['lines'][0]['spans'][0] if b['lines'] else None
        font = first_span['font'] if first_span else 'unknown'
        size = first_span['size'] if first_span else 0
        color = first_span.get('color', 0) if first_span else 0
        
        print(f"\n  Blocco {i}: bbox={bbox}")
        print(f"    Font: {font}, size={size:.1f}, color={color}")
        print(f"    Testo: {full_text[:200].strip()}")

doc.close()
