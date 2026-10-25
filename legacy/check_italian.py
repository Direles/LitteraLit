import fitz, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

doc = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf')

with open(r'C:\Users\anton\Desktop\traduzione libri\translations.json', 'r', encoding='utf-8') as f:
    translations = json.load(f)

# Check page 16 - should have Italian text from translations
page = doc[15]  # page 16, 0-indexed
text = page.get_text()

# Search for specific Italian translations we know should be there
page_key = "p16"
for key, val in translations.items():
    if key.startswith(page_key) and val['translated']:
        ita_text = val['translated'][:60]
        # Check if this text exists somewhere in the page
        if ita_text.lower().strip()[:30] in text.lower():
            print(f"TROVATO: {key} -> '{ita_text[:80]}'")
        else:
            print(f"MANCANTE: {key} -> '{ita_text[:80]}...'")

# Also check for accented chars (definitely Italian)
total = len(text)
acc_chars = sum(1 for c in text if c in 'àèéìòù')
print(f"\nCaratteri accentati italiani trovati: {acc_chars} su {total} totali")

doc.close()
