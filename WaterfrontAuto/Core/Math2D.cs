using System;
using System.Collections.Generic;

namespace WaterfrontAuto.Core
{
    public struct Vec2 : IEquatable<Vec2>
    {
        public float X;
        public float Z;

        public Vec2(float x, float z) { X = x; Z = z; }

        public float LengthSq => X * X + Z * Z;
        public float Length => (float)Math.Sqrt(LengthSq);

        public Vec2 Normalized()
        {
            float len = Length;
            return len > 1e-5f ? new Vec2(X / len, Z / len) : new Vec2(0f, 0f);
        }

        // Right-hand perpendicular in XZ plane (assuming +X right, +Z forward, +Y up: right of (dx, dz) is (dz, -dx))
        public Vec2 RightPerp() => new Vec2(Z, -X);
        public Vec2 LeftPerp() => new Vec2(-Z, X);

        public static Vec2 operator +(Vec2 a, Vec2 b) => new Vec2(a.X + b.X, a.Z + b.Z);
        public static Vec2 operator -(Vec2 a, Vec2 b) => new Vec2(a.X - b.X, a.Z - b.Z);
        public static Vec2 operator -(Vec2 a) => new Vec2(-a.X, -a.Z);
        public static Vec2 operator *(Vec2 a, float s) => new Vec2(a.X * s, a.Z * s);
        public static Vec2 operator *(float s, Vec2 a) => new Vec2(a.X * s, a.Z * s);
        public static Vec2 operator /(Vec2 a, float s) => new Vec2(a.X / s, a.Z / s);

        public static float Dot(Vec2 a, Vec2 b) => a.X * b.X + a.Z * b.Z;
        public static float Cross(Vec2 a, Vec2 b) => a.X * b.Z - a.Z * b.X;
        public static float Distance(Vec2 a, Vec2 b) => (a - b).Length;
        public static float DistanceSq(Vec2 a, Vec2 b) => (a - b).LengthSq;
        public static Vec2 Lerp(Vec2 a, Vec2 b, float t) => new Vec2(a.X + (b.X - a.X) * t, a.Z + (b.Z - a.Z) * t);

        public bool Equals(Vec2 other) => X.Equals(other.X) && Z.Equals(other.Z);
        public override bool Equals(object obj) => obj is Vec2 o && Equals(o);
        public override int GetHashCode() => HashCode.Combine(X, Z);
        public override string ToString() => $"({X:F1}, {Z:F1})";
    }

    public struct Vec3 : IEquatable<Vec3>
    {
        public float X;
        public float Y;
        public float Z;

        public Vec3(float x, float y, float z) { X = x; Y = y; Z = z; }
        public Vec3(Vec2 xz, float y) { X = xz.X; Y = y; Z = xz.Z; }

        public Vec2 XZ => new Vec2(X, Z);
        public float Length => (float)Math.Sqrt(X * X + Y * Y + Z * Z);

        public static Vec3 operator +(Vec3 a, Vec3 b) => new Vec3(a.X + b.X, a.Y + b.Y, a.Z + b.Z);
        public static Vec3 operator -(Vec3 a, Vec3 b) => new Vec3(a.X - b.X, a.Y - b.Y, a.Z - b.Z);
        public static Vec3 operator *(Vec3 a, float s) => new Vec3(a.X * s, a.Y * s, a.Z * s);
        public static Vec3 Lerp(Vec3 a, Vec3 b, float t) => new Vec3(a.X + (b.X - a.X) * t, a.Y + (b.Y - a.Y) * t, a.Z + (b.Z - a.Z) * t);
        public static float Distance(Vec3 a, Vec3 b) => (a - b).Length;

        public bool Equals(Vec3 other) => X.Equals(other.X) && Y.Equals(other.Y) && Z.Equals(other.Z);
        public override bool Equals(object obj) => obj is Vec3 o && Equals(o);
        public override int GetHashCode() => HashCode.Combine(X, Y, Z);
        public override string ToString() => $"({X:F1}, {Y:F1}, {Z:F1})";
    }

    public static class Geom2D
    {
        public static float Clamp(float v, float lo, float hi) => v < lo ? lo : v > hi ? hi : v;

        public static float PointToSegmentDist(Vec2 p, Vec2 a, Vec2 b, out float t, out Vec2 closest)
        {
            Vec2 ab = b - a;
            float lenSq = ab.LengthSq;
            if (lenSq < 1e-8f)
            {
                t = 0f;
                closest = a;
                return Vec2.Distance(p, a);
            }
            t = Clamp(Vec2.Dot(p - a, ab) / lenSq, 0f, 1f);
            closest = a + ab * t;
            return Vec2.Distance(p, closest);
        }

        public static bool SegmentsIntersect(Vec2 a, Vec2 b, Vec2 c, Vec2 d)
        {
            float d1 = Vec2.Cross(d - c, a - c);
            float d2 = Vec2.Cross(d - c, b - c);
            float d3 = Vec2.Cross(b - a, c - a);
            float d4 = Vec2.Cross(b - a, d - a);
            if (((d1 > 1e-5f && d2 < -1e-5f) || (d1 < -1e-5f && d2 > 1e-5f)) &&
                ((d3 > 1e-5f && d4 < -1e-5f) || (d3 < -1e-5f && d4 > 1e-5f)))
                return true;
            return false;
        }

        public static bool PointInConvexQuad(Vec2 p, Vec2[] quad, float margin = 0f)
        {
            if (quad == null || quad.Length < 4) return false;
            float area = SignedArea(quad);
            float sign = area >= 0f ? 1f : -1f;
            for (int i = 0; i < 4; i++)
            {
                Vec2 a = quad[i];
                Vec2 b = quad[(i + 1) % 4];
                Vec2 edge = b - a;
                float len = edge.Length;
                if (len < 1e-5f) continue;
                float cross = Vec2.Cross(edge, p - a) * sign;
                if (cross < -margin * len) return false;
            }
            return true;
        }

        public static bool SegmentIntersectsQuad(Vec2 a, Vec2 b, Vec2[] quad, float shrinkMargin = 0.25f)
        {
            if (quad == null || quad.Length < 4) return false;
            if (PointInConvexQuad(a, quad, -shrinkMargin) || PointInConvexQuad(b, quad, -shrinkMargin))
                return true;
            if (PointInConvexQuad(Vec2.Lerp(a, b, 0.5f), quad, -shrinkMargin))
                return true;
            for (int i = 0; i < 4; i++)
            {
                if (SegmentsIntersect(a, b, quad[i], quad[(i + 1) % 4]))
                    return true;
            }
            return false;
        }

        public static float SignedArea(IReadOnlyList<Vec2> ring)
        {
            if (ring == null || ring.Count < 3) return 0f;
            double sum = 0.0;
            for (int i = 0; i < ring.Count; i++)
            {
                Vec2 a = ring[i];
                Vec2 b = ring[(i + 1) % ring.Count];
                sum += (double)a.X * b.Z - (double)b.X * a.Z;
            }
            return (float)(0.5 * sum);
        }

        public static Vec2[] EnsureCcw(Vec2[] ring)
        {
            if (ring == null || ring.Length < 3) return ring;
            if (SignedArea(ring) >= 0f) return ring;
            var rev = new Vec2[ring.Length];
            for (int i = 0; i < ring.Length; i++) rev[i] = ring[ring.Length - 1 - i];
            return rev;
        }

        /// <summary>Unity Y-axis yaw (radians) so local +Z faces along dir.</summary>
        public static float YawFromDir(Vec2 dir)
        {
            if (dir.LengthSq < 1e-8f) return 0f;
            return (float)Math.Atan2(dir.X, dir.Z);
        }

        public static int DeterministicSeed(float x, float z, int salt = 0)
        {
            unchecked
            {
                int hx = (int)Math.Round(x * 2f);
                int hz = (int)Math.Round(z * 2f);
                uint h = (uint)(hx * 73856093 ^ hz * 19349663 ^ salt * 83492791);
                h ^= h >> 16;
                h *= 0x85ebca6bU;
                h ^= h >> 13;
                h *= 0xc2b2ae35U;
                h ^= h >> 16;
                return (int)(h & 0x7fffffffU);
            }
        }

        public static float Hash01(int seed)
        {
            unchecked
            {
                uint h = (uint)seed;
                h ^= h >> 15;
                h *= 0x2c1b3c6dU;
                h ^= h >> 12;
                h *= 0x297a2d39U;
                h ^= h >> 15;
                return (h & 0x00ffffffU) / 16777216f;
            }
        }
    }
}
