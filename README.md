# BULLY Discs

A Fabric mod for Minecraft that adds **19 original instrumental music discs** inspired by the tracklist moods of Kanye West's album *BULLY* — styled in a washed-out BULLY palette and playable in any jukebox.

> Fan tribute mod. All music is **original, synthesized instrumental audio** — no Kanye West recordings or samples are included. Track names identify the mood each instrumental evokes.

## Versions

- Minecraft **1.20.1** (Java 17)
- Minecraft **1.21.1** (Java 21)

Loader: Fabric (Fabric API required).

## The discs

| # | Disc | Mood |
|---|------|------|
| 1 | KING | heavy soul loop, sub-bass grief |
| 2 | THIS A MUST | rage / industrial alarms |
| 3 | FATHER | church organ + synth bass |
| 4 | ALL THE LOVE | synth ballad, talkbox lead |
| 5 | PUNCH DRUNK | gospel chops, swing |
| 6 | WHATEVER WORKS | dusty soul loop |
| 7 | MAMA'S FAVORITE | music-box keys ballad |
| 8 | SISTERS AND BROTHERS | warm soul-funk clav |
| 9 | BULLY | toy-mallet music-box over industrial swell |
| 10 | HIGHS AND LOWS | two-chord emotional swell |
| 11 | I CAN'T WAIT | nostalgic strings bounce |
| 12 | WHITE LINES | icy detached FM keys |
| 13 | CIRCLES | lofi Rhodes loop |
| 14 | PREACHER MAN | sped-up soul stabs |
| 15 | BEAUTY AND THE BEAST | downtempo guitar plucks |
| 16 | DAMN | stripped piano, tape wobble |
| 17 | LAST BREATH | salsa montuno + clave |
| 18 | THIS ONE HERE | samba-jazz fusion |
| 19 | LOSING YOUR MIND | motorik krautrock creep |

## The special craft (the BULLY ritual)

Every disc is crafted with a golden checkerboard "ritual" pattern:

```
G R G
R C R
G R G
```

- **G** — Gold Nugget (YZY gold)
- **R** — Rotten Flesh (the toy mallet)
- **C** — a core item that identifies the track, e.g.:
  - KING → Gold Ingot
  - FATHER → Compass
  - MAMA'S FAVORITE → Baked Potato
  - CIRCLES → Echo Shard
  - THIS ONE HERE → Nether Star (epic rarity!)
  - LOSING YOUR MIND → Eye of Ender

The full core list is in `tools/make_recipes.py` and every recipe file in `data/bully_discs/recipes/`.

## Build

```bash
./gradlew build   # for the version set in gradle.properties
```

For the 1.21.1 build, the same sources are compiled with 1.21.1 mappings/dependencies (see the `1.21` branch or CI workflow).

## License

MIT — see `LICENSE`. The included music is original synthesized audio (MIT).
