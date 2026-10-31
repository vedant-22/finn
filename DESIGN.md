# FINN's design (stage 4, section 11)

FINN shows the few things that need you today, and whether management kept its word. The first screen asks almost nothing of you: a count, the companies, the window. Everything else waits behind Read more or a fold. The look is v4's, the version the user called the cleanest: white paper, warm panels, ENAM blue for what you tap and for one band a screen. Tokens live at the top of `web/src/styles.css`.

## Idea
- **Calm on entry.** The first screen holds the wordmark, one count ("2 need you"), one grey sentence naming the companies, the window, and the top of the first card. No buttons to press, no settings.
- **Progressive disclosure.** A card says what happened in one line; Read more grows it into its full view. The rest of the window sits in two folds, Worth a look and Routine filings.
- **One family for the interface.** Inter sets every title and figure, and every label and control. PT Serif in roman grey sets only for the sentence under a title and for quotes. No italics, no serif figures.
- **A status is a small capital word in its colour.** Missed, Gone quiet, Kept, Partly kept, Not due. No glyphs.

## Colour
| Token | Hex | Role | On white | On panel |
|---|---|---|---|---|
| `--paper` | #FFFFFF | the page | | |
| `--panel` | #FBF8F2 | cards, the warm tops of Book, a company and an item, tiles, quotes | | |
| `--ink` | #333333 | text and figures | 12.6 | 11.9 |
| `--ink-2` | #6A6970 | the grey sentence, captions, labels | 5.4 | 5.1 |
| `--rule` | #D9D9D9 | hairlines and fold rules | | |
| `--brand` | #005DA3 | what you can tap; the end band; a company's questions block | 6.8 | 6.4 |
| `--missed` | #9E2B25 | Missed | 7.4 | 7.0 |
| `--quiet` | #94600A | Gone quiet | 5.3 | 5.0 |
| `--kept` | #24704A | Kept | 6.0 | 5.7 |

On the blue band, text is white (6.8:1) or white at 82% (5.1:1). `web/scripts/contrast.py` checks every pair in `web/scripts/tokens.py` and exits 1 on a failure. One full-colour moment a screen: the end band on Today, the questions block on a company.

## Type
v4's scale, all Inter except where noted:
- Count 72/100% at 500 with a 36 px unit ("2 need you"). Card figures 40 px with a 20 px unit; promise figures 48 to 24 px by length; Book's counts 30 px.
- Title 30/112% at 450 (Look up's banner, a company's name, an item's name, the end band). Section head 26/116% at 450. Card title and fold title 21/124% at 500 and 450.
- Body 16/140%; captions 14/140% grey; labels 12 px capitals at 450 with 0.24 px tracking.
- PT Serif 16 to 17 px roman grey: the sentence under a title, a card's sentence, the next-call questions, quotes. Its ₹ falls through to Inter's.

## Space and shape
Gutter 16 px; the column stops at 560 px. v4's spacing scale (4 to 80). Square panels; pill buttons; sheets 12 px at the top. No shadows. Every tap target is at least 44 px.

## Components
- **Masthead.** FINN in blue capitals, tracked. It hides on the way down and comes back on the way up.
- **Tab bar.** Today, Book, Look up.
- **Card.** Warm panel: the month's price line, short, with its first and last session; the kind ("Results, Q2"); the company; the day's move with its session and volume ("At the 28 Oct close, on 43.5× its usual volume"); one grey sentence; the line it crossed; Read more.
- **Full view.** The card's warm top, grown: Back, the price line, the name, the figure, the sentence, the lines it crossed with Change. Then the results table, the management change with the person's background, Against their word (verdict word, promise, what the filings showed, the quote and page), Ask FINN chips, sources.
- **Folds.** A rule, the title with its count in grey, a plus that turns to a minus. The content fades up as it opens.
- **End band.** ENAM blue to the tab bar: "That's the last 24 hours.", a question for each company's next call (news first) with Copy, then Open your book and Change your lines.
- **Book.** A warm top with one row of four counts and coloured words (Missed, Gone quiet, Kept, Not due), each a filter; then tiles, most promises broken first.
- **Company.** A warm top with the name in grey running into its record ("Larsen & Toubro. 1 of 2 promises kept."), the price and size in the serif; a full-width price line; the tally; settled promises one to a row with what was promised as the figure and what the filings showed under the verdict; Still running in a fold; the blue questions block; then folds.
- **Look up.** "Look up any NSE company", one big underlined field for a symbol, a name or a question (the button turns to Ask), Recent and Ready to open tiles, and a fold of book questions.
- **Your lines.** A sheet: the alerts switch, the two thresholds, the kinds of filing that can interrupt.

## Motion
One family of curves: expo out for reveals, decelerate for folds and sheets, standard for the morph. Transform and opacity only. Everything respects `prefers-reduced-motion` (it all appears in place).

Kept, because each one explains something:
- **A card grows into its full view** (a shared-element view transition, 340 ms). The warm panel itself grows; the card's face fades in the first 100 ms and the view's face after 140 ms, so text is never doubled. Back shrinks it into the same card at the same scroll. It says where the view came from and where it goes back to.
- **Blocks rise 12 px and settle** as they scroll into view (700 ms, expo out), the first three in an 80 ms stagger. It tells you the list goes on.
- **The count falls** from every filing in the window to what needs you, once a session (the sieve), and rolls when the window changes.
- **Price lines draw** left to right on a card, once; the full view shows the line already drawn.
- **Folds open** on a grid-rows transition with their content fading up 6 px.
- **Sheets slide up** in 260 ms and can be dragged down.

Removed, because each one got in the investor’s way:
- The first morph cross-faded the card and the view on top of each other: text read twice in the middle frames (all three critics in round s11-1). Replaced by the growing panel.
- The price line drawing again when a card opened: the same picture twice.
- The step bar and the swipe-to-clear reader: it made the first action a button press and a progress count.
- The card under the thumb lit and the others dimmed while scrolling: tried as a scroll-driven fade; at two cards a screen it greyed out the text you were about to read, so it went.

## States
Loading shows Today's shape: a grey count and a warm card. An empty window says "Nothing needs you", that nothing crossed your lines, and links to the nearest wider window that has something ("Last month: 6 need you"). A link to an item no longer in the window says "Not in this window". Errors are a plain grey sentence with Try again. Offline, the service worker serves the last snapshot, labelled with its time. Out of model quota, live research says so and lists the companies ready to open. An unknown symbol is said plainly, with Look up another.

## Words on screen
Short, plain sentences to the investor, in sentence case, numbers before adjectives. No emoji, no glyphs for status. When something isn't graded, say why.
