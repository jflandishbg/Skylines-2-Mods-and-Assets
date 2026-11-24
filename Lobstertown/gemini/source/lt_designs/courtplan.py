"""Motor court layouts (ZP4): pure Python, no Blender, so the roster can import it for household counts.

plan(layout, W, D) -> dict(hh, items) where each item is (kind, rot, ox, oy): kind 'C' (front-row or rear-row cabin),
'W' (wing cabin), 'O' (office); rot degrees (0 faces the street, 90 faces +x, -90 faces -x); (ox, oy) is the middle of
the cabin's court-facing wall in lot coordinates (lot centre at 0, 0). Cell = 8 m.
"""
SIDE = 1.0                     # side yard
CABIN = dict(C=(6.0, 8.0), W=(5.6, 6.0), O=(8.0, 9.0))     # width, depth
PITCH = dict(C=5.94, W=5.54, O=7.94)
GAP = 5.0                      # the drive into the court
# per layout and lot: (front row tokens, left wing n, right wing n, rear row tokens)
TABLE = {
    "U": {(3, 5): ("OgC", 2, 2, "CC"), (4, 5): ("COgC", 2, 2, "CCC"), (4, 6): ("COgC", 3, 3, "C_C")},
    "L": {(3, 5): ("OgC", 0, 2, "CCC"), (4, 5): ("COgC", 0, 2, "CCCC"), (4, 6): ("COgC", 0, 3, "CCCC")},
    "R": {(3, 5): ("OgC", 3, 3, ""), (4, 5): ("COgC", 3, 3, ""), (4, 6): ("COgC", 4, 4, "")},
}


def _row(tokens, gap_w):
    ws = [GAP if t == "g" else gap_w if t == "_" else PITCH[t] for t in tokens]
    return ws, sum(ws)


def plan(layout, W, D):
    front, nl, nr, rear = TABLE[layout][(W, D)]
    X = 4.0 * W - .01
    yF, end = -4.0 * D + 1.0, 4.0 * D - .6
    items = []
    ws, tot = _row(front, GAP)
    x = -tot / 2
    for t, w in zip(front, ws):
        if t in "CO":
            items.append((t, 0, x + w / 2, yF))
        x += w
    ry = end - CABIN["C"][1]
    if rear:
        ws, tot = _row(rear, 8.0)
        x = -tot / 2
        for t, w in zip(rear, ws):
            if t == "C":
                items.append(("C", 0, x + w / 2, ry))
            x += w
    y0 = yF + CABIN["O"][1] + 2.0
    y1 = (ry - 2.0) if rear else end - 2.0
    for n, rot, xw in ((nl, 90, -X + SIDE + CABIN["W"][1]), (nr, -90, X - SIDE - CABIN["W"][1])):
        for j in range(n):
            yc = (y0 + y1) / 2 + (j - (n - 1) / 2) * PITCH["W"]
            items.append(("W", rot, xw, yc))
    hh = sum(1 for k, *_ in items if k != "O")
    return dict(hh=hh, items=items)
