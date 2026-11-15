# FINN's design (stage 4, section 11)

FINN shows the few things that need you today, and whether management kept its word. The first screen asks almost nothing of you: a count, the companies, the window. Everything else waits behind Read more or a fold. The look is v4's, the version the user called the cleanest: white paper, warm panels, ENAM blue for what you tap and for one band a screen. Tokens live at the top of `web/src/styles.css`.

## Idea
- **Calm on entry.** The first screen holds the wordmark, one count ("2 need you"), one grey sentence naming the companies and the time the filings run to, the window, and the top of the first card. No buttons to press, no settings. On the demo, one quiet outlined pill in the masthead gives the day the data stops ("Sample data · 28 Oct"); it is the only thing up there besides the wordmark.
- **Progressive disclosure.** A card says what happened in one line; Read more grows it into its full view. The rest of the window sits in two folds below the cards: Worth a look; Routine filings.
- **One family for the interface.** Inter sets every title and figure; it also sets labels and controls. PT Serif in roman grey sets only the sentence under a title, and quotes. No italics, no serif figures.
- **A status is a small capital word in its colour.** Missed, No update, Done, Partly done, Not yet due, Can't tell yet (Not due where the row is short). No glyphs.

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
| `--quiet` | #94600A | No update | 5.3 | 5.0 |
| `--kept` | #24704A | Done | 6.0 | 5.7 |

On the blue band, text is white (6.8:1) or white at 82% (5.1:1). `web/scripts/contrast.py` checks every pair in `web/scripts/tokens.py` and exits 1 on a failure. One full-colour moment a screen: the end band on Today, the questions block on a company.

## Type
v4's scale, all Inter except where noted:
- Today keeps to five sizes: the count 72/100% at 500 with its 36 px unit; 21 for a card's name and its figure; 16 for the hero sentence, the window, the card's sentence and Read more; 14 for the one grey line under a card's sentence; 12 for capitals and the price line's captions (round s11-4: all three critics counted seven to nine). Elsewhere card figures are 30 px with a 16 px unit; promise figures 48 to 24 px by length, and a settled one shows what was delivered ('11.8% against 15%'); Book's counts 30 px.
- Title 30/112% at 450 (Look up's banner, a company's name, an item's name, the end band). Section head 26/116% at 450. Card title and fold title 21/124% at 500 and 450.
- Body 16/140%; captions 14/140% grey; labels 12 px capitals at 450 with 0.24 px tracking.
- PT Serif 16 to 17 px roman grey: the sentence under a page's title, and quotes. Its ₹ falls through to Inter's, and so do its digits, sign, per cent and ×, through a unicode-range face, so a figure in a sentence matches the figures in the tables. A sentence that is mostly figures (a card's, the next-call questions, a company's record in Look up) is Inter, grey (round s11-3: all three critics read figures in the serif).

## Space and shape
Gutter 16 px; the column stops at 560 px. v4's spacing scale (4 to 80). Square panels; pill buttons; sheets 12 px at the top. No shadows. Every tap target is at least 44 px.

## Components
- **Masthead.** FINN in blue capitals, tracked. It hides on the way down and comes back on the way up. On Today, Book and Look up it carries one outlined pill, "Sample data · 28 Oct", which opens Your data. A real install has no pill; its door is the Your data row at the foot of Your lines.
- **Your data.** One sheet, five blocks, each a heading and at most two sentences, privacy first: the demo, what stays on this phone, what a model reads, then sources (ending on how a filing is read: as text, never as instructions), and what doesn't work here. No heading raises a worry the reader didn't have, and no word needs explaining (no "model key"). "In a real install" sits under the two privacy blocks only. Clear this phone stands alone at the foot and asks once, Keep focused. Counts, dates and the live line are never typed into copy.
- **Who wrote it.** Where a model writes freely (a company's read, its questions, its case for and against) a grey line under it says so, and says what is checked and what isn't.
- **Tab bar.** Today, Book, Look up. It stays on every screen, the full view of a card included.
- **Card.** Warm panel: the month's price line, short, its start saying what the month did ('Since 15 Sep, +8.4%') and its end the day's move ('+12.2% on 28 Oct'); the kind ('Price move on Q2 FY27 results', 'Heavy trading on' when only the volume line was crossed, 'Q2 FY27 results and a new CFO' when a top change came with them); the company; one sentence in ink; one grey line with the line it crossed and the volume ('Past your ±4% and 2× lines, 43.5× volume'); Read more.
- **Full view.** The card's warm top, grown: Back, the price line, the name, the figure, the sentence, the lines it crossed with Change. Then the results table, the management change with the person's background, Against their word (verdict word, promise, what the filings showed, the quote and page), Ask FINN chips, sources.
- **Folds.** A rule, the title with its count in grey, a plus that turns to a minus. The content fades up as it opens.
- **End band.** ENAM blue to the tab bar: "That's the last 24 hours.", a question for each company's next call (news first) with Copy, one button, Open your book, and two white links under it, Change your lines and Listen. Nothing sits between the folds and the band.
- **Book.** A warm top with one row of four counts on four equal columns and coloured words (Missed, No update, Done, Not due), each a filter; then tiles, most promises broken first. The lead tile's picture is its record ('1 of 7 kept', 48 px), not a price line.
- **Company.** A warm top with the name in grey running into its record ("Larsen & Toubro. 1 of 2 promises kept."), the price and size in the serif; a full-width price line; the tally; settled promises one to a row with what was promised as the figure and what the filings showed under the verdict; Still running in a fold; the blue questions block; then folds.
- **Look up.** "Look up any NSE company", one big underlined field for a symbol, a name or a question (the button turns to Ask), Recent and Ready to open as a hairline list (name over symbol, the record at the right), and a fold of book questions. A question about something no promise names is answered 'Not found in the filings', with what they did promise under it.
- **The Network.** Never a screen of its own. A person appears beside the thing they can explain, one at a time. On a Today card: one grey line under the line it crossed, the name in ink ('Ask Dr. Leena Joshi. Director, Discovery Chemistry there, 2011–2019.'); a card says nothing when nobody is close enough, and says 'You know' in place of 'Ask' when the person works at the company now. In the full view: Who to ask, each person a hairline row (the name, how they stand to the company in small capitals, why them in grey, when you last spoke), a question about the company under the person who can answer it, In the room for what to put to the person, then anything ruled out as a footnote ('Not the Deepak Jain you know'). When someone arrives in a seat and two or more of your people can each answer one question, Who to ask gives way to **Who was there**: the path. A hairline down the left; a filled dot a station (the new seat, then each employer the filing lists, in its order); a hollow dot off the line for what the filing doesn't list; the station in small capitals with the role in grey; the question in ink; the name, how they stand to that station and their own role on one grey line. One caption says whose the path is. In the room, then Copy the call sheet. No new colour, type size or motion, and it fits 560 px at 390 wide. That card's line on Today counts them ('Three of your people are on Rinkoo Somani's path.'). In the end band: 'Ask first' under each next-call question, the person and their own question on one line. The card's line, Who to ask and Ask first name one person for one kind of question: for a CEO, CFO or MD who left, someone who worked there and left over a year ago, asked the seat question; for the numbers, someone at a competitor or a customer today, asked about their own seat and on the subject of the question it sits under (a margin that fell: costs; a fall in profit: one-off items; a lender's credit cost: credit costs); nobody fits, nothing is said. **The network's card.** At most one on Today, last in the list and outside the count ('2 need you' still counts what crossed your lines; the grey line adds its own sentence, 'One more from your network.'): the chip 'Your network', the companies as the title in Inter, what happened and the person in one sentence, no price line, the date and 'Sample network' in the foot. It opens to each company's question for the one person and Copy the call sheet, or to a pattern's filed evidence, said once under the sentence, its one person and question, and the question for management. A name FINN can't place carries 'Same person' and 'Someone else' as two quiet links under the question, and 'Change' once answered, under either answer, so a mis-tap can be undone. Same person carries the caution when the contact works there now and opens the company. Under the folds: From your network, a third fold, for what the cards don't carry (what two filings say together, one call that answers two questions, a contact in a filing, a name it can't place, the only person you know inside a holding, a reason to call). A notice with a card that the window leaves in the fold says the card's sentence and opens the same full view; someone you know is one row at a company, with that day's other filing on it. Closed, it says its first notice in one grey line. On a company: Who to ask, straight under the blue questions, listing everyone its count says has worked inside, with a pattern across its filings first and 'Before you meet them' when someone new has a path. In Look up: the same rows answer a direct question. The demo's people are synthetic and each place says so.
- **Your lines.** A sheet: the alerts switch, the two thresholds, the kinds of filing that can interrupt.

## Motion
One family of curves: expo out for reveals, decelerate for folds and sheets, standard for the morph. Transform and opacity only. Everything respects `prefers-reduced-motion` (it all appears in place).

Kept, because each one explains something:
- **A card grows into its full view** (a shared-element view transition, 340 ms). The warm panel grows while every part the view repeats (the price line, the kind, the name, the figure, the sentence) travels to its place. Only the arriving copy of each part is drawn, carried by its group from the old place and size, so nothing is ever seen twice (round s11-4: all three critics saw overprints); the sentence is the card's word for word and wraps as it did, so it moves as one picture. The rest of the card's face is gone in 70 ms and the view's fades in from 120 ms, and the page under the panel dims a little. Back shrinks it into the same card at the same scroll. It says where the view came from and where it goes back to.
- **A Book card grows into its company's warm top**, the name travelling when it sits on one line, and Back shrinks the top into the card (round s11-3: the company page cross-faded). The Book page fades out in 90 ms before the company page comes in, so the two pages are never seen together.
- **Blocks rise 12 px and settle** as they scroll into view (700 ms, expo out), the first three in an 80 ms stagger. It tells you the list goes on.
- **The count falls** from every filing in the window to what needs you, once a session (the sieve), and rolls when the window changes.
- **Price lines fade up** with their card, once (opacity only).
- **Folds open** in two beats: what sits below slides to its new place (FLIP: measured before, put back with a transform, released over 240 ms), then the fold's rows settle in (180 ms from 200 ms). No row is ever half covered and no height is animated (rounds s11-3 and s11-4).
- **Sheets slide up** in 260 ms and can be dragged down.
- **The tab bar stays put** above the growing panel, the same picture before and after, so it is never cross-faded (round s11-3 asked for it in the full view).

Removed, because each one got in the investor’s way:
- The first morph cross-faded the card and the view on top of each other: text read twice in the middle frames (all three critics in round s11-1). Replaced by the growing panel.
- The price line drawing again when a card opened: the same picture twice.
- The price line drawing itself left to right (a clip-path wipe): all three critics in round s11-2 read it as a wipe, and it isn't transform or opacity. It fades up instead.
- The panel growing with nothing on it for a moment (round s11-2, all three): the shared parts fixed it.
- Folds growing in height: the last row was clipped mid-way and the content below was dragged.
- The tab bar stepping down as a card opened (round s11-3): it took Book and Look up away while reading.
- The step bar and the swipe-to-clear reader: it made the first action a button press and a progress count.
- The card under the thumb lit and the others dimmed while scrolling: tried as a scroll-driven fade; at two cards a screen it greyed out the text you were about to read, so it went.

## States
Loading shows Today's shape: a grey count and a warm card. An empty window says "Nothing needs you", that nothing crossed your lines, and links to the nearest wider window that has something ("Last month: 6 need you"). A link to an item no longer in the window says "Not in this window". Errors are a plain grey sentence with Try again. Offline, the service worker serves the last snapshot, labelled with its time. Out of model quota, live research says so and lists the companies ready to open. An unknown symbol is said plainly, with Look up another.

## Words on screen
Short, plain sentences to the investor, in sentence case, numbers before adjectives. No emoji, no glyphs for status. When something isn't graded, say why.
