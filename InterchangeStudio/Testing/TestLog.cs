using System;
using System.Collections.Generic;
using InterchangeStudio.Core;

namespace InterchangeStudio.Testing
{
    /// <summary>Collects the planner's log lines so a test can print why something didn't fit.</summary>
    public sealed class TestLog : IPlanLog
    {
        public readonly List<string> Lines = new List<string>();
        public void Info(string line) => Lines.Add(line);
        public void Warn(string line) => Lines.Add("WARN " + line);
        public void Error(Exception e, string line) => Lines.Add("ERROR " + line + ": " + e);
    }
}
