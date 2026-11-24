// Interchange Studio - Core/Splits.cs
// Where a new road may split an existing road piece without leaving a sliver the game rejects.
using Unity.Mathematics;

namespace InterchangeStudio.Core
{
    public static class Splits
    {
        /*
         * Where along a road piece of a given length a new road may split it: at least MinSplit metres from
         * either end, so neither leftover is a sliver the game rejects as an invalid shape.
         * Returns 0 or 1 to mean "use that end's node instead".
         */
        public const float MinSplit = 30f;

        /// <summary>
        /// Every highway piece meeting a ramp's diverge or merge must be at least this long: the gore (the
        /// junction's footprint) eats into each of them, and a shorter piece folds (seen in-game 2026-10-15 on
        /// a 40 m piece upstream of a diverge).
        /// </summary>
        public const float GoreClear = 55f;
        public static float Safe(float length, float t)
        {
            if (length < MinSplit * 2f) return t < 0.5f ? 0f : 1f;
            float lo = MinSplit / length, hi = 1f - lo;
            if (t < lo * 0.5f) return 0f;
            if (t > 1f - lo * 0.5f) return 1f;
            return math.clamp(t, lo, hi);
        }
    }
}
