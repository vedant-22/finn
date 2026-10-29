# FINN design

FINN follows the reference design system (studied at 390×844 and in its source; see `design/inspiration.md` and `design/PLAN.md`) in ENAM's colours. None of its branding, photos or copy is used.

## Idea
- **A title and one sentence.** Every card says one thing; the rest waits behind "Read more" or a fold.
- **Figures lead.** Tallies and promises are set as outcome figures, a big number with its unit set smaller on the baseline.
- **Status is a word.** KEPT, MISSED, GONE QUIET, PARTLY KEPT, NOT DUE, CAN'T TELL, in small caps. No marks or icons.
- **The card's picture is the stock.** Where the reference puts a photo, FINN draws the last 30 sessions of the holding's price.

## Colour
| Token | Hex | Role | Contrast on white |
|---|---|---|---|
| paper | #FFFFFF | page | |
| panel | #FBF8F2 | cards, tally grids | |
| ink | #333333 | text, figures | 12.6 |
| ink-2 | #6A6970 | secondary text (ENAM grey) | 5.4 |
| rule | #D9D9D9 | hairlines, idle switch track, volume ticks | |
| brand | #005DA3 | ENAM blue: wordmark, the one filled button, outlined pills, Read more and links, the chart line, the active tab, switches when on | 6.8 |
| brand-pressed | #004A82 | the filled button and links while pressed | |
| missed | #9E2B25 | the word MISSED, nothing else | 7.4 |

Moves and changes are ink with a sign and a true minus; there is no green or red for up and down.

## Type
Inter (variable) and PT Serif, both bundled. The reference's mobile mixins:
- Outcome large: 72/100%, 500, −3.6px; unit 36px. Outcome: 48/100%, 500, −2.4px; unit 24px. Smaller steps 30 and 24 for long figures.
- Page title 30/112% 450 −1.04px. Section head 26/116% 450 −1.1px with a hairline under it. Card title 21/124% 500 −0.36px.
- Body 16/140% −0.42px. Small text 14/140%.
- Label: 12px uppercase, 450, +0.24px.
- PT Serif 400 16/140% for the one sentence under a title (card sentences, the read, page descriptions), muted.

## Space and shape
Spacing scale 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 60, 80. Gutter 16. Cards: panel, square corners, 16px inside, the picture inset at the top. Pills are full radius (1000px). The bottom sheet's top corners are 12px. No shadows, gradients or glass.

## Components
- **Masthead**: FINN wordmark (brand, 600, 0.08em tracking) left; one outlined pill right ("Your lines" on Today). Hides on the way down and returns on the way up.
- **Section head**: 26px title, no rule, one serif line under it.
- **Page header** (company page, Book): a warm panel edge to edge with a 12px rounded foot. On a company page: the sector and symbol as a caps label, then a 30px title where the name in grey runs into its record in ink ('Larsen & Toubro. 1 of 3 promises kept, 1 partly.'), then the price line in serif; the 30-session picture runs edge to edge on white under it. Book's holds its title, serif line and the tally. The masthead or Back bar is warm while it sits over the panel.
- **Card**: picture, caps label (the kind), title, outcome figure with a muted caption, one serif sentence, then a foot row 32px below: "Read more" left (opens an accordion with the detail and sources), when it happened as a quiet label right. Cards with a picture stay warm; the one ENAM-blue block is a company's 'Ask on the next call', which is text only.
- **Window choice** (Today): four words in a row, the one that's on in ink with a 2px brand rule under it, as the tab bar.
- **Tile** (Book after its lead, Look up): two columns of warm cards. On Book: status label, name, record figure, the weakest promise in serif, the price at the foot. On Look up: the symbol over the name.
- **Outcomes grid**: two columns, number, one dark line, one muted line, a link. A company's promises keep their figures in one 48px band so every row's sentences start level.
- **Fold**: hairline above and below, 21px title with a count, a plus that turns into a minus; opens on a grid-rows transition.
- **Buttons**: one filled brand pill per screen at most; the rest outlined brand pills or plain text.
- **Switch**: grey track off, brand track on, white knob.

## Motion
- Reveal: blocks fade in (opacity only) over 1200 ms on expo-decelerate as they enter the view; the first cards step 120 ms apart.
- Today's count: on the first open of a session it falls from the filing count to what needs you (the sieve); switching windows rolls it in 320 ms.
- Accordions open in 200 ms (decelerate) and close in 100 ms; the plus turns with them.
- The masthead slides away on scroll down (400 ms, expo).
- Sheets slide up 220 ms. Rows dim while pressed; pills fill brand.
- Waiting: nothing under 400 ms, then one muted line with a pulsing brand dot.
- `prefers-reduced-motion`: everything appears in place.

## Words on screen
Speak to the investor. Sentence case except labels. Numbers before adjectives. A card gets one sentence.
