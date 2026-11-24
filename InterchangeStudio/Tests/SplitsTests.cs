using InterchangeStudio.Core;
using Xunit;

public class SplitsTests
{
    [Theory]
    [InlineData(300f, 0.01f)] [InlineData(300f, 0.06f)] [InlineData(300f, 0.5f)] [InlineData(300f, 0.95f)]
    [InlineData(45f, 0.3f)] [InlineData(61f, 0.2f)] [InlineData(1000f, 0.02f)]
    public void SplitsNeverLeaveASliver(float length, float t)
    {
        float s = Splits.Safe(length, t);
        if (s <= 0f || s >= 1f) return;                       // uses the node instead
        Assert.True(s * length >= Splits.MinSplit - 0.01f);
        Assert.True((1 - s) * length >= Splits.MinSplit - 0.01f);
    }
}
