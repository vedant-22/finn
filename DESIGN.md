# FINN design

The product checks management's word against evidence. That is what an auditor does with a working paper: trace each figure to its source and put a mark next to it. FINN borrows that world, not a trading terminal's.

## Idea
- **Tick marks are the signature.** Auditors vouch figures with small pencil marks: a tick for agreed, a cross for not agreed. Every promise in FINN gets one, drawn as a pencil stroke when it's graded. It is the only place with motion that isn't a reply to a tap.
- **Paper and ink, not screens and glow.** A cool working-paper ground, blue-black ink, two pencil colours.
- **Quiet by default.** Most of a screen is ink on paper. Red and green appear only on marks and on the numbers they judge.

## Colour
| Token | Hex | Role |
|---|---|---|
| paper | #EDF0E8 | ground (cool working-paper green, not cream) |
| sheet | #F7F8F4 | raised surfaces: sheets, the open card |
| ink | #1C2838 | text, figures (blue-black ink, not grey-black) |
| ink-2 | #5B6573 | secondary text |
| rule | #CCD5C8 | ledger rules, dividers |
| kept | #2E7A4E | green pencil: kept, up moves |
| missed | #B23A2C | red pencil: missed, down moves |
| partly | #A86A12 | ochre pencil: partly, late |
| quiet | #8B9088 | graphite: quiet, pending, folded |
| mark | #F2DF6B | highlighter, once per screen at most, on the number that matters |

## Type
One family, Archivo (variable weight and width). Width does the work a second face usually does:
- Display figures: width 112–125, weight 600, tabular figures.
- Company names: width 112, weight 650, sentence case.
- Body: width 100, weight 400, 15/22.
- Dense tables and quotes: width 85, weight 400–500, 13/18.
Scale (px): 12, 13, 15, 17, 22, 30, 44. No all-caps labels, no letter-spaced eyebrows.

## Space and shape
4px base; 8, 12, 16, 24, 32. Screen gutter 16. Radius 6 on sheets only, 0 on ledger rows. No drop shadows except the bottom sheet (one soft edge). Row rules are 1px `rule`.

## Motion
- Tick marks draw in (stroke-dashoffset, 280ms, ease-out), staggered 60ms, when a ledger opens or a grade arrives.
- Sheets slide up 220ms. Expanding rows animate height via transform/opacity only.
- `prefers-reduced-motion`: marks appear drawn.

## Icons
None from icon sets. The marks (tick, cross, half-tick, open circle, dot) are drawn here as SVG paths with a slight hand wobble. Navigation is words.

## Words on screen
Speak to the investor. Sentence case. Numbers before adjectives. A screen gets one sentence at most.
