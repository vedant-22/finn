# Motion notes

The motion copy (https://finn-ledger-motion.vercel.app, branch `motion`) adds a few of the reference design's scroll effects to FINN. Content, layout, colours and type are unchanged. Each effect was judged from frame strips at 390×844 and 1440×900 (`web/test/e2e/scroll.py`) against the submitted look, and the whole set again at the end.

## Kept
- **Header hide and show** (`useHideOnScroll`): the masthead and the company bar slide away on the way down and come back on any scroll up, so reading gets the whole screen and Back is always one flick away.
- **Opening drift** (`useDrift`): Today's opening and the company header lag up to 30px as they scroll off. It's a soft parallax that never reaches the content below.
- **Reveal** (`startReveal`): blocks fade in and rise 12px on expo.out, 80ms apart (four at most), so a screen of cards arrives in order and settles in about 0.7s.
- **Ready to open as a row with a scroll thumb** (`useThumb`, Look up): the companies snap one at a time, the next one peeks in, and a 2px thumb shows where you are. It turns a list of rows into one row and keeps FINN's hairline style. Its tiles skip the reveal, so a swipe shows them at once. With reduced motion it stays the vertical list.
- **Read more label** (`startCursorTag`, desktop with a mouse only): over a Today card's picture, a small blue "Read more" pill grows out of the pointer and follows it a beat behind, and a click on the picture opens the card, as the label says. It only shows over the picture, as the reference keeps its label to media: over the whole card it covered the sentence you were reading. It never runs on touch, below 1024px, or with reduced motion.
- **Pictures settle about the latest price** (`useSettle`, replacing the dropped chart scale): a card's picture comes in at 1.15 and settles to 1 by the time it has risen 40% of the screen. It scales about its last close at the right edge, so the latest price never moves and is never clipped. Only the oldest sessions wait outside the plate, and they're in before the picture is anywhere you'd read it. Anything on screen at load is already at 1.
- **Hover, as the reference's cards and lists** (CSS, hover-capable pointers only): a Today card's picture grows 4% about its latest price over 400ms, Book's and Look up's names turn blue, and a tab looks chosen. On desktop a click target now answers the pointer, where it used to do nothing.
- **The header comes down as the app opens** (`useEnter`, from the reference's header script): on a load the masthead slides down into place (−100% to 0, 0.6s, expo.out) while the page fades in, and both land by about 300ms. It happens once a load, so the header shows it slides before it first hides on scroll. A header that mounts later (another tab, a company page) is simply there, and one that mounts mid-slide (the loading screen's, then Today's) carries on from where the slide had got to.

## Removed
- **Chart scale on scroll, as first ported** (1.15 to 1, centred): FINN's pictures are price charts. At 1.15 the clip cut off both ends of the line, which hid the latest price until the card reached the top. The settle above replaces it.
- **Velocity skew** (desktop, the reference's light 0.02 multiplier, 4° at most): at reading speed it peaked near 0.1°, too small to see. At a fast fling it reached 0.6°, enough to put Book's two columns about 5px out of step and soften the text mid-scroll. All cost, no gain on a quiet ledger. It's in history (`43c6259`) if wanted.

## Not done
- **Book's grid as a row**: left as the grid. A ranked list of eighteen holdings scans faster in two columns than one tile at a time.
- **Prev and next buttons on Look up's row** (the reference slider's desktop control): they'd add UI, and this copy changes motion only. With a mouse the row scrolls by trackpad or shift and wheel.

## The rest of the reference's motion, and why it stayed there
Its other moving parts were checked against FINN. The hover states and the header's entrance came over, as above. These didn't:
- **The menu dropping open, its links sliding in**: FINN has no menu, and one would be new UI.
- **Page headers fading in line by line** (120ms apart): a company page's header already arrives inside the card's morph, and Today's count already rolls. A second entrance on top of either would only hold the words back.
- **An arrow that slides out and back in on hover**: FINN shows no arrows.
- **A strip of pictures drifting sideways as the page scrolls**: FINN has no such strip, and its only sideways row is one you scroll yourself.
- **The banner and the card slider**: already here, as the opening drift and Look up's row.

## Final pass
Every scene in `scroll.py` (Today, Book, a company page, Look up's row, the hover, the load) was recorded at 390×844 and 1440×900, for this copy and for the submitted look, and the frames read side by side. At rest every frame matches the submitted look line for line. The differences show only mid-scroll: the header away, the opening a few pixels behind, a card on its way in. Nothing was heavy enough to take out at this stage.

## Checks
- Smoothness (`smooth.py`, 390×844, the CPU slowed 4×): under 1% of frames go over 20ms on Today, Book and a company page, and the longest is 33ms, the same as the submitted look.
- `flows.py` against the motion link, after the last deploy: 40 of 40 ok, no page errors. `folds.py`: every fold opens in view, nothing left moving.
- With `prefers-reduced-motion: reduce`, every hook returns early and the content shows in place. The header has no transform at load or after a scroll, nothing on the page holds one, every card is at full opacity, Look up's row is the list, and the cursor label isn't even created.
- On a phone (touch, 390×844) a tap on a card's picture does what it did before: nothing. Only Read more opens the card.
