import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

with open(r'C:\Users\anton\Desktop\traduzione libri\traduzioni_batch1_DONE.json', 'r', encoding='utf-8') as f:
    done = json.load(f)
print(f"Blocchi in DONE: {len(done)}")
k = list(done.keys())[0]
print(f"Prima chiave: {k}")
print(f"Translated: {done[k]['translated'][:80]}")

with open(r'C:\Users\anton\Desktop\traduzione libri\translations.json', 'r', encoding='utf-8') as f:
    tr = json.load(f)
print(f"Blocchi in translations.json: {len(tr)}")
if k in tr:
    status = "VUOTO" if not tr[k]['translated'] else tr[k]['translated'][:80]
    print(f"TRADOTTO: {status}")
else:
    print(f"CHIAVE {k} NON TROVATA")

translated_count = sum(1 for v in tr.values() if v['translated'])
print(f"\nTradotti: {translated_count}, Non tradotti: {len(tr)-translated_count}")
