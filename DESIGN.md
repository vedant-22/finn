# FINN's design (stage 4)

FINN is a brief you finish. The design follows from that. There is one short list a morning, read one item per screen, and it ends. It keeps ENAM's colours on white paper and puts nothing on screen that the investor can't act on or doesn't need to know. Tokens live at the top of `web/src/styles.css`.

## Idea
- **Nothing has a border unless it's a control.** Space separates blocks; inside a list, a hairline does.
- **The serif sets what you look at, the sans says what FINN found.** Titles, section heads, company names in lists, big figures and management's quotes are in the book serif. Everything else is in the sans.
- **One idea per block, five things per first view.** The rest is one tap away.
- **A status is a word in its colour.** Kept, Partly kept, Missed, Gone quiet, Not due yet. No chips and no tick marks.

## Colour
| Token | Hex | Role | Contrast on white |
|---|---|---|---|
| `--paper` | #FFFFFF | the page | |
| `--ink` | #333333 | text and figures | 12.6 |
| `--ink-2` | #6A6970 | secondary text (ENAM grey) | 5.4 |
| `--rule` / `--rule-2` | #E7E7E9 / #D9D9D9 | hairlines / control outlines | |
| `--blue` | #005DA3 | what you can tap: the one filled button, links, the lit tab and window stop, the price line, progress | 6.8 |
| `--kept` | #24704A | the word Kept | 6.0 |
| `--missed` | #9E2B25 | the word Missed, nothing else | 7.4 |
| `--panel` | #FBF8F2 | management's quote | |

Moves are ink with a sign and a true minus. There is no green or red for up and down.

## Type
- **Newsreader**, a variable book serif with optical sizes and its own ₹. Big figure 68 px at 380 ("2" in "2 *to read*", with the unit in italic at 40 px). Title 32/110% at 450: screen titles, company names, "You're up to date". Head 22/120% at 500: section heads ("Crossed your lines", "Against their word"). Alert names 21 px, promise rows 19 px, alert figures 32 px at 400, the Book's tally 48 px at 380. Quotes 18/145%.
- **Inter** (variable) at 400 and 500 for everything FINN says: body 16/150%, alert sentences and tables 15 px, small 13/140% in grey.
- Six styles in all: figure, title, head, body, small, quote. One italic per screen at most. No caps labels. Headings wrap balanced and paragraphs avoid orphans. Tables and counts use tabular figures.

## Space and shape
Gutter 20 px; the column stops at 560 px. Sections 28 to 36 px apart. Radii: buttons 12, the brief's one pill fully round, the quote panel and the Ask field 14, sheets 20 at the top. No shadows. Every tap target is at least 44 px.

## Components
- **Mark.** A small blue square on the baseline and *finn* in the serif at 500.
- **Tab bar.** Brief, Book, Ask: solid white over a hairline, the lit tab in ink with a short blue rule. Respects the bottom safe area.
- **Brief head.** The snapshot time in grey, the figure ("2 *to read*"), one grey line that names the companies and adds up the rest ("4 more worth a line; 3 routine filings set aside"), then the one pill: Read the brief.
- **Window.** Four words (24 hours, 3 days, Week, Month), the chosen one in ink and underlined in blue.
- **Alert row.** A flat row between hairlines. Top: the time on the left, the line it crossed on the right in grey (tap it to move the line). Then the company in the serif, one sentence under it, and on the right the figure (the day's move or PAT YoY) with a month of closes drawn under it and its change written out.
- **Reader.** Full screen, over the tabs. Top: close, one progress segment per item, "2 of 3". The item: what it is and when, the company as the title, then its detail. Bottom, in thumb reach: Keep for later (outlined) and Done (filled). Swipe left for Done, right to keep.
- **Results table.** Revenue, EBITDA, PBT, PAT and Margin; columns Quarter, QoQ, YoY; hairlines between rows; one grey line saying what it is compared against.
- **Against their word.** The period and what was delivered, ending on the verdict word in its colour; then "Their Aug ’25 promise: ..." in grey; then the quote on the warm panel with the speaker and a link to the page.
- **Background.** For a management change: who joins in which role, then their background from the company's filing, credited to it.
- **Ask.** A rounded field with a mic (where the browser has speech) and a square blue send button. The answer's headline carries the verdict ("Larsen & Toubro on revenue growth: missed"), then the record in one grey line, then each promise as before and after.
- **Promise row.** The promise in the serif with a chevron; under it, the verdict word and when it was said. It opens in place on the quote and the evidence.
- **Sheet.** Your lines slides up over the brief with a grab handle; drag down to close. Changing a line recounts the brief behind it.
- **Done.** "You're up to date", what was read and kept, how many filings were set aside, and Back to the brief.

## Motion
One easing, cubic-bezier(.2, 0, 0, 1). UI motion 150 to 300 ms; data motion a little longer.
- The brief's count rolls when the window changes (300 ms).
- Done slides the item left and fades; the next one comes in from the right (250 ms). The progress segment fills (200 ms).
- Result figures roll to their value as the item opens.
- Price lines draw left to right.
- A verdict word lands after its evidence: a fade and a 6 px rise.
- Sheets slide up in 300 ms.
- `prefers-reduced-motion`: everything appears in place, skeletons stop shimmering.

## States
Loading shows skeletons in the shape of the screen. An empty window reads "All quiet", says nothing crossed your lines in it, counts what is worth a line, and links to the nearest wider window that has something ("Last month: 1 to read"). Errors are a plain sentence with Try again. Offline, the service worker serves the last snapshot, labelled with its time. When the model is out of quota, live research says so in one line and lists the companies that are ready; Ask on cached companies is unaffected. On first run, one line at the foot of the reader explains Keep and Done and says swiping works; it goes after the first item.

## Words on screen
Short, plain sentences to the investor, in sentence case, with numbers before adjectives. No emoji, no glyphs for status. When something isn't graded, say why.
