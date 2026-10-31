# FINN's colour pairs for contrast.py: each ground, and the text and marks set on it, with the ratio each needs
GROUNDS = {'paper': '#FFFFFF', 'panel': '#FBF8F2', 'band': '#005DA3'}
INK = [('ink', '#333333', 4.5), ('ink-2', '#6A6970', 4.5), ('brand', '#005DA3', 4.5),
       ('missed', '#9E2B25', 4.5), ('quiet', '#94600A', 4.5), ('kept', '#24704A', 4.5), ('rule as a switch outline', '#6A6970', 3)]
PAIRS = {
    'paper': INK,
    'panel': INK,
    'band': [('white', '#FFFFFF', 4.5), ('white 82%', 'rgba(255,255,255,.82)', 4.5), ('white 70% underline', 'rgba(255,255,255,.7)', 3)],
}
