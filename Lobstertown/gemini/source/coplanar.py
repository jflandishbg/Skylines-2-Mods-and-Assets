"""Find overlapping same-facing coplanar body polygons, including atlas tiles.

Use a normal/offset index, a projected bounding-box sweep, then convex clipping
to measure the intersection. Shared edges alone have zero intersection area.
"""
from collections import defaultdict
from math import hypot
from mathutils import Vector
from mathutils.geometry import tessellate_polygon
from nf_build import area2d, cross3, is_convex

DISTANCE_TOL = .00025
AREA_TOL = .000025

def pieces(points):
    if area2d(points)<0:
        points=points[::-1]
    if is_convex(points):
        return [points]
    return [[points[v] if isinstance(v,int) else tuple(v[:2]) for v in t]
            for t in tessellate_polygon([[Vector((*q,0)) for q in points]])]

def intersect(subject,clip):
    if area2d(clip)<0:
        clip=clip[::-1]
    result=subject
    for i,b in enumerate(clip):
        a=clip[i-1]
        previous=result
        result=[]
        if not previous:break
        for j,q in enumerate(previous):
            p=previous[j-1]
            margin=.000035*hypot(b[0]-a[0],b[1]-a[1])
            s,t=cross3(a,b,p)-margin,cross3(a,b,q)-margin
            if (s>=0)!=(t>=0):
                k=s/(s-t)
                result.append((p[0]+k*(q[0]-p[0]),p[1]+k*(q[1]-p[1])))
            if t>=0:result.append(q)
    return abs(area2d(result)) if len(result)>2 else 0

def overlaps(obj):
    positions=[obj.matrix_world@v.co for v in obj.data.vertices]
    basis=obj.matrix_world.to_3x3().inverted().transposed()
    groups=defaultdict(list)
    for poly in obj.data.polygons:
        pts=[positions[i] for i in poly.vertices]
        n=(basis@poly.normal).normalized()
        if n.length_squared<.9:continue
        axis=max(range(3),key=lambda i:abs(n[i]))
        other=[i for i in range(3) if i!=axis]
        points=[(p[other[0]],p[other[1]]) for p in pts]
        lo,hi=min(p[0] for p in points),max(p[0] for p in points)
        bottom,top=min(p[1] for p in points),max(p[1] for p in points)
        groups[(axis,n[axis]>0)].append(
            (lo,hi,bottom,top,n,n.dot(pts[0]),poly.index,points,pts))
    violations=[]
    for group in groups.values():
        active=[]
        for entry in sorted(group,key=lambda e:e[0]):
            lo,hi,bottom,top,n,d,idx,points,pts=entry
            active=[prior for prior in active if prior[1]>lo+.00002]
            for x0,x1,y0,y1,n2,d2,idx2,poly,pts2 in active:
                if min(top,y1)-max(bottom,y0)<=.00002 or n.dot(n2)<.9999998:continue
                if abs(d-d2)>.006:continue
                if max(abs(n.dot(p)-d) for p in pts2)>DISTANCE_TOL:continue
                if max(abs(n2.dot(p)-d2) for p in pts)>DISTANCE_TOL:continue
                area=sum(intersect(a,b) for a in pieces(points) for b in pieces(poly))
                if area>AREA_TOL:
                    violations.append(dict(faces=[idx2,idx],overlap_m2=round(area,6),
                           normal=[round(x,3) for x in n],
                           point=[round(x,4) for x in pts[0]]))
            active.append(entry)
    return violations
