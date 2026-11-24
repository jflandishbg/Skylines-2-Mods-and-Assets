"""Vector/constant compatibility shim: uses mathutils inside Blender, pure Python outside."""
import math

try:
    from mathutils import Vector  # type: ignore
except ImportError:
    class Vector:
        """Minimal 3D vector compatible with mathutils.Vector for pure-Python builds and tests."""

        __slots__ = ("_c",)

        def __init__(self, *args):
            if len(args) == 0:
                self._c = (0.0, 0.0, 0.0)
            elif len(args) == 1:
                vals = list(args[0])
                if len(vals) == 2:
                    self._c = (float(vals[0]), float(vals[1]), 0.0)
                elif len(vals) == 3:
                    self._c = (float(vals[0]), float(vals[1]), float(vals[2]))
                else:
                    raise ValueError(f"Vector expects 2 or 3 components, got {len(vals)}")
            elif len(args) in (2, 3):
                vals = [float(a) for a in args]
                if len(vals) == 2:
                    vals.append(0.0)
                self._c = (vals[0], vals[1], vals[2])
            else:
                raise ValueError(f"Vector expects 2 or 3 arguments, got {len(args)}")

        @property
        def x(self):
            return self._c[0]

        @property
        def y(self):
            return self._c[1]

        @property
        def z(self):
            return self._c[2]

        def __len__(self):
            return 3

        def __iter__(self):
            return iter(self._c)

        def __getitem__(self, idx):
            return self._c[idx]

        def __repr__(self):
            return f"Vector({self._c!r})"

        def __eq__(self, other):
            if isinstance(other, Vector):
                return self._c == other._c
            return False

        def __add__(self, other):
            o = other._c if isinstance(other, Vector) else tuple(other)
            return Vector(self._c[0] + o[0], self._c[1] + o[1], self._c[2] + o[2])

        def __radd__(self, other):
            return self.__add__(other)

        def __sub__(self, other):
            o = other._c if isinstance(other, Vector) else tuple(other)
            return Vector(self._c[0] - o[0], self._c[1] - o[1], self._c[2] - o[2])

        def __rsub__(self, other):
            o = other._c if isinstance(other, Vector) else tuple(other)
            return Vector(o[0] - self._c[0], o[1] - self._c[1], o[2] - self._c[2])

        def __neg__(self):
            return Vector(-self._c[0], -self._c[1], -self._c[2])

        def __mul__(self, k):
            k = float(k)
            return Vector(self._c[0] * k, self._c[1] * k, self._c[2] * k)

        def __rmul__(self, k):
            return self.__mul__(k)

        def __truediv__(self, k):
            k = float(k)
            return Vector(self._c[0] / k, self._c[1] / k, self._c[2] / k)

        @property
        def length_squared(self):
            x, y, z = self._c
            return x * x + y * y + z * z

        @property
        def length(self):
            return math.sqrt(self.length_squared)

        def normalized(self):
            L = self.length
            if L <= 0.0:
                return Vector(0.0, 0.0, 0.0)
            return Vector(self._c[0] / L, self._c[1] / L, self._c[2] / L)

        def normalize(self):
            self._c = self.normalized()._c

        def negate(self):
            self._c = (-self._c[0], -self._c[1], -self._c[2])

        def dot(self, other):
            o = other._c if isinstance(other, Vector) else tuple(other)
            return self._c[0] * o[0] + self._c[1] * o[1] + self._c[2] * o[2]

        def cross(self, other):
            ax, ay, az = self._c
            bx, by, bz = other._c if isinstance(other, Vector) else tuple(other)
            return Vector(ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)

        def copy(self):
            return Vector(self._c)

        def to_tuple(self):
            return self._c


E = 0.004  # 4 mm air gap preventing coplanar z-fighting
UP = Vector((0.0, 0.0, 1.0))
DOWN = Vector((0.0, 0.0, -1.0))
