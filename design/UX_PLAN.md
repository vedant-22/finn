# Folio: FINN's design system (stage 3 plan)

FINN's design system is called **Folio**. A folio is a numbered leaf of an account book, and in India it is also the number on an investor's holding. It is the page FINN keeps for each management team: what they said, and what happened.

This plan follows `brief/UX_SPEC.md`. Reference A is the base whose code was ported; references B and C were studied at 390x844 and 1440x900 (notes in the git-ignored research file). No reference is named in tracked files.

## What we keep from reference A
- The ENAM palette and its roles: white paper, ink #333333, grey #6A6970, rules #D9D9D9, ENAM blue #005DA3 kept rare, dark red #9E2B25 only for a missed promise, the warm panel #FBF8F2 for one block per page at most.
- The spacing scale (4 to 80), the 16 px gutter, the 560 px column, hairlines, one idea per block.
- The calm reveal: fade and rise on expo-decelerate, first blocks staggered; reduced motion shows everything in place.
- The accordion's grid-rows open, the sheet with a grab handle, the sticky Back bar, the ENAM-blue end band.

## What we take from reference B (investor calm)
- **Stat stacks:** a light serif figure, its unit as a serif word, one plain sans sentence, a hairline with air above it.
- **Index lists:** plain rows split by hairlines, a count and an arrow at the right, opening a full sheet.
- **Small square controls:** 6 px radius, 13 to 15 px medium sans, no pills for actions.
- **A quote with a round arrow** and **an occasional tinted band** in a pale ENAM blue (#F2F7FB).

## What we take from reference C (warmth and the before-and-after)
- **The visible before-and-after** as FINN's signature: raw words, the parts that matter marked and named in chips, then the clean result.
- **A floating rounded header bar** inset from the edges.
- **Rounded media cards** (20 px) with the picture in a rounded inset (14 px).
- **A big serif headline with one italic phrase**, at most once per screen.
- **Rounded chips in sentence case**, arriving with a small spring.
- **Short human micro-copy.**

## The six fundamentals, in Folio
1. **Wordmark.** Lowercase *finn* in the book serif at 600, after a 16 px ENAM-blue rounded square holding a white tick (the app icon, small). Not spaced caps.
2. **Alert lines.** The header has one small square Menu control. Menu opens a full sheet with an index list: Today, Book, Look up in serif, then an **Alert lines** row that says what is on ("6 kinds of filing, ±5% in a day, 3× volume") with an arrow; it opens the lines sheet. The end band's second button opens the same sheet.
3. **Fold rows.** "Worth a look" and "Routine filings" are index rows: serif title, one sans line naming what's inside, the count as a serif figure, an arrow. Each opens a sheet with its list. A sheet that was open is open again after Back from a company.
4. **The card.** The Folio card: white, 20 px radius, hairline border. A chip row (kind, time), the company in serif, a stat stack (serif figure, sans caption), one sans sentence, the 30-session picture in a rounded wash inset, and when the company made a promise on this topic, the before-and-after strip. It closes on a round arrow control, not "Read more".
5. **Type pairing.** Newsreader (a book serif with optical sizes, tabular figures and a proper ₹) for headlines, big numbers, quotes and company names; Inter at 400 and 500 with light tracking (-0.01em) for sentences and controls. Reference A's 450-weight tight sans headlines and serif sentences are gone.
6. **Status labels.** Rounded chips in sentence case with a small mark: Kept (tick, blue wash), Missed (cross, red wash, red text), Partly kept, Gone quiet, Not due, Can't tell (grey). Kinds (Results, Unusual day, People) are neutral chips. No caps micro-labels.

## The before-and-after (the signature component)
Three steps in one rounded block, read top to bottom, and on wide screens with a sticky step list at the left:
1. **They said.** The verbatim quote in the serif, the speaker and the call under it. The target figure is marked in pale ENAM blue and the date in pale amber, each with a mark that sweeps in.
2. **What FINN pulled out.** Chips name what was found, "Target found", "Date found" (only when the words are really in the quote), then the promise as one clean serif line: "Group revenue growth 15% by FY26".
3. **What the filings showed.** The status chip and the verdict sentence, with the source link.
Motion: the marks sweep (450 ms), chips arrive with a spring (cubic-bezier(.34,1.56,.64,1), 380 ms, staggered 90 ms), the promise and verdict fade up. Reduced motion: all in place.
Used on Today's card detail (the company's promise on that topic) and on every opened promise on the Company page.

## Screen blueprints (390x844)
- **Today.** Floating header. Meta line (snapshot time). Stat stack headline: serif figure "2" with "*need you*" as the one italic phrase, sans line "Out of 7 filings across 18 holdings." The window as a small segmented control (24h, 3 days, Week, Month). Folio cards. Index rows for Worth a look and Routine filings. The ENAM-blue end band rising with 28 px rounded top corners; square buttons.
- **Book.** Floating header. Serif headline "Your book" and one sans sentence. The tally as stat stacks in two columns (serif figures, hairlines), tappable to filter. "Weakest word first": holdings as index rows (name in serif, record figure "6/14", a status chip for the weakest promise, arrow).
- **Company.** Back bar. Chip row (sector, symbol), serif name, the record as a sans sentence, price as a stat stack, the picture in a rounded media card. "Their word": tally stat stacks, then promises as rows with status chips; opening one shows the before-and-after. Numbers, for and against, and sources as index rows that open in place.
- **Look up.** Serif headline with one italic phrase, a rounded field with a square button, Ready to open as index rows with records.

## Ordered checklist
- [x] 1. Folio foundations: tokens renamed into Folio, Newsreader loaded, type roles, chips, square controls, spring motion. Port reference A's remaining pieces (section header, modal/sheet, motion helpers) under Folio names
- [x] 2. Header: floating bar, new wordmark, Menu sheet with the index list and the Alert lines row
- [x] 3. Status chips everywhere caps labels were
- [x] 4. The Folio card on Today
- [x] 5. The before-and-after component, on Today's card detail
- [x] 6. Fold rows as index rows opening sheets
- [x] 7. Today finished: test at 390x844 and 320, flows and folds scripts, critic round, deploy
- [x] 8. Book: stat stacks and index rows; test, critic, deploy
- [x] 9. Company: header, before-and-after on every promise, index rows; test, critic, deploy
- [x] 10. Look up; test, critic, deploy
- [ ] 11. README shots, DESIGN.md (Folio), covering note, walkthrough; git grep for reference names finds nothing
