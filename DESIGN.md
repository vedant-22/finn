# FINN design

The product checks management's word against evidence. That is what an auditor does with a working paper: trace each figure to its source and put a mark next to it. FINN borrows that world, not a trading terminal's.

## Idea
- **Tick marks are the signature.** Auditors vouch figures with small pencil marks: a tick for agreed, a cross for not agreed. Every promise in FINN gets one, drawn as a pencil stroke when it's graded. It is the only place with motion that isn't a reply to a tap.
- **Paper and ink, not screens and glow.** A white working paper, near-black ink, pencil colours only on marks.
- **Quiet by default.** Most of a screen is ink on paper. Red and green appear only on marks and on the numbers they judge.

## Language
Calm and spacious, after the reference studied in `design/inspiration.md`: one idea per screen, type and whitespace instead of boxes, hairline rules, pill controls, one quiet reveal.

## Colour
Drawn from ENAM Holdings' site (white ground, black text, grey #6A6970, ENAM blue #005DA3, #D2D2D2 rules). Each colour has one role.
| Token | Hex | Role | Contrast on white |
|---|---|---|---|
| paper | #FFFFFF | ground | |
| sheet | #F5F6F8 | the one tinted panel, the bottom sheet, inputs | |
| ink | #1F1F24 | text, figures | 16.6 |
| ink-2 | #6A6970 | secondary text (ENAM grey) | 5.5 |
| rule | #DCDCDE | hairlines | |
| accent | #005DA3 | ENAM blue: the primary button, the active tab, the newest volume bar. Rare | 6.6 |
| kept | #2E7A4E | kept, up moves | 5.3 |
| missed | #B23A2C | missed, down moves | 6.0 |
| partly | #94600F | partly, late | 5.3 |
| quiet | #8E8D93 | marks for pending and folded (not text) | |

## Type
Inter (variable) and PT Serif, both bundled.
- Big figure: Inter 72/72, weight 500, −5% tracking, tabular.
- Headings: Inter 26–30, weight 450, −4%. Company names in lists: 21, weight 500.
- Body: Inter 15/21, −1%. Small: 13–14.
- Explaining sentences (the agent speaking: story lines, the read, verdicts, notes): PT Serif 16/22.
No uppercase labels.

## Space and shape
4px base; 8, 12, 16, 24, 32, 48. Gutter 16. Square corners except pills (999px) and the sheet's top (16px). No shadows. Rules are 1px `rule`.

## Motion
- One reveal: blocks fade in and rise 12px as they enter the view, 900ms, cubic-bezier(.19,1,.22,1); the first three stagger 90ms.
- Tick marks draw in (280ms) when they come into view; the headline count rolls.
- Sheets slide up 220ms.
- Press: tappable rows dim to half while held; pills fill with `sheet`. No browser tap flash.
- Waiting: under 400ms shows nothing; after that one muted line with a pulsing dot ('Opening the ledger'). Lists and tallies appear whole, never counting up as files arrive.
- From the home screen on iOS, a swipe in from the left edge goes back; the page follows the finger.
- On a company page the header sticks (white, hairline once scrolled) and carries the name when the title has gone; nothing else is fixed except the tab bar.
- `prefers-reduced-motion`: everything appears in place.

## Icons
None from icon sets. The marks (tick, cross, half-tick, open circle, dot) are drawn here as SVG paths with a slight hand wobble. Navigation is words.

## Words on screen
Speak to the investor. Sentence case. Numbers before adjectives. A screen gets one sentence at most.
