import fitz, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

doc = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf')

with open(r'C:\Users\anton\Desktop\traduzione libri\translations.json', 'r', encoding='utf-8') as f:
    tr = json.load(f)

# Check pages 16-20 for spacing issues
for pg_idx in [15, 16, 17, 18, 19]:  # pages 16-20
    page = doc[pg_idx]
    text = page.get_text()
    
    # Count newlines (indicates wrapping)
    lines = text.split('\n')
    non_empty = [l for l in lines if l.strip()]
    
    # Check for suspicious patterns: very short lines (excessive wrapping)
    short_lines = [l for l in non_empty if len(l) < 15]
    
    eng = sum(text.lower().count(w) for w in [' the ', ' and '])
    ita = sum(text.lower().count(w) for w in [' lo ', ' il ', ' la '])
    acc = sum(1 for c in text if c in 'àèéìòù')
    
    print(f"Pagina {pg_idx+1}: {len(non_empty)} righe non vuote, "
          f"corte={len(short_lines)}, accenti={acc}, ENG={eng}, ITA={ita}")
    if short_lines:
        for sl in short_lines[:5]:
            print(f"  corta: '{sl}'")

doc.close()
