# 🍝 Menu QR · Pranzo di famiglia Tosti-Piselli

QR code + landing page statica per il pranzo di famiglia **Tosti-Piselli** durante la
festa di paese a **Morignano (Ascoli Piceno)**.

Inquadri il QR con la fotocamera del telefono e si apre il menu.

**Sito:** https://g95g95.github.io/qr_code/
**Cartello QR stampabile:** https://g95g95.github.io/qr_code/qr.html

## Cosa c'è nel repo

| File | Cosa fa |
| --- | --- |
| `index.html` | La landing page del menu (antipasto / primo / secondo), autonoma: zero dipendenze esterne |
| `qr.html` | Cartello con il QR, pronto da stampare e attaccare in cucina o sul tavolo |
| `assets/qr-menu.svg` / `.png` | Il QR code generato (SVG per lo schermo, PNG per la stampa) |
| `tools/generate_qr.py` | Genera i due file del QR |
| `tools/test_qr.py` | Test: decode del QR + controlli sulla landing page |
| `.github/workflows/pages.yml` | Rigenera, testa e pubblica il sito su GitHub Pages |

## Rigenerare il QR

```bash
pip install segno Pillow
python3 tools/generate_qr.py                       # usa l'URL di default
python3 tools/generate_qr.py --url https://esempio.it   # per un altro indirizzo
```

## Eseguire i test

```bash
pip install opencv-python-headless Pillow segno
python3 tools/test_qr.py
```

I test verificano che il QR si decodifichi all'URL giusto a diverse dimensioni
(fino a 200 px), sfocato e ruotato, che la quiet zone sia intatta, che le pagine
non facciano richieste a domini esterni e che tutti i piatti del menu siano
presenti. Se è installato Playwright, viene anche rasterizzato `qr.html` con
Chromium per controllare che il QR sia leggibile **così come lo disegna il
browser**, anche su schermo di telefono a 1x.

## Note sul QR

- correzione errore **H** (30%): regge stampe scadenti, pieghe e macchie di sugo;
- moduli arrotondati ma contigui e occhi con raggio ≤ 1 modulo: l'arrotondamento
  più spinto ("a pois" con gli occhi tondi) faceva fallire i decoder;
- quiet zone di 4 moduli su tutti i lati.

## Attivare GitHub Pages

Il workflow prova ad attivare Pages da sé (`actions/configure-pages` con
`enablement: true`). Se il repo non lo permette: **Settings → Pages → Source:
GitHub Actions**, poi lancia di nuovo il workflow.
