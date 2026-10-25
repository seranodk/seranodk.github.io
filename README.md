# seranodk.github.io
Små spil til tidsfordriv

Landingssiden på https://seranodk.github.io/ med links til spillene:
[Sensible](https://seranodk.github.io/Sensible/) · [Ishockey](https://seranodk.github.io/Ishockey/) · [Brikker](https://seranodk.github.io/Brikker/) · [Labyrint](https://seranodk.github.io/Labyrint/)

Versionsnumrene på kortene hentes automatisk fra hvert spils `index.html`, når siden åbnes, og igen hvert minut, mens siden er åben. Linket til spillet får versionen på (`?v=0.35.1`), så spillerne altid åbner den nyeste udgave i stedet for en gemt kopi.

## Nye spil kommer automatisk
Siden spørger selv GitHub, hver gang den åbnes, så et nyt repo med Pages vises med det samme (med spillets app-ikon, indtil skærmbilledet er taget). En GitHub Action (`.github/workflows/opdater.yml`) kører hvert 5. minut og gør kortet færdigt: Den finder alle offentlige repos hos seranodk, som har GitHub Pages slået til og en `index.html`, og lægger nye spil på siden med et ingame-skærmbillede og en kort beskrivelse.

- **Navn, genre og beskrivelse** tages fra spillets `<meta name="spil:navn">`, `<meta name="spil:genre">` og `<meta name="description">`. Mangler de, bruges overskriften og første afsnit i spillets README.
- **Skærmbillede** tages automatisk første gang. Slet billedet i `kilde/billeder/`, så tages et nyt ved næste kørsel.
- **Håndskrevne tekster** til et spil skrives i `kilde/spil.json`. De går forud for det automatiske.
- **Skjul et repo**, der ikke er et spil: skriv navnet i `"skjul"` i `kilde/spil.json`.
- Kør den med det samme under **Actions → Opdater spilhal → Run workflow**.

## Filer
- `index.html` – selve siden (bygget, med billederne indlejret)
- `kilde/build.py` – bygger `index.html`
- `kilde/spil.json` – rækkefølge og håndskrevne tekster
- `kilde/screenshot.py` – tager ingame-skærmbilleder
- `kilde/fundne.json` – det sidst fundne om hvert spil (skrives automatisk)
- `kilde/billeder/` – skærmbilleder fra spillene

Byg igen lokalt med `python3 kilde/build.py` (kræver `pip install playwright pillow`).
