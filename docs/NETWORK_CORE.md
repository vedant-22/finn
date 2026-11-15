# The Network core

Live at https://finn-network.vercel.app. Code in `finn/network/`, data in `data/network/`, checks in `evals/run_network.py`.

## What it does

It takes three inputs: the investor's contact list, the people named in company filings (already read by `finn/people.py`), and a small registry of organisations. From these it answers "who do I know who can help me understand this".

| Question from the brief | Method | Example on the demo data |
|---|---|---|
| Who should I call? | `who_to_call`, `company` | CEAT: a competitor's marketing head, a former plant head, and the man who bought tyres for Maruti, a CEAT customer |
| Second-degree reach | `reach` | HDFC Bank's new MD: Sanjay Bhatia, an invented contact, headed institutional equities at ICICI Securities, where the filing says Anup Bagchi was CEO & MD |
| Diligence on people | `diligence`, `team`, `prep` | Home First's new CFO: the path as the filing lists it, four contacts who can each answer one question about it, and one question for the room (the last role was interim) |
| Expertise map | `expertise` | Semiconductors: one person, the only contact who has made chips |
| Keeping the network warm | `warm` | A contact not spoken to since 2022 whose former employer just reported |
| Push: a material event | `for_event`, `for_filing` | SRF's ₹266 crore tax notice points to the contact who ran SRF's taxation until 2022 |
| What it notices | `notices`, `prep`, `patterns`, `one_call`, `only_one`, `coverage` | See below |

`ask.answer(net, question)` takes a direct question and routes it to one of these.

**What it notices that the investor wouldn't:**
- A contact has turned up in a filing (Rajat Shah, promoted at CG Power).
- A filing names someone who may be a contact, and it can't tell (HDFC Bank's new General Counsel is a Jigar Shah; the investor knows a Jigar Shah who is a banking lawyer). It asks; it doesn't assume.
- A filing names someone who shares a contact's name but is provably someone else (three cases in the demo). It says so, which stops the investor making the wrong match themselves.
- A change of designation is not an exit. Syngene filed four people ceasing within four days, but two of them were "Changed from SMP to Non-SMP category" and keep their jobs, so it counts two exits, the CFO and the head of strategy, under the three a pattern needs, and says nothing.
- **The path.** Someone arrives in a seat, and the filing lists where they came from. At each station FINN pins the one contact who can answer one question about it, written for what that contact can know without having met the person: the seat, the institution, the trade. Home First's new CFO: its former risk head on the seat, a former treasury head on IDFC Limited, a contact who is at the Dani family office now, and, because the filing lists no housing finance employer, the CFO of a competitor (the same seat means the same line of work and the same rank). It reads the filing and the investor's own records only, so it is the same with every public profile removed, and it never says two people overlapped. A seat at another firm that the filing's own profile opens with is a station too: CEAT's new independent director is filed as "Founder & CEO of Samara Capital Group", so a former principal there is asked what the firm held in that time, and what it holds today is a question for the room. An employer is matched only when the known name is the whole of what the filing wrote: "HDFC Life Insurance Company Limited" is not HDFC, and stays a bare station in the filing's words. Anyone with a desk at the company now is named at most, and never asked, at any station. Five paths show on the demo day.
- **Control seats.** Two or more different people leave seats in audit, risk, compliance, legal, the company secretary's office or finance at one company within 30 days, in separate filings. Within two days, Crompton's head of internal audit moved to another role in the company and its compliance officer resigned, with no successor filed; Push had folded the resignation as routine. The line holds only the company, the span, the filed titles and what each filing says happened; the evidence is each name, title, date and the filing's own reason, word for word. The seat is read from the title itself, so the head of a lending business is not a control seat. The person to ask is asked about the seats where that person sits, never about the people who left. A reason of retirement, superannuation or a completed tenure doesn't count, which is why HDFC Bank's two stay silent; nor does a death, or a change of designation with nobody leaving ("Changed from SMP to Non-SMP category"). "No disagreement with the management" is read as a denial, and "moved to another role" is said only when the filing says the move is within the company and the person did not resign. It fires at one company of 18.
- **One call, two answers.** A contact who is the person to ask at two or more companies this month, and inside none of them. Two qualify on the demo day; the rule raises one, the closer tie.
- **The only one.** The quiet contact who is the single person the investor knows to have worked inside a holding, when there is a reason to call now. One a day: the longest silence that has a reason. If an arrival's path already asks that contact about the company, it is said there, once ("Arvind is the only person you know who has worked inside CEAT; you last spoke in Oct 2021."). Otherwise the reason is a filing that fits what the contact did there, dated, with one question. No reason, no notice.
- **Who fits the question** (`fit`). One choice per company and kind of question, used by the card, Who to ask and Ask first: for a CEO, CFO or MD who left, someone who worked inside and left over a year ago, asked the seat question; for results, margins or guidance, someone at a competitor or a customer today, asked about their own seat ("How does the housing finance market look from Aavas Financiers?"). Nobody who has left is on a numbers row; nobody inside is asked.
- **A card of its own.** Control seats with a person to ask, and one call, carry a card; Today raises at most one a window, outside the count of what needs you.
- A reason to call must fit the person: a tax order is no reason to call a purchasing head. Each is dated by its reason, so Today's fold shows it only in a window that holds the reason; standing notes (where the investor is blind) are answered when asked, not pushed.
- Near misses: "both at ICICI Bank, in different years" is shown as ruled out, not as a link.
- Blind spots: holdings where nobody the investor knows has worked inside, and holdings where the only inside view hasn't been spoken to in two years.

## Key design choices

1. **No model in the network core.** The model's work ends at reading the filing. Matching people, scoring links and answering questions are rules. This keeps the contact list out of every prompt, makes every answer repeatable, costs nothing per question, and lets identity be tested exhaustively. Live answers take about half a second.

2. **A name alone never confirms a person.** `identity.judge` gives one of three answers.
   - *Same*: the names are compatible, something independent ties the two records (a shared employer or school), and nothing contradicts it. A shared employer counts for less the larger it is: one shared 200-person firm is enough, one shared bank of 200,000 is not.
   - *Different*: the known person was verifiably working elsewhere at the time, or the two careers share nothing.
   - *Possible*: shown as a question, and nothing further is built on it. The investor can settle it. They cannot overrule a contradiction.

3. **Same employer is not a link unless the years overlap.** Different years are reported as a near miss. If the filing gives no years the link is kept, marked "dates unknown", and scored at 40%. Two companies in one group (L&T and L&T Finance) are two employers.

4. **Link strength is arithmetic you can read.** It starts from the employer's size and rises with seniority, a shared line of work and years together. The app shows words (strong, fair, weak) and the evidence, never the decimal. Nothing weaker than a fair link is pushed; weak links appear only when the investor asks.

5. **Relevance comes before closeness.** Who to call is ranked first by what the person would know (time inside the company, then customer, supplier, competitor; how senior; how long ago) and only then by how warm the tie is. For an event, the person's line of work must fit the event: a tax notice goes to a tax head, not to a purchasing head who happened to work there.

6. **Silence is an answer.** A bond issue or an immaterial consumer-court order gets no network line. A question it can't place gets "no answer rather than a guess". An ambiguous name gets "which one?".

7. **A caution on inside information.** A contact who works at the company now, or left within a year, is flagged: keep the conversation to what is public.

## Data, and what is synthetic

- **Real:** the people in filings (name, role, previous employers, education), from the companies' own SEBI filings, each with a verified quote and page.
- **Synthetic, and labelled so in the files, the API and the app:** the investor and all 43 contacts. The employers are real companies; the contacts and their ties are invented. No scraping. Until 14 Nov the demo also held invented public profiles that added years to filing people's careers; `network-loop` deleted them and the code that attached them, so a real person carries only what the company filed.
- **Curated:** the registry (89 organisations, 20 schools, 57 themes, 8 supply links).

**For real:** the investor uploads a contact export and calendar history. Profiles come from a licensed provider or from each contact's consent, never scraped. Themes and supply links would be read from annual reports. The network would sit behind login and be stored per investor; the demo file `web/public/data/network.json` is public only because it is synthetic. Identity confirmations already stay on the device and travel with each request.

## How it was tested

`python3 evals/run_network.py` runs 334 checks with no model and no network access. All pass. Results are in `evals/network_result.txt`, and the rows below are its groups (15 Nov).

| Group | Result |
|---|---|
| Names (initials, word order, spelling variants, look-alikes) | 31/31 |
| Organisations and schools resolved from filing text | 29/29 |
| Identity on the demo's own traps | 9/9 |
| Identity, adversarial: every filing person given two invented namesakes (84 in all) | 0 false matches |
| Identity, recall: invented true records under a differently written name | 9/9 matched, counted as one check |
| Links: overlap arithmetic; every dated link in the data rests on overlapping years | 21/21 |
| Who to call, events, and what must stay silent | 28/28 |
| Direct questions: right kind of answer and right first name, 34 questions | 59/59 |
| The path, control seats, one call, the only one: the demo results exactly, invariants over all 42 filing people, firing counts over all 18 companies, fixtures, the cases that broke the first build in review, no year on a real person's earlier job, and every answer state of Same person or Someone else | 155/155 |

Also checked when the core was built (10 Nov): the app's then 27 tests passed; the four app surfaces were opened at phone width with no sideways scroll; the live API returned the right answers for a reach, an event, an ambiguous name and a question it can't answer.

## Limits

- The eval cases are mine, written alongside the rules. They show the rules do what I intended, not that the intent is right for a real network.
- The registry is hand-kept. A ticker outside it still gets an answer ("nobody has worked there"), but no competitors or suppliers.
- Questions are matched on words, so unusual phrasing can fall through to "no answer". A small model could route the question; it should still never write the answer.
- Most filing people have no years, so many links stay "dates unknown". Real profile data would fix that.
- The questions FINN puts to a contact are templates, nineteen of them in one table (`ASK` in `engine.py`), none naming a time. A model would write better ones and would need the contact list in a prompt, which the core doesn't allow.
- The path gives no years for a filing person and claims no overlap, and where a person has a path it is the answer everywhere, a direct "Who knows …?" included. Since `network-loop` a real person carries only filed fields: the five invented profiles and the code that attached them are gone.
- Results are a reason to call only when the filing carries figures, and the reason says them as the results card does ("DCM Shriram reported Q2 on 26 Oct: revenue up 20.9%, profit down 33.4% on a year ago."). In Today's fold a reason is left out when its company has a card.
- In the app the Network is a person beside the event (see The Network in `DESIGN.md` and `docs/NETWORK_PROGRESS.md`). A "possible" match is answered in the app (Same person or Someone else); the answer stays on the phone, applies only to a pair the engine asked about, and `/api/network` op `views` rebuilds every view from it with the same function the pipeline uses (`finn/network/views.py`).

## Run it

```
python3 pipeline/build_network.py     # after build_push.py; writes data/network/filings.json and web/public/data/network.json
python3 evals/run_network.py
curl -X POST https://finn-network.vercel.app/api/network -H 'Content-Type: application/json' -d '{"q":"Who knows the new MD of HDFC Bank?"}'
```
