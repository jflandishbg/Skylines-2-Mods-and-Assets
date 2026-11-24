"""Rounded architectural sculpture, using the landmark mesh and palette."""
import math
from mathutils import Vector

def tube(m, points, radii, mat, sides=8):
    rings=[]
    for i,p in enumerate(points):
        p=Vector(p)
        direction=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])
        direction.normalize()
        ref=Vector((0,0,1)) if abs(direction.z)<.9 else Vector((0,1,0))
        u=direction.cross(ref).normalized()
        v=direction.cross(u).normalized()
        rings.append([tuple(p+radii[i]*(u*math.cos(2*math.pi*k/sides)+v*math.sin(2*math.pi*k/sides))) for k in range(sides)])
    for i in range(len(rings)-1):
        center=(Vector(points[i])+Vector(points[i+1]))*.5
        for k in range(sides):
            q=[rings[i][k],rings[i][(k+1)%sides],rings[i+1][(k+1)%sides],rings[i+1][k]]
            m.facing(q,tuple(sum((Vector(v) for v in q),Vector())/4-center),mat)
    m.facing(rings[0],tuple(Vector(points[0])-Vector(points[1])),mat)
    m.facing(rings[-1],tuple(Vector(points[-1])-Vector(points[-2])),mat)

def rounded_beam(m,p,q,w,mat):
    tube(m,[p,q],[w*.5,w*.36],mat,8)

def curved_strip(m,P,pts,w0,w1,d0,d1,mat,step=.004):
    # One continuous elliptical relief surface; depth remains inside the original envelope.
    path=[]
    for i in range(len(pts)-1):
        a=Vector(pts[max(0,i-1)]);b=Vector(pts[i]);c=Vector(pts[i+1]);d=Vector(pts[min(len(pts)-1,i+2)])
        for j in range(3):
            t=j/3
            v=.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)
            path.append(v)
    path.append(Vector(pts[-1]))
    rings=[]
    depth=(d1-d0)*.5
    for i,p in enumerate(path):
        tangent=path[min(i+1,len(path)-1)]-path[max(0,i-1)]
        tangent.normalize();normal=Vector((-tangent.y,tangent.x))
        width=(w0+(w1-w0)*i/(len(path)-1))*.5
        rings.append([P(*(p+normal*width*math.cos(2*math.pi*k/6)),(d0+d1)*.5+step*i/3+depth*math.sin(2*math.pi*k/6)) for k in range(6)])
    for i in range(len(rings)-1):
        center=Vector(P(*((path[i]+path[i+1])*.5),(d0+d1)*.5))
        for k in range(6):
            q=[rings[i][k],rings[i][(k+1)%6],rings[i+1][(k+1)%6],rings[i+1][k]]
            m.facing(q,tuple(sum((Vector(v) for v in q),Vector())/4-center),mat)

def cod_body(m,cx,cy,z0,s,lod,mat):
    # Continuous fusiform body, three dorsal fins, broad caudal fin and a chin barbel.
    from lt_designs.landmarks import prism,plane,blob,IRON
    sections=[(-.40,.045,.016,.023),(-.32,.075,.038,.055),(-.22,.12,.067,.09),
              (-.10,.155,.09,.125),(.04,.16,.105,.14),(.17,.14,.09,.13),
              (.28,.11,.074,.10),(.36,.085,.055,.072),(.42,.073,.022,.033)]
    if lod==0:
        rounded=[]
        for i in range(len(sections)-1):
            a=Vector(sections[max(0,i-1)]);b=Vector(sections[i])
            c=Vector(sections[i+1]);d=Vector(sections[min(len(sections)-1,i+2)])
            for t in [0,1/3,2/3]:
                rounded.append(tuple(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)))
        sections=rounded+[sections[-1]]
    sides=24 if lod==0 else 10 if lod==1 else 6
    rings=[[(cx+x*s,cy+ry*s*math.cos(2*math.pi*k/sides),z0+(z+rz*math.sin(2*math.pi*k/sides))*s) for k in range(sides)] for x,z,ry,rz in sections]
    for i in range(len(rings)-1):
        center=Vector((cx+(sections[i][0]+sections[i+1][0])*s/2,cy,z0+(sections[i][1]+sections[i+1][1])*s/2))
        for k in range(sides):
            q=[rings[i][k],rings[i][(k+1)%sides],rings[i+1][(k+1)%sides],rings[i+1][k]]
            m.facing(q,tuple(sum((Vector(v) for v in q),Vector())/4-center),mat)
    m.facing(rings[0],(-1,0,0),mat);m.facing(rings[-1],(1,0,0),mat)
    P=plane(cx,cy,1,0)
    def fin(points):
        prism(m,[(x*s,z0+z*s) for x,z in points],P,-.008*s,.008*s,mat,back=True)
    fin([(-.39,.065),(-.52,.155),(-.54,-.045),(-.39,.025)])
    for a,c,z in [(-.29,-.17,.20),(-.15,.01,.30),(.03,.18,.34)]:
        fin([(a,z-.075),((a+c)/2,z),(c,z-.065)])
    if lod<2:
        for side in [-1,1]:
            blob(m,(cx+.32*s,cy+side*.061*s,z0+.13*s),(.010*s,.009*s,.010*s),IRON,8,4)
            tube(m,[(cx+.19*s,cy+side*.08*s,z0+.07*s),(cx+.10*s,cy+side*.16*s,z0+.005*s)],[.025*s,.004*s],mat,6)
        tube(m,[(cx+.35*s,cy,z0+.025*s),(cx+.32*s,cy,z0-.035*s)],[.007*s,.002*s],mat,6)

def loft_elliptical(m, spine, r_u, r_v, mat, sides=14, up_hint=(0, 0, 1), cap_ends=True):
    """Smooth elliptical-section loft along a 3D spine: r_u = width half-axis (horizontal/lateral),
    r_v = thickness half-axis (vertical/normal). Ideal for flat sea-turtle flippers, necks, and pinniped bodies."""
    n = len(spine)
    rings = []
    hint = Vector(up_hint)
    for i, pt in enumerate(spine):
        p = Vector(pt)
        d = Vector(spine[min(i + 1, n - 1)]) - Vector(spine[max(0, i - 1)])
        if d.length < 1e-6:
            d = Vector((0, 1, 0))
        d.normalize()
        # Keep lateral axis U consistently oriented near horizontal when possible
        ref = hint if abs(d.dot(hint)) < 0.92 else Vector((1, 0, 0))
        u = d.cross(ref)
        if u.length < 1e-6:
            u = Vector((1, 0, 0))
        u.normalize()
        v = u.cross(d).normalized()
        ru, rv = r_u[i], r_v[i]
        ring = [tuple(p + u * (ru * math.cos(2 * math.pi * k / sides))
                        + v * (rv * math.sin(2 * math.pi * k / sides))) for k in range(sides)]
        rings.append(ring)
    for i in range(n - 1):
        center = (Vector(spine[i]) + Vector(spine[i + 1])) * 0.5
        for k in range(sides):
            nxt = (k + 1) % sides
            q = [rings[i][k], rings[i][nxt], rings[i + 1][nxt], rings[i + 1][k]]
            m.facing(q, tuple(sum((Vector(v_) for v_ in q), Vector()) / 4 - center), mat)
    if cap_ends:
        d0 = Vector(spine[0]) - Vector(spine[1])
        d1 = Vector(spine[-1]) - Vector(spine[-2])
        m.facing(rings[0], tuple(d0), mat)
        m.facing(rings[-1], tuple(d1), mat)


def _turtle_surface_z(x, y, rx, ry, h_max):
    """Heart-oval sea turtle carapace height at local (x, y) relative to shell center."""
    yn = y / ry
    # Wider at front shoulders (yn < 0), gently tapering toward the tail (yn > 0)
    w_fac = 1.0 + 0.08 * math.sin(-yn * math.pi * 0.5) - 0.14 * max(0.0, yn) ** 1.6
    xn = x / (rx * max(0.55, w_fac))
    r2 = xn * xn + yn * yn
    if r2 >= 1.0:
        return 0.0
    r = math.sqrt(r2)
    # Sleek sea-turtle dome with subtle flared marginal skirt near r = 0.85..1.0
    if r < 0.86:
        base = math.sqrt(max(0.0, 1.0 - (r / 0.94) ** 2))
    else:
        t = (r - 0.86) / 0.14
        z86 = math.sqrt(max(0.0, 1.0 - (0.86 / 0.94) ** 2))
        base = z86 * (1.0 - t) ** 1.15
    # Gentle front-weighted crown arch
    arch = 1.0 + 0.08 * math.cos(min(math.pi, max(-math.pi, (yn + 0.15) * 2.1)))
    return h_max * base * arch


def turtle_shell(m, cy, rx, ry, top, lod):
    """Oval, heart-tapered coastal sea-turtle carapace: dark slate recessed seam dome,
    13 raised verdigris-copper hexagonal Voronoi scutes reaching right down to r=0.90, and
    a sleek flared verdigris-copper marginal border rim with pale-stone bevel edge."""
    seam_mat = "SlateDark"
    scute_mat = "TinGreen"
    rim_mat = "TinGreen"
    h_max = 5.4
    sectors = 40 if lod == 0 else 20 if lod == 1 else 14
    levels = 9 if lod == 0 else 5 if lod == 1 else 4

    def shell_xy(r_frac, ang):
        yn = r_frac * math.sin(ang)
        w_fac = 1.0 + 0.08 * math.sin(-yn * math.pi * 0.5) - 0.14 * max(0.0, yn) ** 1.6
        return rx * w_fac * r_frac * math.cos(ang), ry * yn

    def point(x, y, raise_by=0.0):
        return (x, cy + y, top + _turtle_surface_z(x, y, rx, ry, h_max) + raise_by)

    # 1. Dark recessed under-shell dome (forms crisp dark seams between scutes!)
    rings = []
    for j in range(levels + 1):
        r_frac = math.cos(math.pi * j / (2 * levels))
        ring = []
        for k in range(sectors):
            ang = 2 * math.pi * k / sectors
            x, y = shell_xy(r_frac, ang)
            z = top + _turtle_surface_z(x, y, rx, ry, h_max * (0.94 if lod < 2 else 1.0))
            ring.append((x, cy + y, z))
        rings.append(ring)
    for j in range(levels):
        for k in range(sectors):
            nxt = (k + 1) % sectors
            q = [rings[j][k], rings[j][nxt], rings[j + 1][nxt], rings[j + 1][k]]
            if j == levels - 1:
                q = q[:3]
            c = sum((Vector(v) for v in q), Vector()) / len(q)
            m.facing(q, (c.x, c.y - cy, max(0.15, c.z - top)), scute_mat if lod == 2 else seam_mat)

    if lod == 2:
        return

    # 2. Flared marginal border scutes (18 verdigris-copper rim plates separated by crisp dark seams + pale edge lip!)
    n_marg = 18
    for k in range(n_marg):
        a0 = 2 * math.pi * (k + 0.06) / n_marg
        a1 = 2 * math.pi * (k + 0.94) / n_marg
        p00 = point(*shell_xy(0.89, a0), 0.18)
        p01 = point(*shell_xy(0.89, a1), 0.18)
        p10 = point(*shell_xy(1.02, a0), 0.22)
        p11 = point(*shell_xy(1.02, a1), 0.22)
        b10 = (p10[0], p10[1], top + 0.02)
        b11 = (p11[0], p11[1], top + 0.02)
        c = (Vector(p00) + Vector(p01) + Vector(p10) + Vector(p11)) * 0.25
        m.facing([p00, p01, p11, p10], (c.x, c.y - cy, max(0.3, c.z - top)), rim_mat)
        m.facing([p10, p11, b11, b10], (c.x, c.y - cy, 0.0), "RevealStone")

    # 3. 13 Raised cambered Voronoi scutes (5 vertebral spine + 4 costal each side) reaching down to r = 0.89!
    centers = [(0.0, y) for y in (-0.60, -0.30, 0.0, 0.30, 0.60)]
    centers += [(sgn * 0.46, y) for sgn in (-1, 1) for y in (-0.46, -0.15, 0.15, 0.46)]
    boundary = [(0.89 * math.cos(2 * math.pi * k / 36), 0.89 * math.sin(2 * math.pi * k / 36)) for k in range(36)]

    def clip(poly, nx, ny, d):
        res = []
        for a, b in zip(poly, poly[1:] + poly[:1]):
            da = a[0] * nx + a[1] * ny - d
            db = b[0] * nx + b[1] * ny - d
            if da <= 0:
                res.append(a)
            if (da <= 0) != (db <= 0):
                t = da / (da - db)
                res.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        return res

    def uv_to_xy(u, v):
        w_fac = 1.0 + 0.08 * math.sin(-v * math.pi * 0.5) - 0.14 * max(0.0, v) ** 1.6
        return rx * w_fac * u, ry * v

    for cu, cv in centers:
        poly = boundary[:]
        for ou, ov in centers:
            if (ou, ov) == (cu, cv):
                continue
            poly = clip(poly, ou - cu, ov - cv, (ou * ou + ov * ov - cu * cu - cv * cv) / 2)
        if len(poly) < 3:
            continue
        outline = []
        subdiv = 2 if lod == 0 else 1
        for a, b in zip(poly, poly[1:] + poly[:1]):
            for k in range(subdiv):
                t = k / subdiv
                u = a[0] * (1 - t) + b[0] * t
                v = a[1] * (1 - t) + b[1] * t
                outline.append((cu + (u - cu) * 0.945, cv + (v - cv) * 0.945))
        scales = (0.45, 0.82, 1.0) if lod == 0 else (0.65, 1.0)
        heights = (0.40, 0.32, 0.08) if lod == 0 else (0.34, 0.08)
        cx_, cy_ = uv_to_xy(cu, cv)
        prev = None
        for sc, hh in zip(scales, heights):
            ring = [point(*uv_to_xy(cu + (u - cu) * sc, cv + (v - cv) * sc), hh) for u, v in outline]
            for k in range(len(ring)):
                nxt = (k + 1) % len(ring)
                q = [point(cx_, cy_, 0.44), ring[k], ring[nxt]] if prev is None else [prev[k], ring[k], ring[nxt], prev[nxt]]
                c = sum((Vector(p_) for p_ in q), Vector()) / len(q)
                m.facing(q, (c.x, c.y - cy, max(0.2, c.z - top)), scute_mat)
            prev = ring


def turtle_anatomy(m, cy, yF, end, XH, top, rx, ry, lod):
    """Proud forward-reaching sea-turtle neck & bold reptilian head, sweeping broad flat wing flippers at shell-rim
    level (zero side slits, single clean eave height!), and tapered rear tail."""
    from lt_designs.landmarks import blob, COPPER, CREAM, IRON
    # 1. Proud extended muscular neck + bold reptilian sea-turtle skull & hooked beak (strictly inside y >= -15.70!)
    head_spine = [
        (0.0, yF + 2.9, top + 0.85),
        (0.0, yF + 1.3, top + 1.45),
        (0.0, yF + 0.15, top + 2.05),
        (0.0, yF - 0.75, top + 2.35),
        (0.0, yF - 1.32, top + 2.15),
        (0.0, yF - 1.62, top + 1.70),
    ]
    head_ru = [1.85, 1.50, 1.65, 2.05, 1.45, 0.42]
    head_rv = [1.25, 1.05, 1.20, 1.52, 1.05, 0.28]
    loft_elliptical(m, head_spine, head_ru, head_rv, COPPER, sides=14 if lod == 0 else 8 if lod == 1 else 6)
    if lod < 2:
        # Pale cream lower jaw / throat plate curving underneath neck & chin
        jaw_spine = [
            (0.0, yF + 2.2, top + 0.55),
            (0.0, yF + 0.7, top + 1.05),
            (0.0, yF - 0.50, top + 1.45),
            (0.0, yF - 1.35, top + 1.40),
        ]
        loft_elliptical(m, jaw_spine, [1.30, 1.15, 1.38, 0.52], [0.46, 0.42, 0.44, 0.20], CREAM, sides=10 if lod == 0 else 6)
        # Side-set dignified reptilian eyes under sculpted copper brow ridges
        for sgn in (-1, 1):
            blob(m, (sgn * 1.62, yF - 0.88, top + 2.55), (0.36, 0.52, 0.30), COPPER, 8, 4)
            blob(m, (sgn * 1.74, yF - 0.95, top + 2.38), (0.28, 0.34, 0.30), IRON, 8, 4)
            if lod == 0:
                blob(m, (sgn * 1.90, yF - 1.01, top + 2.42), (0.09, 0.10, 0.10), CREAM, 6, 3)

    # 2. Broad, flat, sweeping FRONT sea-turtle pectoral wing flippers at shell-rim level!
    # Inner trailing edge overlaps the pavilion wall cleanly (zero narrow XY gap!), while outer leading edge
    # flares dramatically to +-15.65 m (31.3 m wingspan!) and stays near top = 6.8 m (clean single eave level!).
    for sgn in (-1, 1):
        f_spine = [
            (sgn * 9.8, cy - 7.8, top + 0.72),
            (sgn * 12.4, cy - 8.2, top + 0.48),
            (sgn * 13.85, cy - 5.6, top + 0.22),
            (sgn * 13.75, cy - 2.0, top + 0.04),
            (sgn * 13.35, cy + 1.4, top - 0.06),
            (sgn * 12.85, cy + 3.6, top - 0.10),
        ]
        f_ru = [1.65, 2.05, 1.75, 1.45, 1.00, 0.28]
        f_rv = [0.55, 0.44, 0.34, 0.26, 0.18, 0.10]
        loft_elliptical(m, f_spine, f_ru, f_rv, COPPER, sides=12 if lod == 0 else 8 if lod == 1 else 6)
        if lod == 0:
            edge_pts = [
                (sgn * 12.4, cy - 9.2, top + 0.42),
                (sgn * 15.1, cy - 6.3, top + 0.20),
                (sgn * 15.1, cy - 2.2, top + 0.02),
                (sgn * 14.3, cy + 1.2, top - 0.06),
            ]
            tube(m, edge_pts, [0.22, 0.20, 0.16, 0.08], "RevealStone", 6)

        # 3. Broad, flat webbed REAR sea-turtle flippers fanning cleanly over the rear corners (zero gap!)
        r_spine = [
            (sgn * 8.8, cy + 8.6, top + 0.65),
            (sgn * 11.8, cy + 10.6, top + 0.35),
            (sgn * 13.25, cy + 12.4, top + 0.10),
            (sgn * 13.35, cy + 14.2, top - 0.04),
            (sgn * 12.85, cy + 14.9, top - 0.10),
        ]
        loft_elliptical(m, r_spine, [1.25, 1.65, 1.45, 0.72, 0.22], [0.46, 0.34, 0.24, 0.16, 0.09],
                        COPPER, sides=10 if lod == 0 else 6)

    # 4. Tapered curved rear turtle tail emerging cleanly under rear shell rim (strictly inside y <= 15.70!)
    t_spine = [
        (0.0, cy + ry * 0.78, top + 0.65),
        (0.0, cy + ry * 0.92, top + 0.35),
        (0.0, end - 0.10, top + 0.05),
        (0.0, end + 0.65, top - 0.12),
    ]
    loft_elliptical(m, t_spine, [1.15, 0.82, 0.45, 0.12], [0.75, 0.52, 0.28, 0.10], COPPER, sides=10 if lod == 0 else 6)


def relief_blob(m, P, u, z, ru, rz, d0, d1, mat, lod):
    from lt_designs.landmarks import Mesh, blob
    local = Mesh()
    blob(local, (u, (d0 + d1) / 2, z), (ru, (d1 - d0) / 2, rz), mat, 20 if lod == 0 else 10, 8 if lod == 0 else 4)
    center = Vector(P(u, z, (d0 + d1) / 2))
    for face in local.f:
        pts = [P(local.v[i][0], local.v[i][2], local.v[i][1]) for i in face]
        normal = sum((Vector(p) for p in pts), Vector()) / len(pts) - center
        m.facing(pts, normal, mat)


def nautilus(m, P, u, z, s, mat, lod):
    from lt_designs.landmarks import COPPER, CREAM
    if lod == 2:
        relief_blob(m, P, u, z + .26 * s, .36 * s, .36 * s, .02, .18, COPPER, lod)
        return
    relief_blob(m, P, u, z + .26 * s, .36 * s, .36 * s, .02, .18, COPPER, lod)
    pts = []
    samples = 64 if lod == 0 else 32
    for i in range(samples):
        t = i / (samples - 1)
        a = math.pi * .35 + math.pi * 4.3 * t
        r = s * (.31 * (1 - t) + .015)
        pts.append(P(u + r * math.cos(a), z + .26 * s + r * math.sin(a), .185))
    tube(m, pts, [.020 if lod == 0 else .024] * samples, CREAM, 6)
    if lod == 0:
        for k in range(14):
            a = 2 * math.pi * k / 14
            pts = [P(u + s * r * math.cos(a), z + .26 * s + s * r * math.sin(a), .17) for r in (.27, .31, .35)]
            tube(m, pts, [.012, .014, .01], CREAM, 5)
    for side in (-1, 1):
        for k in range(2):
            pts = [(u + side * .18 * s, z + .02 * s), (u + side * (.26 + .10 * k) * s, z - .12 * s),
                   (u + side * (.35 + .10 * k) * s, z - .35 * s), (u + side * (.30 + .10 * k) * s, z - .45 * s)]
            curved_strip(m, P, pts, .065 * s, .010 * s, .02, .16 - .025 * k, COPPER)


def nautilus_3d(m, cx, cy, z0, s, lod):
    """Monumental 3D logarithmic-spiral chambered nautilus shell coiled clockwise in the X-Z plane (facing street -Y)
    so the largest cream-and-copper chambered whorl arches proudly across the sky and the open aperture spills
    copper tentacles down onto the limestone pedestal."""
    from lt_designs.landmarks import COPPER, CREAM
    turns = 2.075
    steps = 56 if lod == 0 else 28 if lod == 1 else 14
    sides = 14 if lod == 0 else 8 if lod == 1 else 6
    a0 = 0.036 * s
    b = 0.175
    zc = z0 + 0.38 * s
    spine, r_u, r_v = [], [], []
    for i in range(steps + 1):
        u_ang = 2 * math.pi * turns * i / steps
        th = -u_ang
        rr = a0 * math.exp(b * u_ang)
        tr = 0.56 * rr
        spine.append((cx + rr * math.cos(th), cy, zc + rr * math.sin(th)))
        r_u.append(tr * 0.92)   # plump natural nautilus shell thickness along Y
        r_v.append(tr)          # tightly overlapping whorls with zero gap between turns!
    # Build shell rings with alternating CREAM body and COPPER chamber-septa bands
    rings = []
    for i, pt in enumerate(spine):
        p = Vector(pt)
        d = Vector(spine[min(i + 1, steps)]) - Vector(spine[max(0, i - 1)])
        d.normalize()
        u = Vector((0, 1, 0))                     # lateral = Y (out of the X-Z spiral plane)
        v = d.cross(u).normalized()
        ru, rv = r_u[i], r_v[i]
        ring = [tuple(p + u * (ru * math.cos(2 * math.pi * k / sides))
                        + v * (rv * math.sin(2 * math.pi * k / sides))) for k in range(sides)]
        rings.append(ring)
    for i in range(steps):
        center = (Vector(spine[i]) + Vector(spine[i + 1])) * 0.5
        mat_ = COPPER if (lod < 2 and i % 4 == 0 and i > steps // 5) else CREAM
        for k in range(sides):
            nxt = (k + 1) % sides
            q = [rings[i][k], rings[i][nxt], rings[i + 1][nxt], rings[i + 1][k]]
            m.facing(q, tuple(sum((Vector(v_) for v_ in q), Vector()) / 4 - center), mat_)
    m.facing(rings[-1], tuple(Vector(spine[-1]) - Vector(spine[-2])), COPPER)
    # Sweeping copper tentacles emerging from the wide 4-o'clock outer aperture onto the pedestal
    if lod < 2:
        mouth = Vector(spine[-1])
        for dx, dy, dz in (
            (0.09, -0.14, -0.15),
            (0.16, -0.09, -0.17),
            (0.02, -0.17, -0.19),
            (0.13, 0.11, -0.16),
            (-0.05, -0.12, -0.19),
        ):
            pts = [
                tuple(mouth + Vector((0.0, dy * 0.22 * s, -0.02 * s))),
                tuple(mouth + Vector((dx * 0.70 * s, dy * 0.75 * s, dz * 0.55 * s))),
                tuple(mouth + Vector((dx * 1.25 * s, dy * 1.10 * s, dz * 0.95 * s))),
                tuple(mouth + Vector((dx * 1.05 * s, dy * 0.92 * s, dz * 1.18 * s))),
            ]
            tube(m, pts, [0.044 * s, 0.032 * s, 0.019 * s, 0.006 * s], COPPER, 6)


def walrus(m, cx, cy, z0, s, lod):
    """Monumental reclining copper Walrus with a smooth lofted curved pinniped body, broad whiskered muzzle,
    sweeping ivory tusks, splayed front paddle flippers, and fanned rear tail flippers."""
    from lt_designs.landmarks import blob, COPPER, CREAM, IRON
    # 1. Continuous lofted curved pinniped body (proud raised chest -> hunched back -> curved tapering tail)
    if lod == 2:
        body_spine = [
            (cx, cy - 0.22 * s, z0 + 0.30 * s),
            (cx, cy - 0.12 * s, z0 + 0.19 * s),
            (cx + 0.03 * s, cy + 0.11 * s, z0 + 0.14 * s),
            (cx + 0.10 * s, cy + 0.35 * s, z0 + 0.08 * s),
            (cx + 0.14 * s, cy + 0.43 * s, z0 + 0.06 * s),
        ]
        body_ru = [0.14 * s, 0.22 * s, 0.20 * s, 0.095 * s, 0.045 * s]
        body_rv = [0.13 * s, 0.19 * s, 0.15 * s, 0.070 * s, 0.035 * s]
        loft_elliptical(m, body_spine, body_ru, body_rv, COPPER, sides=5)
        head_spine = [
            (cx, cy - 0.18 * s, z0 + 0.28 * s),
            (cx, cy - 0.27 * s, z0 + 0.36 * s),
            (cx, cy - 0.35 * s, z0 + 0.31 * s),
        ]
        loft_elliptical(m, head_spine, [0.13 * s, 0.12 * s, 0.085 * s],
                        [0.12 * s, 0.115 * s, 0.075 * s], COPPER, sides=5)
        for side in (-1, 1):
            tusk_pts = [
                (cx + side * 0.062 * s, cy - 0.345 * s, z0 + 0.275 * s),
                (cx + side * 0.078 * s, cy - 0.370 * s, z0 + 0.140 * s),
                (cx + side * 0.088 * s, cy - 0.315 * s, z0 - 0.005 * s),
            ]
            tube(m, tusk_pts, [0.028 * s, 0.018 * s, 0.004 * s], CREAM, 4)
        return

    body_spine = [
        (cx, cy - 0.22 * s, z0 + 0.30 * s),       # upper chest / neck base
        (cx, cy - 0.14 * s, z0 + 0.20 * s),       # heavy barrel chest
        (cx + 0.01 * s, cy - 0.02 * s, z0 + 0.16 * s),
        (cx + 0.03 * s, cy + 0.11 * s, z0 + 0.14 * s),
        (cx + 0.06 * s, cy + 0.24 * s, z0 + 0.11 * s),
        (cx + 0.10 * s, cy + 0.35 * s, z0 + 0.08 * s),
        (cx + 0.14 * s, cy + 0.43 * s, z0 + 0.06 * s),
    ]
    body_ru = [0.14 * s, 0.22 * s, 0.23 * s, 0.20 * s, 0.15 * s, 0.095 * s, 0.045 * s]
    body_rv = [0.13 * s, 0.19 * s, 0.18 * s, 0.15 * s, 0.11 * s, 0.070 * s, 0.035 * s]
    loft_elliptical(m, body_spine, body_ru, body_rv, COPPER, sides=18 if lod == 0 else 10)

    # 2. Proud lifted head & sculpted muzzle facing the street (-Y)
    head_spine = [
        (cx, cy - 0.18 * s, z0 + 0.28 * s),
        (cx, cy - 0.24 * s, z0 + 0.37 * s),
        (cx, cy - 0.30 * s, z0 + 0.35 * s),
        (cx, cy - 0.35 * s, z0 + 0.31 * s),
    ]
    loft_elliptical(m, head_spine, [0.13 * s, 0.13 * s, 0.115 * s, 0.085 * s],
                    [0.12 * s, 0.125 * s, 0.105 * s, 0.075 * s], COPPER, sides=14 if lod == 0 else 8)

    # 3. Bold sweeping ivory/cream tusks
    for side in (-1, 1):
        tusk_pts = [
            (cx + side * 0.062 * s, cy - 0.345 * s, z0 + 0.275 * s),
            (cx + side * 0.074 * s, cy - 0.375 * s, z0 + 0.175 * s),
            (cx + side * 0.084 * s, cy - 0.355 * s, z0 + 0.070 * s),
            (cx + side * 0.088 * s, cy - 0.315 * s, z0 - 0.005 * s),
        ]
        tube(m, tusk_pts, [0.028 * s, 0.022 * s, 0.014 * s, 0.004 * s], CREAM, 10 if lod == 0 else 6)

    # 4. Broad splayed front paddle flippers + fanned rear hind flippers
    for side in (-1, 1):
        ff_spine = [
            (cx + side * 0.17 * s, cy - 0.12 * s, z0 + 0.11 * s),
            (cx + side * 0.28 * s, cy - 0.16 * s, z0 + 0.04 * s),
            (cx + side * 0.36 * s, cy - 0.23 * s, z0 + 0.01 * s),
        ]
        loft_elliptical(m, ff_spine, [0.09 * s, 0.11 * s, 0.04 * s], [0.04 * s, 0.028 * s, 0.014 * s],
                        COPPER, sides=10 if lod == 0 else 6)
        # Plump whisker pads & dark eyes
        blob(m, (cx + side * 0.055 * s, cy - 0.355 * s, z0 + 0.295 * s), (0.062 * s, 0.042 * s, 0.048 * s), COPPER, 10, 5)
        blob(m, (cx + side * 0.088 * s, cy - 0.315 * s, z0 + 0.375 * s), (0.016 * s, 0.014 * s, 0.016 * s), IRON, 8, 4)
        if lod == 0:
            for k in range(4):
                wpts = [
                    (cx + side * 0.065 * s, cy - 0.388 * s, z0 + (0.315 - 0.015 * k) * s),
                    (cx + side * 0.165 * s, cy - 0.395 * s, z0 + (0.295 - 0.020 * k) * s),
                ]
                tube(m, wpts, [0.005 * s, 0.0015 * s], CREAM, 5)
    # Fanned rear tail flippers curled cleanly on the plinth
    for side, dy_f in ((-1, 0.03), (1, -0.02)):
        rf_spine = [
            (cx + 0.13 * s, cy + 0.41 * s, z0 + 0.055 * s),
            (cx + (0.16 + side * 0.07) * s, cy + (0.48 + dy_f) * s, z0 + 0.035 * s),
            (cx + (0.19 + side * 0.13) * s, cy + (0.53 + dy_f) * s, z0 + 0.020 * s),
        ]
        loft_elliptical(m, rf_spine, [0.05 * s, 0.075 * s, 0.025 * s], [0.025 * s, 0.018 * s, 0.010 * s],
                        COPPER, sides=8 if lod == 0 else 6)
