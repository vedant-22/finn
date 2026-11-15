# What a 10 looks like for FINN

Written 1 Nov, 01:00 IST, from the two ENAM documents (via docs/BRIEF_TRACE.md), docs/INVESTOR.md, the critic notes in docs/PROGRESS.md, spec sections 9 to 11, and a side-by-side of v4 and live at 390×844. The benchmark is v4. When in doubt, the ENAM documents decide: "shows them only what's important", "burying everything else, beautifully", "core, concise, beautifully presented, and interactive", "thin-but-working beats broad-but-broken".

Every criterion is something a critic can check on a screenshot, a clip or a tap. A 10 needs every criterion on its axis; a 9 allows one miss; an 8, two.

## The axes

### 1. Calm on entry (how little the first screen asks of you)
- The first screen at 390×844 holds at most five things: the wordmark, one count, one sentence, the window, and the top of the first card. No list of rows, no settings, no toggles.
- The eye lands on one figure (the count) within 2 seconds; nothing else on the screen is the same size or weight.
- There is no button you must press to begin. Scrolling is the action.
- Nothing on entry is a control you have to understand (no step bars, switches, filters, or "Listen" competing with the count).
- Everything beyond the two or three things that need you sits behind "Read more" or a fold.

### 2. Clean
- One type family for the interface (Inter), plus PT Serif in plain roman grey for the one sentence under a title and for quotes. No italics anywhere. No serif figures.
- At most four type sizes on any one screen, all from v4's scale (72/48/40/30, 26, 21, 16, 14, 12 caps).
- Spacing comes from one scale (4 to 80), and sections are separated by space or one hairline, never both a hairline and a box.
- No borders except on controls and hairline rules; no shadows; square-cornered warm panels.
- Every row on a screen is aligned to one left edge (16 px gutter) at 390 and 320.

### 3. Beauty (colour and warmth included)
- Warm #FBF8F2 panels hold the content blocks; ENAM blue #005DA3 appears as a full-colour moment at most once per screen (the end band, the questions block) and otherwise only on what you can tap.
- Text on blue is white; every pair passes WCAG AA (4.5:1 body, 3:1 for 24 px and up and for marks).
- Big figures are set in Inter at 72 or 48 px with a smaller unit, as v4 set them: the number is the picture.
- Each card has one picture (the price line) or one big figure, never a crowd of small ones.
- A screenshot of any screen would look at home as a page of a well-made research publication.

### 4. Clarity (what matters, and why)
- Each card says what happened in one line and names the line it crossed; the four results figures (revenue, EBITDA, PBT, PAT, with QoQ and YoY) are one tap away.
- Status words are words, coloured: Missed in red, Gone quiet in amber, Kept in green, Not due in grey. No glyphs.
- Counts agree everywhere (hero, folds, end band, Book).
- Every figure names its period and its session ("today", "yesterday", a date), and its source is one tap away.

### 5. Ease
- Everything an investor does in the four moments of INVESTOR.md is at most two taps from the screen they're on.
- Tap targets are 44 px; the tab bar is reachable with one thumb; Back returns to the same scroll position.
- Changing the window or a line changes what is shown at once, and says how many things it changed.
- Look up takes a symbol, a name or a question in the same field.

### 6. Motion
- Animated properties are transform and opacity only; 150 to 400 ms; one easing family (v4's expo out for reveals, decelerate for folds and sheets).
- Every motion explains something: where a view came from (a card opening into its full view and closing back), what changed (figures settling to a new window), or what is in focus (the card under the thumb).
- Nothing loops except a working indicator; nothing moves on its own after the screen settles.
- With reduced motion on, every view appears at once and nothing is lost.

### 7. Trust and grounding
- Every promise shows the quote, the call it came from and the page; every verdict shows the filed number it was checked against.
- Ask answers only from the filings, with the page, and says "not found in the filings" when it isn't there.
- No buy or sell language, no price forecasts, no invented figures. Cached data is labelled with its time.

### 8. Daily use
- The brief ends: a full-colour end band says the window is done ("That's the last 24 hours") and what to do next.
- What is new since the last visit is marked, and alerts can come to the phone with the line that set them off.
- The book's word (who keeps promises) is one tab away and sorted weakest first.

### 9. States
- Loading is a skeleton in the shape of the screen, never a spinner. First run, empty window ("Nothing crossed your lines"), offline, error, out of model quota and unknown symbol are each designed, with a next step.

### 10. Accessibility
- AA contrast everywhere (scripted), visible focus, 44 px targets, no sideways scroll at 320 px, real buttons and headings, reduced motion respected.

### 11. Overall
- An investor would open it every morning, and could explain the point of view after one use: "FINN shows the few things that need me, and whether management kept its word."

## Screen by screen: v4 against live (1 Nov)

| Screen and element | v4 | Live (round 3) | Clearer | Keep |
|---|---|---|---|---|
| Home: the count | "2 need you", Inter 72 | "2 to read", Newsreader 72 | v4: sans, no serif display | v4's, with live's count logic |
| Home: line under it | one grey serif sentence | two lines, one a link | v4 | v4's form, live's words ("4 more worth a line" goes in the fold) |
| Home: window | words under the count | above the count | v4: count first, then the knob | v4's place |
| Home: entry action | none, scroll | "Read the brief" pill, then a stepper reader with "1 of 6" bar | v4 (the bar was flagged as bad) | no reader bar; the card opens in place |
| Home: what needs you | two warm cards: price line, big figure, one line, Read more | rows with three lines each and a small sparkline | v4 for calm; live for content (CFO exit, profit, line crossed) | v4's card, live's lines inside "Read more" |
| Home: the rest | folds "Worth a look (4)", "Routine filings (3)" | rows with chevrons, alerts switch, Your lines row | v4 | v4's folds; alerts and lines move into the Your lines sheet |
| Home: the end | blue band "That's the last 24 hours." with two buttons | none on the home screen | v4 | v4's band |
| Home: Listen | none | top right | live has the feature, but it competes on entry | Listen moves to the end band and the card's full view |
| Card opened | inline Read more: the table, people, their word, sources | full-screen reader with step bar, Keep and Done | v4 for calm; live for the step-by-step finish | Read more on the card, opening as a shared-element view |
| Book: tally | four big Inter figures in a warm panel | four coloured cells / a four-colour bar with serif numbers (flagged) | v4 | v4's panel, status words coloured only in the small label |
| Book: holdings | two-column warm tiles, weakest first | one-column rows | v4 for beauty; live rows scan faster | v4's tiles |
| Company: top | warm panel, name with the verdict in grey, price and size | white, serif name, verdict line, big serif price | v4 | v4's |
| Company: price line | full bleed, "Last 30 sessions, −1.3%" | inset, smaller | v4 | v4's |
| Company: their word | tally panel, then promise by promise with big figures | two rows, then "Still running 10" | v4 for beauty; live for status first | v4's grid, live's corrected verdicts and pages |
| Company: Ask on the next call | blue block, numbered serif questions | white, numbered | v4 | v4's blue block (the screen's one colour moment) |
| Company: folds | New on the latest call, The numbers, For and against, Read for this page | same, as chevron rows | v4 | v4's folds |
| Look up | "Look up any NSE company", big underlined field, "Check their word", warm tiles "Ready to open" | "Ask" with a search pill, "Try" questions, "Outside your book" rows | v4 (the user called it amazing) | v4's, verbatim, with today's search (name or symbol), live research and Ask behind it |
| Tab bar | Today, Book, Look up | Brief, Book, Ask | v4 | v4's labels; Ask lives in Look up and on each company |
| Type | Inter + PT Serif roman grey | Inter + Newsreader, an italic phrase | v4 | v4's exactly |

## Gap analysis (my own score of live against the rubric, 1 Nov 01:00)

| Axis | Live | v4 | The gap |
|---|---|---|---|
| Calm on entry | 6 | 9 | live opens on a button, two dense rows, four settings rows |
| Clean | 7 | 9 | two families, serif figures, rows with three lines |
| Beauty | 6 | 8.5 | one white plane; v4 had warm panels, big sans figures and a blue end |
| Clarity | 8 | 6.5 | live's copy fixes (dates, line crossed, profit in rupees) are better |
| Ease | 7.5 | 7.5 | live's reader is a detour; v4 had no Ask |
| Motion | 6 | 7 | both mostly fade; no shared-element opening, no focus |
| Trust | 8.5 | 7.5 | live has Ask with pages and corrected verdicts |
| Daily use | 7.5 | 7 | live has alerts and since-last-visit |
| States | 8 | 6 | live has skeletons, quota and offline |
| Overall | 7.5 | 7.5 | |

So: v4's look and placement with live's content and states would score above both.

## Backlog, in order of effect on the score

1. **Type to v4's exactly.** Inter for titles, figures, labels, controls; PT Serif roman grey only for the sentence under a title and quotes. Remove Newsreader and every italic. (clean, beauty, typography for every critic)
2. **Colour to v4's:** white paper, warm #FBF8F2 panels and cards, ENAM blue moments with white text; scripted AA check (web/scripts/contrast.py over the tokens).
3. **Look up restored** from v4's code: banner, the big field, "Check their word", "Ready to open" tiles; today's name search and live research behind it; a question typed in the field goes to Ask; the tab is Look up again.
4. **Home as v4's Today:** count, grey sentence, window, two warm cards (price line, big figure, one line), "Read more", folds Worth a look and Routine filings, the blue end band. Live's lines (CFO exit, profit, the line crossed) go in the card. No "Read the brief" button, no step bar.
5. **Card opening:** "Read more" opens the card's full view (results table, management change with background, their word, sources, Ask here, Listen) with a shared-element transition; close shrinks it back. Reduced motion: no transition.
6. **Book as v4's:** the warm tally panel of four Inter figures with plain words, partly kept as a quiet line; "Weakest word first" tiles; status label coloured small.
7. **Company as v4's:** warm top with the verdict, full-bleed price line, their word with Read more, tally, promise by promise, blue "Ask on the next call", folds; live's corrected verdicts, pages and Ask here.
8. **Your lines sheet** holds the alerts switch and the lines; the home screen keeps only a "Your lines" pill in the masthead, as v4 did.
9. **Motion pass (11b):** cards rise into view in a light stagger; the card under the thumb in focus; folds expand with content fading up; figures settle; the price line draws. Clip each at 390×844, keep what helps, log it in DESIGN.md.
10. **States in v4's look:** skeletons shaped like the warm cards, the quiet window, offline, quota, unknown symbol.
11. **Panel round** with v4's shots blind, on this rubric; fix what two agree on; repeat.
12. Docs: DESIGN.md, README shots, covering note, walkthrough, BRIEF_TRACE.
