# Stage 4: interaction models, explored

Seven models, each run through the investor's morning from docs/INVESTOR.md (7:40 am, on the commute, overnight results from two holdings, one 6% move, 40 routine filings). Scored 1 to 5 on time saved, signal over noise, how often it gets used, delight, and whether it ships well by 1 Nov. The data is the 28 Oct snapshot: 286 filings, 18 holdings, 22 company ledgers.

## 1. Chat (obvious)

The home screen is a message box. They type "what happened overnight?" and FINN replies with a paragraph and some cards.

Their morning: thumbs out a question on a moving train, waits for the model, reads prose, asks a follow-up. Nothing tells them when they are done. Every answer costs a model call, and the free tier runs out by mid-morning if a few people use the link.

Time 2, signal 3, use 2, delight 2, ships 3. **Rejected as the spine.** Typing is the slowest way to ask a phone anything, and a blank box puts the work of filtering back on the investor.

## 2. Voice (obvious)

"Read me the brief." FINN reads the few things that matter aloud, then waits for a question.

Their morning: earbuds in, hears "Syngene reported after the close. Revenue 833 crore, up 13% on the quarter, down 9% on the year..." and the rest of the brief in under a minute. Good for the commute. Useless in a meeting. Speech recognition on Safari is patchy and numbers read aloud are hard to hold.

Time 4, signal 4, use 3, delight 4, ships 3. **Kept as a feature inside the brief:** a "Listen" control reads the brief with the browser's own speech, free and offline. Not the spine.

## 3. Dashboard (obvious)

Tiles: portfolio value, movers, filings by category, a heat map.

Their morning: scans twelve equal tiles to find the two that matter. That is the aggregation problem the brief says isn't the scarce skill.

Time 2, signal 1, use 3, delight 1, ships 5. **Rejected.**

## 4. Copilot on every screen (obvious)

An "Ask" control on every screen that knows where you are. On a Syngene card it offers "Did they deliver on margins?"; on the book it offers "Who missed?".

Their morning: reads a results card, taps Ask, gets the margin promise from the January call with its page and the filed number beside it. That is exactly the "promised vs delivered" the brief values most, one tap from the push item.

It needs no model for questions about promises: the 22 ledgers already hold every promise with its quote, page, verdict and evidence, so matching a question to a company and a topic (margins, revenue, capex, debt, orders) is a lookup. A company outside the cache runs the existing live research.

Time 4, signal 5, use 3, delight 4, ships 4. **Kept as the pull half.**

## 5. A brief you finish (not obvious)

The morning is a short stack: the few things that need you, one after another. Each one is read, then kept for later or cleared. When the last one goes, the screen says you're up to date and how many routine filings it set aside for you, every one still a tap away. Tomorrow starts from where you left off: anything new since your last visit is marked.

Their morning: opens FINN, sees "4 to read" and the companies' names. Reads Syngene's results with the four lines and the promise that was due, clears it. Keeps the Syngene move for the 9 am meeting. Clears two management changes after reading who's coming in. "You're up to date. 48 routine filings set aside." Two minutes, and they know they've seen everything.

Time 5, signal 5, use 5, delight 5, ships 5 (frontend only, state in localStorage, works with the model off). **Chosen as the spine.**

## 6. Alerts as notifications (not obvious)

The things that crossed a line arrive as phone notifications: "Syngene rose 12.2%, past your 4% line." The line is printed on the notification, and moving it is one tap from there.

Their morning: the lock screen holds two notifications. Tapping one opens the brief at that item. In the app, the alerts since the last visit sit at the top of the brief as a notification stack.

FINN's data is a snapshot built after the close, so a real server push would promise something the pipeline doesn't do yet. The honest version: the alerts render as notifications at the top of the brief, each with its line, and "Turn on alerts" asks the browser's permission and shows a real system notification for anything new since the last visit when the app is opened. No background push is claimed.

Time 4, signal 5, use 4, delight 4, ships 4. **Kept as the push half, inside the brief.**

## 7. The word, book-wide (not obvious)

One screen ranks every management team in the book by whether it does what it says: kept, partly, missed, gone quiet, not due. Weakest first.

Their morning: not daily. Useful on a weekend or before a review. Strongest as the place a brief item links to ("Home First: 6 promises gone quiet").

Time 3, signal 5, use 2, delight 4, ships 5. **Kept as the second tab, Book.**

## Also considered

- **A time scrubber for the window.** Dragging through hours is fiddly with a thumb; four stops (since last visit, 24 h, week, month) do the job. The window control stays, as a short row of stops on the brief.
- **Swipe to clear.** Kept, with buttons beside it: a gesture alone is invisible, and swipes fight the browser's back gesture at the screen edge.
- **"What changed since you last looked."** Kept, as the default first stop of the window when the last visit was inside 24 hours.

## Scores

| Model | Time | Signal | Use | Delight | Ships | Total |
|---|---|---|---|---|---|---|
| 1 Chat | 2 | 3 | 2 | 2 | 3 | 12 |
| 2 Voice | 4 | 4 | 3 | 4 | 3 | 18 |
| 3 Dashboard | 2 | 1 | 3 | 1 | 5 | 12 |
| 4 Copilot | 4 | 5 | 3 | 4 | 4 | 20 |
| 5 Brief you finish | 5 | 5 | 5 | 5 | 5 | 25 |
| 6 Notifications | 4 | 5 | 4 | 4 | 4 | 21 |
| 7 The word, book-wide | 3 | 5 | 2 | 4 | 5 | 19 |

## The combination

The brief you finish is the spine. Alerts arrive at its top as notifications, with the line that set each off. Every item can be asked about in place, and the answer is promised against delivered, from the filings, with pages. The book-wide word and company research sit one tap behind.

**Point of view:** FINN is a brief you finish. Each morning it hands you the few things that changed, holds each one against what management promised, and lets you go.
