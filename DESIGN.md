# Folio, FINN's design system

A folio is a numbered leaf of an account book, and in India it is also the number on an investor's holding. Folio is the page FINN keeps for each management team: what they said, and what happened. It is built on a base design's code and scales (tokens, spacing, the accordion, the sheet, the calm reveal), then made FINN's own: a book serif for what FINN reports, rounded cards and chips, a floating bar, index rows, and the before-and-after. None of any reference's branding, images or copy is used. Tokens live in `web/src/styles.css` as `--fo-*`.

## Idea
- **The before-and-after is the signature.** What management said, the promise FINN pulled out of it, and what the filings showed, read top to bottom in one block.
- **One idea per block.** A card says one thing in one sentence; the rest waits behind a round control, a sheet or a row that opens in place.
- **The serif reports, the sans speaks.** Names, figures, quotes and headlines are in the book serif. Sentences and controls are in a plain sans.
- **Status is a chip.** Sentence case with a small mark, never caps.

## Colour
| Token | Hex | Role | Contrast on white |
|---|---|---|---|
| `--fo-paper` | #FFFFFF | page, cards | |
| `--fo-ink` | #333333 | text, figures | 12.6 |
| `--fo-ink-2` | #6A6970 | secondary text (ENAM grey) | 5.4 |
| `--fo-rule` | #D9D9D9 | hairlines, card borders | |
| `--fo-blue` | #005DA3 | ENAM blue, kept rare: the mark, the one filled button, links, the price line, the lit tab, the end band, the questions block | 6.8 |
| `--fo-missed` | #9E2B25 | a missed promise, nothing else | 7.4 |
| `--fo-panel` | #FBF8F2 | the before-and-after block | |
| `--fo-tint` | #F2F7FB | the tally block and the picture's inset | |
| `--fo-chip` | #F1F1F2 | neutral chips, the window's track | |
| `--fo-mark-fig` / `--fo-mark-date` | blue 16% / amber 26% | a target figure and a date, marked in a quote | |

Moves are ink with a sign and a true minus; there is no green or red for up and down.

## Type
- **Newsreader** (variable, optical sizes, lining and tabular figures, its own ₹) for headlines, company names, figures, quotes and index-row titles. Light: 400 for figures and headlines, 500 for card names and the promise line, 600 only in the mark.
- **Inter** (variable) at 400 and 500, tracking −0.01em, for sentences, captions and every control.
- Page headline 34/108% (Look up's 46/102%), section head 28/112%, card name 23/118%, index-row title 22/120%, promise row 20/125%.
- Figures: 76, 50, 42 and 32 px steps with the unit set at about half size on the baseline; stat figures 50/92%.
- Body 16/145%, card sentences 15/145%, captions 13 to 14 px.
- One italic phrase per screen at most, and only where it carries the meaning: "2 *need you*", "What did they *promise*?".
- No caps labels anywhere. Headings wrap balanced, paragraphs without orphans; an amount keeps its unit on its line.

## Space and shape
Spacing 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 60, 80; gutter 16; the column stops at 560 px. Radii: controls 8, media insets 14, cards 20, the end band's top 28, chips round. Hairlines, no shadows except the lifted segment in the window control.

## Components
- **Mark.** A small solid ENAM-blue square standing on the baseline, then *finn* in lowercase serif at 600.
- **Floating bar.** A rounded bar inset 10 px from the edges, white at 94% with a blur and a hairline. On a tab: the mark and one square Menu control; it slides away on the way down and returns on the way up. On a company page: Back with its arrow, then the name once the heading has scrolled off; it stays.
- **Menu.** A short sheet with two index rows: Alert lines (what's on, in a line) and How a promise is graded (what each verdict means).
- **Folio card.** White, 20 px radius, a hairline. A chip and the time; the company in serif; a stat stack (serif figure, sans caption); one sentence; the before-and-after when the company made a promise on this topic; the small price strip; a foot row with a round control that turns to open the detail.
- **Stat stack.** A serif figure, its word in serif under it, one plain sentence; set two to a row on the tinted block with a blue-tinted hairline between rows. Book's are tappable filters.
- **Index row.** Serif title, a count or a record figure and an arrow on the right, one plain line under; hairlines between. It opens a sheet (Today's Worth a look and Routine filings) or opens in place, the arrow turning down (a company's numbers, for and against, sources).
- **Promise row.** The promise in serif, a round control, then its status chip and when it was said; it opens on the before-and-after.
- **The before-and-after.** A warm rounded block with three steps on a hairline: *They said* (the quote in serif, the target figure and the date marked where they stand, the speaker and page), chips naming what was found (Target found, Date found, only when the words are in the quote), *The promise* as one serif line, *What the filings showed* (the status chip, the verdict, the evidence). On a card it shows one sentence of the quote.
- **Status chips.** Kept (tick, blue wash), Partly kept (dash), Missed (cross, red wash, red text), Gone quiet (ring), Not due (clock), Can't tell (?). Kinds of filing (Results, Unusual day, People) are neutral chips.
- **Price strip.** The last 30 sessions in a 14 px rounded tinted inset, 80 units tall, with its change as a caption. Context, never the point.
- **Controls.** Square-ish (8 px) buttons: one filled blue per screen at most, the rest outlined. The window is a segmented control. Look up's field is rounded with its square arrow button inside.
- **End band.** Today closes on ENAM blue rising with 28 px rounded corners: the window named in white serif, then Open your book and Change alert lines.
- **Sheet.** Slides up over the tab bar with a grab handle; drag down to close.

## Motion
- Reveal: blocks fade in over 1200 ms on expo-decelerate as they enter the view; the first cards step 120 ms apart.
- The before-and-after, as it scrolls in: the marks sweep under the figure and the date (650 ms), the chips arrive with a small spring (cubic-bezier(.34, 1.56, .64, 1), 90 ms apart), then the promise and the verdict fade up.
- The round control turns 180° on the same spring; arrows nudge on hover.
- Today's count rolls when the window changes. Accordions open in 200 ms and close in 100 ms. Sheets slide up in 220 ms.
- Waiting: nothing under 400 ms, then one muted line with a pulsing blue dot.
- `prefers-reduced-motion`: everything appears in place.

## Words on screen
Speak to the investor in short, plain sentences. Sentence case everywhere. Numbers before adjectives. A card gets one sentence. Say why something isn't graded rather than hiding it.
