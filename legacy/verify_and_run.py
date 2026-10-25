# -*- coding: utf-8 -*-
import json
import os

with open(r'C:\Users\anton\Desktop\traduzione libri\batch_p291-324_DONE.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

keys = sorted(data.keys())
total = len(data)

# Count translated
translated = sum(1 for k in data if data[k]['translated'] != data[k]['original'])

print(f"Total blocks: {total}")
print(f"Translated: {translated}")
print(f"File size: {os.path.getsize(r'C:\Users\anton\Desktop\traduzione libri\batch_p291-324_DONE.json')} bytes")

# Show first and last few
print(f"\nFirst key: {keys[0]}")
print(f"  Original: {repr(data[keys[0]]['original'][:80])}")
print(f"  Translated: {repr(data[keys[0]]['translated'][:80])}")

print(f"\nLast key: {keys[-1]}")
print(f"  Original: {repr(data[keys[-1]]['original'][:80])}")
print(f"  Translated: {repr(data[keys[-1]]['translated'][:80])}")

# Check a few middle ones
for k in ['p295_b5', 'p301_b4', 'p308_b3', 'p313_b1', 'p323_b4']:
    if k in data:
        print(f"\n{k}:")
        print(f"  Original: {repr(data[k]['original'][:100])}")
        print(f"  Translated: {repr(data[k]['translated'][:100])}")

print("\n--- Now running apply_translations.py ---")
