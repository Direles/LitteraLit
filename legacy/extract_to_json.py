import fitz, json, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

PDF_PATH = r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf'
OUT_PATH = r'C:\Users\anton\Desktop\traduzione libri\extracted_text.json'

doc = fitz.open(PDF_PATH)
output = []

for page_num in range(len(doc)):
    page = doc[page_num]
    page_rect = list(page.rect)
    blocks = page.get_text('dict')['blocks']
    
    page_data = {
        'page': page_num + 1,
        'rect': page_rect,
        'blocks': []
    }
    
    for b in blocks:
        block_data = {'type': b['type'], 'bbox': list(b['bbox'])}
        
        if b['type'] == 0:  # text
            full_text = ""
            lines_data = []
            for line in b['lines']:
                line_text = ""
                spans_data = []
                for span in line['spans']:
                    line_text += span['text']
                    spans_data.append({
                        'text': span['text'],
                        'font': span['font'],
                        'size': span['size'],
                        'color': span.get('color', 0),
                        'bbox': list(span['bbox'])
                    })
                lines_data.append({
                    'text': line_text,
                    'spans': spans_data,
                    'bbox': list(line['bbox'])
                })
                full_text += line_text + "\n"
            
            block_data['text'] = full_text.strip()
            block_data['lines'] = lines_data
            
            if lines_data and lines_data[0]['spans']:
                s = lines_data[0]['spans'][0]
                block_data['font'] = s['font']
                block_data['size'] = s['size']
                block_data['color'] = s['color']
        
        page_data['blocks'].append(block_data)
    
    output.append(page_data)
    
    if (page_num + 1) % 50 == 0:
        print(f"Estratte {page_num + 1}/{len(doc)} pagine...")

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=1)

print(f"\nSalvato! {len(output)} pagine estratte.")
print(f"File: {OUT_PATH}")

doc.close()
