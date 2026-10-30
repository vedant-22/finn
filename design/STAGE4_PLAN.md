# Stage 4 plan

**Point of view:** FINN is a brief you finish. Each morning it hands you the few things that changed, holds each one against what management promised, and lets you go.

## The investor moments and where they live

| Moment (docs/INVESTOR.md) | Screen | 10 seconds | 1 minute | 10 minutes |
|---|---|---|---|---|
| Before the open | Brief | "3 to read" and the companies | The reader: one item at a time, Clear or Keep | Open the company from the item |
| Market hours | Brief, top: crossed your lines | A notification with the line printed on it | The price line and the filing that explains it | Move the line |
| After the close, results | Reader: results item | Four lines, QoQ and YoY | The promise that was due, against the number | Company: their word |
| An idea comes up | Ask, then Company | The verdict on their word | Trajectory, cash, for and against | Every promise with its page |

Anything that doesn't serve one of these is cut: the old Look up tab becomes Ask; the menu sheet goes; the masthead's snapshot line moves under the headline.

## Why v4 reads cleaner than v5 (390×844, Today, Book, Company)

1. **No boxes around chrome.** v4's header is the wordmark and one outlined button on white. v5 wraps the header in a floating bordered capsule.
2. **Flat blocks, not cards.** v4 separates with space and a full-bleed warm band. v5 draws a bordered, rounded card around every item and nests a tinted panel inside it, so the eye reads frames before content.
3. **Fewer type styles.** v4: a sans headline, a sans figure, one serif sentence. v5 on one screen: a serif display, an italic, sans body, a serif quote, chip text and highlighter marks on figures inside quotes.
4. **Quieter controls.** v4's window control is four words and an underline. v5's is a grey segmented pill. v5 adds chips ("Unusual day", "Target found", the sector).
5. **Fewer elements on the first screen.** v4's first screen holds a label, a number, a line, the window and a chart. v5's holds eleven distinct things.
6. **Media without frames.** v4's price line runs edge to edge. v5 boxes it in a tinted rounded panel.

What v4 did that we won't bring back: all-caps small labels (a tell), and a 300 px chart that pushes the words below the fold.

## The rules that beat v4

- Nothing gets a border unless it's a control. Separation is space and, inside lists, a hairline rule.
- One sans family does all of FINN's talking. The serif appears only for management's own words, quoted from a filing, on the warm panel. So the two voices are never confused: FINN in sans, management in serif.
- Six type styles in the whole app: figure, title, heading, body, small, quote.
- Blue is for things you can tap and for "kept". Dark red is for "missed" alone. No chips for status; a status is a word in its colour.
- Each screen's first view holds one idea and at most five things.
- 44 px tap targets, safe-area padding, no sideways scroll at 320.

## Screens and flows

1. **Brief (home, tab 1).** Mark top left, Listen top right. Under it: "3 to read" (figure rolls), the companies in one line, and the snapshot time. The window as four plain stops (24 h, 3 days, Week, Month). A progress rule with one segment per item. Then **Crossed your lines**: notification cards, each with the line that set it off ("Past your ±4% line"), tap the line to move it. Then **Worth a line**: the one-line notes, cleared together. Then **Set aside**: "41 routine filings" behind one tap. "Read the brief" opens the reader at the first unread item.
2. **Reader.** One item per screen, full height. Top: progress segments and "2 of 3", close. The item: company, what happened in one line, the detail (results table, the incoming person's background, the price line, the deal against revenue), and **Held against their word**: the promise this item settles or the company's record in one line. Bottom, in thumb reach: Keep and Clear. Swipe left clears. Clearing slides the next item in. After the last: **You're up to date**, with counts (read, kept, set aside) and the kept list. Ask chips sit above the actions ("Did they deliver on margins?").
3. **Ask (tab 3).** A field ("Ask about a company or your book") with a mic where the browser supports speech. Suggested questions from the context it was opened from. Answers from the cached ledgers, no model: company + topic, rendered as before and after (their words with page; what the filings show; the verdict word). Book-wide questions ("Who missed?", "Who's gone quiet?"). Unknown ticker: run the live research. No match: "Not in the filings FINN has read", and the promises it does have.
4. **Book (tab 2).** The word across the book: the tally (missed, gone quiet, kept, not due) and the companies weakest first.
5. **Company.** Name and the verdict in one sentence, price and its line drawing in, Their word (before and after per promise), the numbers behind one fold, for and against, sources.
6. **Your lines (sheet).** Kinds of filing that may interrupt, the ±% day, the volume multiple. Changing a line updates the brief behind the sheet.

## States

Loading: skeleton blocks in the shape of the screen. Empty: "Nothing crossed your lines in the last 24 hours" with the widest window that has something. Error: the plain error with Try again. Offline: the service worker serves the last snapshot, labelled with its time. Out of model quota (live research only): a plain line and the ready companies. First run: the brief opens as is, with one line under the headline explaining Clear and Keep, gone after the first clear.

## Motion (one easing, cubic-bezier(.2, 0, 0, 1); UI 150 to 300 ms)

- The headline count rolls to its value when the window changes (300 ms).
- A cleared item slides left and fades, the next settles into place (250 ms).
- The progress segment fills as an item clears (200 ms).
- The reader's next item slides in from the right (250 ms).
- Result figures roll to value when the item opens (400 ms, data).
- The price line draws itself left to right (600 ms, data).
- A verdict word lands after its evidence (fade and 4 px rise, 200 ms, 150 ms delay).
- Everything off under prefers-reduced-motion.

## Build checklist, in priority order

1. [ ] Tokens and type in styles.css (stage 4 rules above), app shell with Brief, Book, Ask tabs, safe areas.
2. [ ] Brief screen: headline, window stops, progress, crossed-your-lines notifications, worth a line, set aside. Cleared and kept state in localStorage. Deploy to finn-ledger-next.
3. [ ] Reader: one item per screen, results, people, moves, deals; Keep and Clear with swipe; done state. Deploy.
4. [ ] Held against their word on each item (promise due for that period, else the record line).
5. [ ] Ask: parser, answers from ledgers, book-wide answers, live research for unknown tickers, mic. Ask chips in the reader and on Company. Deploy.
6. [ ] Company and Book restyled to the rules; price line draws.
7. [ ] Your lines sheet from the notification line; changes recount the brief live.
8. [ ] Listen (speech synthesis) on the brief.
9. [ ] States: skeletons, empty, error, offline, quota, first run. PWA manifest and splash checked.
10. [ ] Tests: unit for ask parsing and brief state; e2e flows updated; 390 and 320 sweeps.
11. [ ] Section 7 comparison; promote only if it wins; then README, DESIGN.md, covering note, walkthrough, trace.
