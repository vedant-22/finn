# Grade review (after the gemini-3.5-flash regrade, 28 Oct 2026)

`python3 evals/sample_grades.py` prints a fixed sample (seed 3) of 20 graded promises that have a verdict (kept, partly, missed, gone quiet). I checked each one by hand against the quote, the evidence and the quarterly numbers.

**Result: 18 of 20 hold up. 2 are wrong.**

| # | Company | Promise | FINN | Mine | Note |
|---|---|---|---|---|---|
| 1 | DIXON | Semi-auto washing machines in mass production by Mar 2026 | kept | kept | Later call says production started |
| 2 | TITAN | Eyewear growth 13-14% for FY26 | quiet | quiet | No full-year eyecare number given |
| 3 | TCI | 50 new branches this year | quiet | quiet | |
| 4 | DCMSHRIRAM | HSCL breaks even by year-end | quiet | quiet | |
| 5 | KFINTECH | MF industry crosses $1 trillion in 12-14 months | quiet | quiet | An industry call, not really the company's promise |
| 6 | SUNPHARMA | File Ilumya PsA by end of calendar year | quiet | quiet | |
| 7 | CROMPTON | Wires in select markets within 6-7 weeks | kept | kept | Launched in Q1 FY27 |
| 8 | CEATLTD | Customer transition over 3-4 quarters | kept | **pending** | 60% done, rest expected by end of Q2; the window runs to Q3 FY27. Graded early |
| 9 | TITAN | Jewellery margin 11-11.5% for FY26 | quiet | quiet | |
| 10 | DIXON | SSD mass production by Q2 FY27 | partly | partly | Slipped one quarter |
| 11 | DIXON | Display trials by Q2 FY27 | partly | partly | Slipped one quarter |
| 12 | DIXON | Tirupati expansion ready by Aug 2025 | missed | missed | Now Q3 FY27 |
| 13 | TCI | Add 100-200 trucks | quiet | quiet | |
| 14 | SYNGENE | EBITDA margin mid-20s for FY26 | kept | kept | FY26 OPM 25% |
| 15 | KFINTECH | Cross INR 2 trillion AIF by next quarter | quiet | quiet | |
| 16 | DCMSHRIRAM | Around 14% margin | missed | missed | OPM 14 → 11 → 9 → 7%. No date, but the trend is clear |
| 17 | DCMSHRIRAM | Commission ECH plant this quarter | kept | kept | Running at ~70% |
| 18 | HOMEFIRST | 6 new branches in Q2 | quiet | quiet | |
| 19 | CROMPTON | 1-1.5% price increase in January | kept | **not a promise** | It reported a price rise already taken. The evidence (17-18% cumulative on fans) is about something else |
| 20 | LT | Nabha Power sale by FY26 | partly | partly | Closed June 2026, one quarter late |

## What the two misses say

- **Graded before the deadline (#8).** The grader marked a promise as kept when the work was mostly done and the window was still open. The safer rule is to stay "not due yet" until the deadline passes or the work is fully done.
- **Statements about the past taken as promises (#19).** Extraction sometimes picks up "we took a price hike in January", which reports something already done. The grader then grounds it in an unrelated quote. A tense check at extraction would drop these.

Slips of about one quarter come out as "partly" and bigger slips as "missed" (#10, #11, #12, #20). That is consistent across the sample.
