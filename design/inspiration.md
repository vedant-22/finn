# What FINN takes from the reference

Studied at 390×844 and in its source (tokens, type mixins, grid, motion helpers). Its name, copy and images are not used.

1. **One idea per screen.** A heading, one line under it, then the content. Nothing competes with the first number.
2. **Type does the work, no boxes.** Sections are separated by space and a 1px hairline, not by cards or borders. One tinted panel per screen at most, square corners.
3. **One sans, one serif.** Inter for headings, figures and controls; PT Serif for sentences that explain (the reference sets its descriptions this way). FINN's serif lines are the agent speaking.
4. **Medium weights, tight tracking.** Headings at 450–500 with negative letter-spacing (about −4% at 26–30px, −5% on big figures). Nothing heavier than 600.
5. **Mobile scale:** 72 / 30 / 26 / 21 / 16 / 14 / 12, line height 100% for big figures, 112–124% for headings, 140% for text.
6. **Spacing rhythm:** 4, 8, 12, 16, 24, 32, 48, 80. Gutter 16 on phones. Sections 48 apart.
7. **Hairlines, no shadows, no gradients.** #DCDCDE rules; the bottom sheet is the only raised thing.
8. **Pill controls.** Buttons and choices are full pills; the one primary action is filled, everything else is outlined or plain text.
9. **Small labels are rare and quiet.** 12px, muted, sentence case (FINN skips the reference's uppercase labels).
10. **Motion only on reveal.** Blocks fade in and rise 12px as they enter the viewport, 900 ms on expo-decelerate (cubic-bezier(.19,1,.22,1)), first three staggered 90 ms. Off under reduced motion. No scroll skew: an app reader needs the text still.
11. **Calm colour.** White ground, near-black text, one brand colour used rarely.
