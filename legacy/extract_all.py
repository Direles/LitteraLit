import fitz
import json
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

doc = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf')

total_chars = 0
total_blocks = 0
total_pages = len(doc)

print(f"Totale pagine: {total_pages}")

for page_num in range(total_pages):
    page = doc[page_num]
    blocks = page.get_text('dict')['blocks']
    
    for b in blocks:
        if b['type'] == 0:
            full_text = ""
            for line in b['lines']:
                for span in line['spans']:
                    full_text += span['text']
            total_chars += len(full_text)
            total_blocks += 1

print(f"Totale blocchi di testo: {total_blocks}")
print(f"Totale caratteri: {total_chars}")
print(f"Stima parole (circa 5 char/parola): {total_chars // 5}")

doc.close()
