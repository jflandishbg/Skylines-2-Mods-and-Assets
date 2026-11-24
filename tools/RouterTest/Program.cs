using System; using Unity.Mathematics; using ClaudeInterchanges;
class P {
  static float MinRadius(RampPath p) { float L = p.Length, best = 1e9f; for (float s = 4; s < L - 4; s += 2) { float2 a = p.Dir(s - 2), b = p.Dir(s + 2); float ang = math.abs(math.atan2(a.x*b.y-a.y*b.x, math.dot(a,b))); if (ang > 1e-4f) best = math.min(best, 4f / ang); } return best; }
  static void Main() {
    foreach (var c in new[]{ ("loop", new float2(82,-32), 0f, new float2(-32,-82), math.PI/2, 50f), ("right", new float2(-128,-32), 0f, new float2(-32,-128), -math.PI/2, 96f), ("sbend", new float2(0,0), 0f, new float2(200,40), 0f, 60f) }) {
      var all = Dubins.All(c.Item2, c.Item3, c.Item4, c.Item5, c.Item6); all.Sort((a,b)=>a.Length.CompareTo(b.Length));
      var p0 = all[0]; var p = new RampPath{Word=p0.Word}; p.Prims.Add(new LinePrim(c.Item2 - new float2(math.cos(c.Item3), math.sin(c.Item3))*60, new float2(math.cos(c.Item3), math.sin(c.Item3)), 60)); p.Prims.AddRange(p0.Prims); p.Prims.Add(new LinePrim(c.Item4, new float2(math.cos(c.Item5), math.sin(c.Item5)), 60)); foreach (var it in new[]{3,5,8}) { var s2 = Smoothing.Smooth(p, it); Console.Write($" it{it}:minR={MinRadius(s2):F0}"); } var sm = Smoothing.Smooth(p, 5);
      Console.WriteLine($"{c.Item1}: {p.Word} L={p.Length:F0} minR={MinRadius(p):F0} -> smooth L={sm.Length:F0} minR={MinRadius(sm):F0} pieces={sm.Prims.Count} start={sm.Pos(0)} end={sm.Pos(sm.Length)} dirEnd={sm.Dir(sm.Length)} turn={sm.LargestTurnDeg():F0}");
    }
  }
}
