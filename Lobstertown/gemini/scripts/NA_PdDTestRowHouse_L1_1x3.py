"""TEST building for the Gemini runner (written by Claude to the template, not a real design).
Three-storey Philadelphia brick row house, 1 x 3 lot, front at the street, slate gable roof."""
import bpy
import bmesh

ZONE = "Z1A"
HOUSEHOLDS = 1
PARTY_WALLS = ("left", "right")

L, R = -3.74, 3.74          # party walls, 0.26 m in from the side lot lines
FRONT, BACK = -11.70, 0.0   # front wall 0.30 m inside the lot front (y = -12); rear wall halfway back
FLOORS = [0.0, 3.6, 6.6, 9.6]
EAVE, RIDGE = 9.6, 12.4

class Mesh:
    def __init__(self):
        self.v, self.f, self.m, self.mats = [], [], [], []
    def quad(self, pts, mat):
        if mat not in self.mats: self.mats.append(mat)
        i = len(self.v); self.v += pts; self.f.append(list(range(i, i + len(pts)))); self.m.append(self.mats.index(mat))
    def box(self, x0, x1, y0, y1, z0, z1, mat, skip=()):
        P = lambda x, y, z: (x, y, z)
        sides = {"bottom": [P(x0,y0,z0),P(x0,y1,z0),P(x1,y1,z0),P(x1,y0,z0)], "top": [P(x0,y0,z1),P(x1,y0,z1),P(x1,y1,z1),P(x0,y1,z1)],
                 "front": [P(x0,y0,z0),P(x1,y0,z0),P(x1,y0,z1),P(x0,y0,z1)], "back": [P(x1,y1,z0),P(x0,y1,z0),P(x0,y1,z1),P(x1,y1,z1)],
                 "left": [P(x0,y1,z0),P(x0,y0,z0),P(x0,y0,z1),P(x0,y1,z1)], "right": [P(x1,y0,z0),P(x1,y1,z0),P(x1,y1,z1),P(x1,y0,z1)]}
        for k, pts in sides.items():
            if k not in skip: self.quad(pts, mat)
    def make(self, name):
        me = bpy.data.meshes.new(name); me.from_pydata(self.v, [], self.f); me.update()
        for k, i in enumerate(self.m): me.polygons[k].material_index = i
        for mat in self.mats: me.materials.append(bpy.data.materials.get(mat) or bpy.data.materials.new(mat))
        bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5); bm.to_mesh(me); bm.free()
        ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
        return ob

def facade(b, g, y, out, bays, lod, door=None):
    """Wall plane at y facing out (-1 front, +1 rear), x from L to R, with window openings per floor."""
    def P(x, z, d=0.0): return (x, y + out * d, z)
    def wq(x0, x1, z0, z1, d=0.0, mat="Brick085"):
        if x1 - x0 > 1e-4 and z1 - z0 > 1e-4:
            pts = [P(x0, z0, d), P(x1, z0, d), P(x1, z1, d), P(x0, z1, d)]
            b.quad(pts if out < 0 else pts[::-1], mat)
    span = (R - L) / bays
    for k in range(3):
        z0, z1 = FLOORS[k], FLOORS[k + 1]
        lo, hi = z0 + (0.9 if k else 0.7), z1 - 0.6
        holes = []
        for j in range(bays):
            c = L + span * (j + .5)
            w = 1.0
            if k == 0 and door is not None and j == door: holes.append((c - .55, c + .55, 0.0, 2.7, True))
            else: holes.append((c - w / 2, c + w / 2, lo, hi, False))
        x = L
        for (a, c, bot, top, is_door) in holes:
            wq(x, a, z0, z1); wq(a, c, z0, bot); wq(a, c, top, z1); x = c
        wq(x, R, z0, z1)
        for (a, c, bot, top, is_door) in holes:
            dep = 0.18 if lod == 0 else 0.06
            # reveals (inward), then glass or door at the back of the reveal
            if lod < 2:
                for pts in ([P(a, bot, 0), P(a, top, 0), P(a, top, -dep), P(a, bot, -dep)], [P(c, top, 0), P(c, bot, 0), P(c, bot, -dep), P(c, top, -dep)],
                            [P(a, top, 0), P(c, top, 0), P(c, top, -dep), P(a, top, -dep)], [P(c, bot, 0), P(a, bot, 0), P(a, bot, -dep), P(c, bot, -dep)]):
                    b.quad(pts if out < 0 else pts[::-1], "Dressed")
            pane = [P(a, bot, -dep), P(c, bot, -dep), P(c, top, -dep), P(a, top, -dep)]
            if is_door: b.quad(pane if out < 0 else pane[::-1], "Black")
            else: g.quad(pane if out < 0 else pane[::-1], "Glass")
            if lod == 0 and not is_door:
                # sash frame and glazing bars, 5 mm in front of the glass
                yi0, yi1 = (y + dep - .05, y + dep - .005) if out < 0 else (y - dep + .005, y - dep + .05)
                a, c, bot, top = a + .003, c - .003, bot + .003, top - .003   # frame stands 3 mm clear of the reveal
                bars = [(a, a + .07, bot, top), (c - .07, c, bot, top), (a + .07, c - .07, bot, bot + .07), (a + .07, c - .07, top - .07, top),
                        (a + .07, c - .07, (bot + top) / 2 - .03, (bot + top) / 2 + .03), ((a + c) / 2 - .02, (a + c) / 2 + .02, bot + .07, top - .07)]
                for k, (x0, x1, zb, zt) in enumerate(bars):
                    lo_y, hi_y = min(yi0, yi1), max(yi0, yi1)
                    if k == 5: lo_y, hi_y = (lo_y + .004, hi_y) if out < 0 else (lo_y, hi_y - .004)   # the upright bar sits 4 mm back
                    if k in (2, 3, 4): x0, x1 = x0 + .002, x1 - .002                                  # rails stop 2 mm short of the stiles
                    b.box(x0, x1, lo_y, hi_y, zb, zt, "Cream", skip=("back" if out < 0 else "front",))
                # stone sill and lintel, standing 4 mm proud of the wall so nothing is coplanar
                for zb, zt in ((bot - .12, bot), (top, top + .22)):
                    y0, y1 = (y - .10, y - .004) if out < 0 else (y + .004, y + .10)
                    b.box(a - .12, c + .12, y0, y1, zb, zt, "Dressed", skip=("back" if out < 0 else "front",))
    if lod == 0:
        for z in FLOORS[1:3]:   # string courses between floors
            y0, y1 = (y - .06, y - .004) if out < 0 else (y + .004, y + .06)
            b.box(L + .01, R - .01, y0, y1, z - .08, z + .02, "Dressed", skip=("back" if out < 0 else "front", "left", "right"))

def build(lod):
    b, g = Mesh(), Mesh()
    facade(b, g, FRONT, -1, 3, lod, door=0)
    facade(b, g, BACK, 1, 2, lod)
    for x, s in ((L, -1), (R, 1)):   # party walls, plain brick
        pts = [(x, FRONT, 0), (x, BACK, 0), (x, BACK, EAVE), (x, FRONT, EAVE)]
        b.quad(pts if s < 0 else pts[::-1], "Brick085")
        tri = [(x, FRONT, EAVE), (x, BACK, EAVE), (x, (FRONT + BACK) / 2, RIDGE)]
        b.quad(tri if s < 0 else tri[::-1], "Brick085")
    # plinth band along the front
    if lod < 2: b.box(L + .01, R - .01, FRONT - .05, FRONT - .004, 0, .6, "StoneBase", skip=("back", "left", "right", "bottom"))
    # cornice
    if lod < 2: b.box(L + .01, R - .01, FRONT - .28, FRONT - .004, EAVE - .45, EAVE, "Cream", skip=("back", "left", "right"))
    if lod == 0:
        # dentils under the cornice and stone quoins at the front corners
        n = 28
        for k in range(n):
            x0 = L + .1 + k * (R - L - .2) / n
            b.box(x0, x0 + .12, FRONT - .24, FRONT - .17, EAVE - .62, EAVE - .46, "Cream", skip=("back",))
        for k in range(14):
            z0 = .6 + k * .64; wdt = .55 if k % 2 else .35
            for x0, x1 in ((L + .01, L + .01 + wdt), (R - .01 - wdt, R - .01)):
                b.box(x0, x1, FRONT - .03, FRONT - .004, z0, z0 + .56, "Dressed", skip=("back",))
    # roof: gable, ridge parallel to the street
    mid = (FRONT + BACK) / 2
    b.quad([(L, FRONT - .2, EAVE + .01), (R, FRONT - .2, EAVE + .01), (R, mid, RIDGE), (L, mid, RIDGE)], "SlateDark")
    b.quad([(R, BACK + .2, EAVE + .01), (L, BACK + .2, EAVE + .01), (L, mid, RIDGE), (R, mid, RIDGE)], "SlateDark")
    if lod < 2: b.box(R - 1.2, R - .3, mid - .5, mid + .5, RIDGE - .6, RIDGE + 1.0, "Chimney", skip=("bottom",))
    for name, m in (("Body", b), ("Windows", g)):
        old = bpy.data.objects.get(name)
        if old: bpy.data.objects.remove(old, do_unlink=True)
        m.make(name)

if __name__ == "__main__":
    build(0)
