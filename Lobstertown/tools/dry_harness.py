import sys, types
from unittest.mock import MagicMock
for n in ("bpy","bmesh","mathutils"):
    sys.modules[n]=MagicMock()
import math
class V:
    def __init__(s,c): s.c=tuple(float(x) for x in c)
    def __iter__(s): return iter(s.c)
    def __getitem__(s,i): return s.c[i]
    def __len__(s): return len(s.c)
    x=property(lambda s:s.c[0]); y=property(lambda s:s.c[1]); z=property(lambda s:s.c[2] if len(s.c)>2 else 0)
    def __add__(s,o): return V(a+b for a,b in zip(s.c,o))
    def __sub__(s,o): return V(a-b for a,b in zip(s.c,o))
    def __neg__(s): return V(-a for a in s.c)
    def __mul__(s,k): return V(a*k for a in s.c)
    __rmul__=__mul__
    def __truediv__(s,k): return V(a/k for a in s.c)
    @property
    def length(s): return math.sqrt(sum(a*a for a in s.c))
    def normalized(s):
        L=s.length; return V(a/L for a in s.c) if L else V(s.c)
    def normalize(s): s.c=s.normalized().c
    def dot(s,o): return sum(a*b for a,b in zip(s.c,o))
    def cross(s,o):
        a,b=s.c,tuple(o); return V((a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]))
    def copy(s): return V(s.c)
    def to_tuple(s): return s.c
sys.modules["mathutils"].Vector=lambda *a: V(a[0]) if len(a)==1 else V(a)
SRC=sys.argv[1]; sys.path.insert(0,SRC)
import nf_kit
TR=[]
def _mk(self,name,*a,**k):
    TR.append(sum(len(f)-2 for f in self.f))
nf_kit.Mesh.make=_mk
import importlib
mod=importlib.import_module("lt_designs."+sys.argv[2])
kw=eval(sys.argv[3]) if len(sys.argv)>3 else {}
for lod in (0,1,2):
    try:
        TR.clear(); mod.build(lod, **kw); print("lod",lod,"ok tris",TR)
    except Exception as e:
        import traceback; traceback.print_exc(); break
