# ADR 6. Annual reports are read by rules

Status: accepted, 14 Nov 2026 (`annual-report`). Code: `finn/annual.py`, `pipeline/build_annual.py`. Evals: `evals/run_annual.py`, labels in `evals/annual_truth.json`, results in `evals/annual_result.txt`.

## Context

The brief names the annual report as a primary source and asks where management's story and the financials part. FINN read only calls. An annual report is 200 to 760 pages; the parts where story and numbers part are a few: the auditor's reports, the contingent-liability note, the related-party note. Their wording is set by regulation (SA 700, 705 and 706 headings, Schedule III's heads, Rule 11(g) for the audit trail, Ind AS 24), so it repeats across companies in a way prose doesn't. The link has no model key, and a figure an investor might repeat to management has to be right.

## Options

- **A model reads the cut pages.** Rejected: there is no key on the link, so it would ship nothing tonight, and a figure a model reads needs the same page check as a figure a rule reads, so the check is the work either way.
- **A model reads the whole report.** Rejected: 760 pages per company per year is the expensive way to find three notes, and the pages that matter can be found by their headings.
- **Rules read cut pages; a model only where rules can't, once there is a key.** Chosen for the rules half; the model half is designed below, not built.
- **Sum the heads of a claims note that prints no total.** Rejected: a sum is FINN's number, not the company's, and sub-rows ("the above includes") and per-head totals make a wrong sum easy. A figure is shown only as printed.

## Decision

- **Two stages.** `cut()` keeps the pages the reader needs, found by their headings, and sweeps the whole PDF for the headings an auditor uses to modify or stress a report; every hit must sit in a cut audit report or be out of scope by a named rule (a sustainability assurance report, the board's report, the secretarial audit). `read()` works only on the cut pages, which are committed (`evals/fixtures/annual_pages.json.gz`) keyed by the PDF's own page number with the PDF's sha256, so the readers and their evals run offline.
- **What is shown is held to its page.** A quote must be exact on the cited page once whitespace and hyphenated line breaks are joined: no fuzzy match, no neighbouring page. A figure is shown as printed, with its unit, both years under a header that puts 31 March 2026 first, or not at all. A note the rules can't read shows its page and says why.
- **The notes against the calls, by the auditor's own words.** For an emphasis of matter, the first term the auditor defines in the paragraph (‘CCI’, ‘EPR’, PLI) and its expansion are searched in the calls already on the page: the abbreviation case-sensitive and word-bounded, the expansion across line breaks. The page says what was measured ("Neither ‘CCI’ nor ‘Competition Commission’ appears in the 5 calls FINN read"), and the question says a term is absent only after three or more readable calls. Each negative line has a hand label on whether the calls discuss the matter in other words; one that did would withdraw the form for every company.
- **Questions from a fixed table**, at most two a company: an emphasis of matter; claims of at least a year's FY26 profit, on the same basis as the company file and only when profit is positive; claims up a quarter and by at least a tenth of profit. Where each fires over the 22 is pinned in the eval.
- **Measured against labels with a held-out half.** Labels were read by hand from the full PDFs. The readers were written on 11 reports and frozen; the other 11 were labelled and committed before the readers first ran on them. The first held-out pass is kept as it came out, and the fixes it called for are a second pass, reported apart.
- **The API never fetches an annual report.** Only the pipeline does, through `netguard` and a host allow-list, with its own 80 MB cap and 180 s deadline; the API keeps 40 MB and 45 s.
- **With a key, later:** a model reads only the notes the rules show as pages only (claims listed by head, a table with no unit), its output limited to a figure and the page it is printed on, and the same exact-on-page check decides whether it is shown.

## Trade-offs

- Rules read what they were written for. The first held-out pass missed Sun Pharma's audit reports ("Ind AS" in the heading) and showed one wrong figure, SRF's first sub-row taken for the total. Both were fixed in the second pass, but on the same half, so that pass isn't a held-out number.
- A claims figure shows for 8 of the 21 reports read. Most notes list claims by head without a total, and those show their page only.
- Auditor recall rests on three companies with an emphasis of matter, all in the dev half, and on the whole-PDF sweep: the held-out half had none, so it tests false alarms only.
- Related parties and the business overview aren't read. A first holding-company reader named the wrong company at one company and missed another; it was cut rather than shipped.

## Revisit when

- A key exists: build the model fallback above for the notes shown as pages only, and measure it on the same labels.
- The FY27 reports arrive (from June 2027): rerun the cutter on all 22, label at least 5 new reports before the readers see them, and keep the first pass as it comes out.
- A reader shows one figure that differs from its label: the rule that read it is withdrawn until a new held-out pass is clean.
