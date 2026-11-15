"""Comparing two people's names.

A filing writes "Mr. S Ramkumar", a contact list "Ramkumar S"; one filing says "Sameer Anjaria" and the
next "Samir Kirit Anjaria". This module only says whether two names could belong to one person.
It never says they do: that needs a shared employer or school (see identity.py).
"""
import re

TITLES = {"mr", "mrs", "ms", "miss", "dr", "shri", "smt", "sri", "prof", "col", "capt", "maj", "gen", "justice", "late"}

DIFFERENT, COMPATIBLE, SAME = 0, 1, 2


def tokens(name):
    """'Mr. K. K. Maheshwari' -> (['maheshwari'], ['k', 'k']): full words and initials, titles dropped."""
    words = re.sub(r"[^a-z' ]", " ", name.lower().replace(".", " ")).replace("'", "").split()
    while words and words[0] in TITLES:
        words.pop(0)
    return [w for w in words if len(w) > 1], [w for w in words if len(w) == 1]


def fold(word):
    """Fold the common spelling variants of Indian names: Sameer/Samir, Sood/Sud, Reddy/Redy, Krishnamurthy/-thi."""
    w = word.replace("ee", "i").replace("oo", "u").replace("aa", "a").replace("ou", "u").replace("w", "v")
    w = re.sub(r"([tdkgbp])h", r"\1", w)
    w = re.sub(r"(.)\1", r"\1", w)
    return re.sub(r"y$", "i", w)


def compare(a, b):
    """SAME when every part of each name is accounted for in the other, COMPATIBLE when one merely
    leaves out or abbreviates what the other spells out, DIFFERENT when each has a part the other contradicts.
    """
    fa, ia = tokens(a)
    fb, ib = tokens(b)
    fa, fb = [fold(w) for w in fa], [fold(w) for w in fb]
    full = 0
    for w in list(fa):
        if w in fb:
            fa.remove(w); fb.remove(w); full += 1
    if not full:
        return DIFFERENT
    units = full
    exact = True
    for w in list(fa):              # a spells out what b abbreviates
        if w[0] in ib:
            fa.remove(w); ib.remove(w[0]); units += 1; exact = False
    for w in list(fb):
        if w[0] in ia:
            fb.remove(w); ia.remove(w[0]); units += 1; exact = False
    for i in list(ia):              # the same initial on both sides
        if i in ib:
            ia.remove(i); ib.remove(i); units += 1
    left_a, left_b = fa + ia, fb + ib
    if (left_a and left_b) or units < 2:
        return DIFFERENT            # each has a part the other lacks, or only one word in common
    return SAME if exact and not left_a and not left_b else COMPATIBLE


def clean(name):
    """The name as shown: titles dropped, spacing fixed, the filing's own spelling kept."""
    words = name.replace(".", ". ").split()
    while words and words[0].lower().strip(".") in TITLES:
        words.pop(0)
    return " ".join(words).replace(" .", ".")
