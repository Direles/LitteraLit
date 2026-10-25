import fitz, json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

doc = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO_v2.pdf')

with open(r'C:\Users\anton\Desktop\traduzione libri\translations.json', 'r', encoding='utf-8') as f:
    tr = json.load(f)

# Check if Italian text is the ONLY text on the pages (redaction removed English)
for pg_idx in [1, 5, 15, 30, 60, 100]:
    page = doc[pg_idx]
    text = page.get_text()
    
    eng_words = [' the ', ' and ', ' this ', ' that ', ' with ', ' for ', ' development ']
    ita_words = [' lo ', ' il ', ' la ', ' gli ', ' le ', ' dello ', ' della ', 
                 ' sviluppo ', ' prodotto ', ' storia ', ' mappatura ']
    
    eng_count = sum(1 for w in eng_words if w in text.lower())
    ita_count = sum(1 for w in ita_words if w in text.lower())
    
    # Count accented chars
    acc = sum(1 for c in text if c in 'àèéìòù')
    
    print(f"Pagina {pg_idx+1}: accenti={acc}, ENG={eng_count}, ITA={ita_count} | prime 100:")
    print(f"  {text[:120]}")
    print()

# Overall stats
total_text = ""
for p in range(len(doc)):
    total_text += doc[p].get_text()

total_acc = sum(1 for c in total_text if c in 'àèéìòù')
total_eng = sum(total_text.lower().count(w) for w in [' the ', ' and ', ' this ', ' for '])
total_ita = sum(total_text.lower().count(w) for w in [' lo ', ' il ', ' la ', ' dello '])
print(f"TOTALE - Accenti italiani: {total_acc}, ENG: {total_eng}, ITA: {total_ita}")

doc.close()
