# Brief analysis

## What they grade, in their words
- "creativity, product sense, judgment, and architecture — not completeness"
- "Thin-but-working beats broad-but-broken." "A demo that doesn't run is the worst outcome."
- "The scarce skill is not aggregating information. It's filtering it."
- "The best submissions will show a point of view about how an investor should interact with this, not just what data to show."
- "no AI slop … feel like a product someone thought hard about, not a model filling a template. Density and design both count."
- Narrative vs numbers: "the difference between summarising management and analysing them — and it's the kind of thing we value most."
- Efficiency is a bonus: "cheap models for bulk extraction, a stronger model only where reasoning demands it), caching, and chunking."
- "We may point it at a company you didn't pick." Pull must generalise to any NSE ticker.

## The user
An analyst or PM at a lean, long-only Indian fund. Holds 15-20 names with a thesis on each. Their day: pre-open scan of overnight filings on NSE/BSE, a couple of concalls, results season means 5-10 results a week across the book, reading transcripts at night. Today they use the NSE announcements page, screener.in, WhatsApp groups, a broker terminal, and Excel where they keep track of what management said last quarter. That Excel sheet is the part nobody builds software for.

## Phrases taken apart
- **"surfacing the few things that actually matter and burying everything else"**: the burying is half the product. A good day should look nearly empty.
- **"what changed and why you should care"**: the why is relative to something. For a long-term holder it is relative to the thesis and to what management said they would do.
- **"let me pick the period"**: window control is a hard requirement on the digest.
- **"I decide what unusual means"**: thresholds must be user-set and must visibly change what is shown.
- **Management change → bio**: they want who the person is, at a glance. LinkedIn is named as an example. The appointment filing itself carries a "brief profile" under SEBI LODR, so the primary source already has it.
- **Results → Revenue, EBITDA, PBT, PAT, QoQ and YoY**: exact numbers. NSE publishes results as XBRL, which means these can be parsed rather than guessed by a model.
- **"For every other announcement type, decide what earns my attention … That judgment is the point."**: the triage policy is graded. It should be written down and visible.
- **Pull "grounded in primary sources" only**: enforce in code; cite document and page; say "not in the filings" when absent.
- **"Worked example — numbers vs. narrative … what was promised vs. what was actually delivered"**: the single most valued output. Most entrants will treat it as one of eight tabs.

## What a tired evaluator has seen 100 times
A chat box over a dashboard of cards. A feed of every filing with an AI summary each. A "Research" tab that is a wall of eight generated sections. Purple gradients. Sentiment scores. "AI insights".

## What would stop them scrolling
A product whose organising idea is the thing they value most: holding management to its word. A feed that is mostly silent. A results card that says "they said 20% margin, they did 17.4%" with the page cited.

## The lazy reading
Scrape announcements, LLM-summarise each one, show a feed with category chips, plus a chat box that answers questions about a company using RAG. Ten tabs, none of them sharp.

## Hard constraints
- Deadline Sun 1 Nov 2026. Mobile-first prototype, deployed link easy to open on a phone.
- Public GitHub repo, AI build history, covering email writeup (built, decisions/trade-offs, left out, next).
- Portfolio 15-20 NSE/BSE names; 3-5 pull demo names; pull must work on any NSE ticker.
- Data: EOD price/volume, NSE/BSE announcements, annual reports + concall transcripts (screener.in links).
- Pull: primary sources only, no model outside knowledge.
- Free tiers are enough. Spend less, score more.
