using TennisIQ.Domain;

namespace TennisIQ.Api.Tests;

public class QuotaTests
{
    [Fact]
    public void Free_user_blocked_after_three()
    {
        var sub = new Subscription { Plan = PlanType.Free, AnalysesUsed = 3, PeriodStart = new DateTime(2026, 8, 1, 0, 0, 0, DateTimeKind.Utc) };
        Assert.False(Quota.CanAnalyze(sub, new DateTime(2026, 8, 15, 0, 0, 0, DateTimeKind.Utc)));
    }

    [Fact]
    public void Free_quota_resets_next_month()
    {
        var sub = new Subscription { Plan = PlanType.Free, AnalysesUsed = 3, PeriodStart = new DateTime(2026, 7, 1, 0, 0, 0, DateTimeKind.Utc) };
        Assert.True(Quota.CanAnalyze(sub, new DateTime(2026, 8, 1, 0, 0, 0, DateTimeKind.Utc)));
        Assert.Equal(0, sub.AnalysesUsed);
    }

    [Fact]
    public void Premium_unlimited()
    {
        var sub = new Subscription { Plan = PlanType.Premium, AnalysesUsed = 100 };
        Assert.True(Quota.CanAnalyze(sub, DateTime.UtcNow));
    }
}
