import fitz, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

doc = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf')

# Check text on multiple pages
for pg_idx in [1, 3, 15, 30, 60]:
    page = doc[pg_idx]
    # Even though visual text is covered, we can still get new text
    text = page.get_text()
    lines = [l for l in text.split('\n') if l.strip()]
    
    # Check for Italian words
    ita_indicators = ['è', 'é', 'à', 'ò', 'ù', 'ì', ' lo ', ' il ', ' la ', 
                      ' gli ', ' le ', ' un ', ' una ', ' che ', ' per ',
                      ' di ', ' del ', ' della ', ' essere ', ' avere ',
                      ' sono ', ' abbiamo ', ' sviluppo ', ' prodotto ',
                      ' software ', ' team ', ' mappatura ']
    
    ita_count = 0
    for line in lines[:30]:
        for ind in ita_indicators:
            if ind in line.lower():
                ita_count += 1
                break
    
    eng_indicators = [' the ', ' and ', ' is ', ' are ', ' was ', ' were ',
                      ' have ', ' has ', ' this ', ' that ', ' with ',
                      ' development ', ' product ', ' software ']
    
    eng_count = 0
    for line in lines[:30]:
        for ind in eng_indicators:
            if ind in line.lower():
                eng_count += 1
                break
    
    print(f"Pagina {pg_idx+1}: {len(lines)} righe, italiano={ita_count}, inglese={eng_count}")
    # Show first few lines
    for l in lines[:5]:
        print(f"  {l[:120]}")

doc.close()
