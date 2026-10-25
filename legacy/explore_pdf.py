import fitz
doc = fitz.open(r'C:\Users\anton\Desktop\traduzione libri\User-story-mapping-discover-the-whole-story-build-the-right-product-Jeff-Patton.pdf')
page = doc[0]
blocks = page.get_text('dict')['blocks']
print(f'Numero blocchi nella pagina 1: {len(blocks)}')
for i, b in enumerate(blocks[:10]):
    print(f'\nBlocco {i}: tipo={b["type"]}')  # 0=text, 1=image
    if b['type'] == 0:  # text
        for line in b['lines'][:3]:
            for span in line['spans'][:2]:
                print(f'  Testo: "{span["text"][:80]}"')
                print(f'  Font: {span["font"]}, size: {span["size"]:.1f}')
                print(f'  BBox: {span["bbox"]}')
    elif b['type'] == 1:  # image
        print(f'  Image bbox: {b["bbox"]}')
        print(f'  Image size: {b.get("width","?")}x{b.get("height","?")}')
print(f'\nPage rect: {page.rect}')
print(f'Page rotation: {page.rotation}')
