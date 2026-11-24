"""Architectural rulebook checker (rules 1-10 + rule 15 closed solids), ported from Lobstertown nf_rules.

Each wall(), cornice(), balcony(), lucarne(), and roof_check() call reports to the active mesh's
Rules tracker. finish() raises RuleError listing every violation unless explicitly waived with a reason.
"""
from collections import Counter
from .math_compat import Vector

NUM = {
    "corners": 1,
    "rhythm": 2,
    "axes": 3,
    "shape": 4,
    "order": 5,
    "balance": 6,
    "glass": 7,
    "clearance": 8,
    "cornice": 9,
    "dormers": 10,
}

FLOOR = ["ground floor"] + [
    f"{k}{'st' if k % 10 == 1 and k != 11 else 'nd' if k % 10 == 2 and k != 12 else 'rd' if k % 10 == 3 and k != 13 else 'th'} floor"
    for k in range(2, 51)
]


class RuleError(Exception):
    """Raised when one or more architectural or closed-solid rules fail."""


class Rules:
    def __init__(self):
        self.bad = []
        self.waived = []
        self.walls = []

    def flag(self, key, where_str, msg, waive=None):
        if waive and key in waive:
            if not str(waive[key]).strip():
                self.bad.append(f"Rule {NUM[key]} ({key}) is waived at {where_str} without a reason")
            else:
                self.waived.append(f"rule {NUM[key]} ({key}) at {where_str}: {waive[key]}")
            return
        line = f"Rule {NUM[key]} ({key}), {where_str}: {msg}"
        if line not in self.bad:
            self.bad.append(line)


def rules_of(m):
    if not hasattr(m, "rules"):
        m.rules = Rules()
    return m.rules


def where(w):
    a, b = w.P(0, 0), w.P(w.L, 0)
    if abs(w.n.y) > 0.9:
        side = "street front" if w.n.y < 0 else "back-facing wall"
        return f"{side} at y {a[1]:.1f} (x {a[0]:.1f} to {b[0]:.1f})"
    side = "right-facing wall" if w.n.x > 0 else "left-facing wall"
    return f"{side} at x {a[0]:.1f} (y {a[1]:.1f} to {b[1]:.1f})"


def floor_of(h, spec):
    if h[4] in ("door", "shop", "bay"):
        return 0
    for f, s in enumerate(spec):
        if abs(s[1] - h[2]) < 1e-6 and abs(s[2] - h[3]) < 1e-6:
            return f
    return None


def surround(h, so, key):
    """Return bounding (u0, u1, z_low, z_high) for a window or door surround."""
    u0, u1, zb, zt, kind = h
    if kind == "shop":
        return (u0 - 0.36, u1 + 0.36, 0.0, zt + 0.66)
    lo = 0.0 if kind == "door" else zb if kind == "fwin" else zb - 0.14
    return (u0 - so, u1 + so, lo, zt + (0.34 if key else 0.24))


def overlap(a, b):
    return a[0] < b[1] - 1e-6 and b[0] < a[1] - 1e-6 and a[2] < b[3] - 1e-6 and b[2] < a[3] - 1e-6


def check_wall(m, w, st, s, e, bays, H, door, z0, trim, quoin, bands, waive):
    R = rules_of(m)
    trim = trim or {}
    so, key = trim.get("so", 0.28), trim.get("key", True)
    spec, low = st["win"], st.get("low", ())
    at = where(w)
    boxes = [surround(h, so, key) + (h,) for h in H]
    R.walls.append(dict(w=w, bays=[w.u_of(c) for c in bays], boxes=boxes, top_w=spec[-1][0] if spec else 0.0, spec=spec))
    if door and not any(abs(door[0] - c) < 1e-6 for c in bays):
        R.flag("axes", at, f"the door at {door[0]} is not on one of the bays {bays}, so it would not be built", waive)
    if not H:
        return

    # Rule 1: corners
    hs = sorted(H)
    for end, ty in (("start", s), ("end", e)):
        if end == "start":
            pier = min(h[0] for h in hs)
            near = [h for h in hs if h[0] - pier < 0.3]
        else:
            pier = w.L - max(h[1] for h in hs)
            near = [h for h in hs if w.L - h[1] - pier < 0.3]
        wd = max(h[1] - h[0] for h in near)
        shop = any(h[4] == "shop" for h in near)
        if ty == "x" and quoin and st.get("quoin_from") is not None:
            need, why = max(wd, 0.85 + so + 0.01), "an outside corner with quoins"
        elif ty in ("x", "c"):
            need, why = max(0.6 * wd, 0.6), "an outside corner" if ty == "x" else "an inside corner"
        else:
            need, why = (0.6 if shop else max(0.5 * wd, 0.6)), "a party-wall end"
        if pier < need - 1e-3:
            R.flag(
                "corners",
                at,
                f"only {pier:.2f} m of wall between the opening and {why} at the {end}; "
                f"needs {need:.2f} m (opening {wd:.2f} m wide). Move the bay inward or narrow it",
                waive,
            )

    # Rule 2: rhythm
    us = sorted({round(w.u_of(c), 3) for c in bays})
    sp = [b - a for a, b in zip(us, us[1:])]
    if len(sp) >= 2 and min(sp) > 0 and max(sp) / min(sp) > 1.3:
        R.flag(
            "rhythm",
            at,
            f"bays are unevenly spaced ({min(sp):.2f} to {max(sp):.2f} m apart); keep them within 30%",
            waive,
        )
    floors = {}
    for h in H:
        floors.setdefault(floor_of(h, spec), []).append(h)
    for f, row in floors.items():
        row = sorted(row)
        for a, b in zip(row, row[1:]):
            if "shop" in (a[4], b[4]):
                continue
            gap, wa, wb = b[0] - a[1], a[1] - a[0], b[1] - b[0]
            if gap < 0.7 * min(wa, wb) - 1e-3:
                R.flag(
                    "rhythm",
                    at,
                    f"{FLOOR[f or 0]}: only {gap:.2f} m of wall between openings; needs {0.7 * min(wa, wb):.2f} m",
                    waive,
                )
            if gap > 2.5 * max(wa, wb) + 1e-3:
                R.flag(
                    "rhythm",
                    at,
                    f"{FLOOR[f or 0]}: {gap:.2f} m of blank wall between openings; at most {2.5 * max(wa, wb):.2f} m",
                    waive,
                )

    # Rules 4 & 5: shape and order
    present = sorted(f for f in floors if f is not None and f < len(spec))
    for f in present:
        wd, zb, zt = spec[f][:3]
        if not any(h[4] in ("win", "fwin") and floor_of(h, spec) == f for h in H):
            continue
        r = (zt - zb) / wd
        lo, hi, kind = (
            (0.9, 1.6, "a low storey")
            if f in low
            else (1.2, 2.4, "the top storey")
            if f == len(spec) - 1 and len(spec) > 1
            else (1.4, 2.4, "a main storey")
        )
        if not lo - 1e-3 <= r <= hi + 1e-3:
            R.flag(
                "shape",
                at,
                f"{FLOOR[f]} windows are {wd:.2f} x {zt - zb:.2f} m (ratio {r:.2f}); {kind} wants {lo}-{hi}",
                waive,
            )
    if door and door[2] / door[1] < 1.25:
        R.flag(
            "shape",
            at,
            f"the door is {door[1]:.2f} x {door[2]:.2f} m; doors want at least 1.25 tall to 1 wide",
            waive,
        )
    seq = [(f, spec[f][2] - spec[f][1]) for f in present if f >= 1 and f not in low]
    for (fa, ha), (fb, hb) in zip(seq, seq[1:]):
        if hb > ha + 0.1:
            R.flag("order", at, f"{FLOOR[fb]} windows ({hb:.2f} m) are taller than the {FLOOR[fa]} ({ha:.2f} m)", waive)

    # Rule 6: balance
    if w.n.y < -0.9 and (door or any(h[4] == "shop" for h in H)):
        if any(h[4] == "shop" for h in H):
            R.flag("balance", at, "a shopfront makes the street front asymmetrical", waive)
        elif len(us) % 2 == 0 or abs(w.u_of(door[0]) - us[len(us) // 2]) > 1e-3:
            R.flag("balance", at, f"the entrance is not in the centre of an odd number of bays ({len(us)} bays)", waive)

    # Rule 7: glass
    area = w.L * (st["top"] - z0)
    if area >= 20:
        ratio = sum((h[1] - h[0]) * (h[3] - h[2]) for h in H) / area
        if not 0.10 <= ratio <= 0.45:
            R.flag("glass", at, f"openings are {100 * ratio:.0f}% of the wall; keep them to 10-45%", waive)

    # Rule 8: clearance
    for name, a, b, cuts in bands:
        for bx in boxes:
            h = bx[4]
            if a < bx[3] - 1e-6 and b > bx[2] + 1e-6 and not any(c0 <= h[0] and h[1] <= c1 for c0, c1 in cuts):
                f = floor_of(h, spec)
                kind_lbl = "door" if h[4] == "door" else "shopfront" if h[4] == "shop" else "window"
                R.flag(
                    "clearance",
                    at,
                    f"the {name} ({a:.2f}-{b:.2f} m) runs into the {FLOOR[f or 0]} {kind_lbl} surrounds ({bx[2]:.2f}-{bx[3]:.2f} m)",
                    waive,
                )
    for i, a in enumerate(boxes):
        for b in boxes[i + 1 :]:
            if overlap(a, b):
                R.flag(
                    "clearance",
                    at,
                    f"two surrounds meet (at {a[2]:.2f}-{a[3]:.2f} m and {b[2]:.2f}-{b[3]:.2f} m high)",
                    waive,
                )


def check_cornice(m, w, top, proud, waive=None):
    street = w.n.y < -0.9
    lo, hi = (top / 40, top / 20) if street else (top / 80, top / 15)
    if not lo - 1e-3 <= proud <= hi + 1e-3:
        rules_of(m).flag(
            "cornice",
            where(w),
            f"the cornice projects {proud:.2f} m on a {top:.1f} m wall; "
            f"{'a street front' if street else 'this wall'} wants {lo:.2f}-{hi:.2f} m",
            waive,
        )


def record_for(m, w):
    """Return registered walls collinear with w and facing the same direction."""
    out = []
    for r in rules_of(m).walls:
        v = r["w"]
        if (v.n - w.n).length < 1e-3 and abs(v.n.dot(v.A - w.A)) < 0.05:
            out.append(r)
    return out


def check_balcony(m, w, parts, waive=None):
    R = rules_of(m)
    for r in [r for r in R.walls if r["w"] is w]:
        for p in parts:
            for bx in r["boxes"]:
                if overlap(p, bx):
                    R.flag(
                        "clearance",
                        where(w),
                        f"the balcony ({p[2]:.2f}-{p[3]:.2f} m) runs into window surrounds below ({bx[2]:.2f}-{bx[3]:.2f} m)",
                        waive,
                    )


def check_lucarne(m, w, c, win, waive=None):
    R = rules_of(m)
    at = f"lucarne at {c:.2f} on the {where(w)}"
    u = w.u_of(c)
    recs = record_for(m, w)
    p = w.P(u, 0)
    on_axis = False
    top_w = None
    for r in recs:
        v = r["w"]
        uu = v.u_of(p[0] if abs(v.t.x) > 0.5 else p[1])
        if -0.05 <= uu <= v.L + 0.05:
            top_w = r["top_w"]
            if any(abs(uu - b) < 0.05 for b in r["bays"]) or abs(uu - v.L / 2) < 0.05:
                on_axis = True
    if not on_axis and abs(u - w.L / 2) > 0.05:
        R.flag("dormers", at, "it stands on neither a window axis below nor the centre of the wall", waive)
    wd, zb, zt = win
    if top_w is not None and wd >= top_w:
        R.flag("dormers", at, f"its window ({wd:.2f} m) is not narrower than the top-floor windows ({top_w:.2f} m)", waive)
    if not 1.0 - 1e-3 <= (zt - zb) / wd <= 2.0 + 1e-3:
        R.flag("shape", at, f"its window is {wd:.2f} x {zt - zb:.2f} m; lucarne windows want 1.0-2.0 tall to 1 wide", waive)


def check_closed_solid(m, t, what):
    """Rule 15: verify every edge of sub-mesh `t` is shared by exactly two faces (closed solid)."""
    c = Counter()
    for f in t.f:
        pts = [tuple(round(x, 4) for x in t.v[i]) for i in f]
        for a, b in zip(pts, pts[1:] + pts[:1]):
            if a != b:
                c[frozenset((a, b))] += 1
    bad = [tuple(e) for e, k in c.items() if k != 2]
    if bad:
        e = bad[0]
        rules_of(m).bad.append(
            f"Rule 15 (closed construction), {what}: {len(bad)} open edge(s), e.g. "
            + " - ".join("(%.2f, %.2f, %.2f)" % p for p in e)
        )


def verdict(m):
    R = rules_of(m)
    waived = list(R.waived)
    bad = list(R.bad)
    R.bad, R.waived, R.walls = [], [], []
    if bad:
        raise RuleError(" || ".join(bad))
    return waived
