import fitz, json, sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

orig = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf')
trans = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf')

with open(r'C:\Users\anton\Desktop\traduzione libri\translations.json', 'r', encoding='utf-8') as f:
    tr = json.load(f)

print(f"Originale: {os.path.getsize(r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf')/1024/1024:.1f} MB")
print(f"Tradotto:  {os.path.getsize(r'C:\Users\anton\Desktop\traduzione libri\User-Story-Mapping-ITALIANO.pdf')/1024/1024:.1f} MB")

# Check page 16: look for Italian text in the page content stream
page = trans[15]  # page 16 (0-indexed)

# Check raw content stream for Italian characters
text = page.get_text()
print(f"\n=== Pagina 16 - cerca testo italiano ===")

# Get specific translations for page 16
ita_count = 0
for key, val in tr.items():
    if key.startswith("p16_") and val['translated']:
        snippet = val['translated'][:40]
        # Check in page text
        if snippet in text or snippet.lower() in text.lower():
            ita_count += 1
        else:
            pass  # Don't print every failure

print(f"Blocchi italiano trovati: {ita_count}")

# Check overall for accented Italian chars
all_text = ""
for p in range(len(trans)):
    all_text += trans[p].get_text()

ita_chars = sum(1 for c in all_text if c in 'àèéìòù')
print(f"\nCaratteri accentati (àèéìòù) nell'intero PDF: {ita_chars}")

eng_phrases = [' the ', ' and ', ' development ', ' product ']
eng_count = sum(all_text.count(p) for p in eng_phrases)
ita_phrases = [' lo ', ' il ', ' la ', ' sviluppo ', ' prodotto ']
ita_word_count = sum(all_text.count(p) for p in ita_phrases)
print(f"Frasi inglesi: {eng_count}, frasi italiane: {ita_word_count}")

# Check a sample translation
for key, val in list(tr.items())[:5]:
    if val['translated']:
        pass

# Compare a specific known translation
sample_key = "p25_b0"
if sample_key in tr:
    print(f"\n--- Traduzione esempio ({sample_key}) ---")
    print(f"Originale: {tr[sample_key]['original'][:100]}")
    print(f"Tradotto:  {tr[sample_key]['translated'][:100]}")

trans.close()
orig.close()
