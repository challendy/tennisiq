using TennisIQ.Domain;

namespace TennisIQ.Api.Tests;

public class AdminJobOpsTests
{
    [Fact]
    public void Retry_failed_resets_to_pending()
    {
        var job = new AnalysisJob
        {
            Status = JobStatus.Failed,
            Attempts = 3,
            Error = "boom",
            ClaimedAt = DateTime.UtcNow,
            CompletedAt = DateTime.UtcNow,
        };
        Assert.Null(AdminJobOps.Retry(job));
        Assert.Equal(JobStatus.Pending, job.Status);
        Assert.Equal(0, job.Attempts);
        Assert.Null(job.Error);
        Assert.Null(job.ClaimedAt);
        Assert.Null(job.CompletedAt);
    }

    [Fact]
    public void Retry_rejects_non_failed()
    {
        var job = new AnalysisJob { Status = JobStatus.Pending };
        Assert.NotNull(AdminJobOps.Retry(job));
    }

    [Fact]
    public void Cancel_marks_failed()
    {
        var now = new DateTime(2026, 8, 1, 12, 0, 0, DateTimeKind.Utc);
        var job = new AnalysisJob { Status = JobStatus.Pending };
        Assert.Null(AdminJobOps.Cancel(job, now));
        Assert.Equal(JobStatus.Failed, job.Status);
        Assert.Equal("Cancelled by admin", job.Error);
        Assert.Equal(now, job.CompletedAt);
    }

    [Fact]
    public void Cancel_rejects_succeeded()
    {
        var job = new AnalysisJob { Status = JobStatus.Succeeded };
        Assert.NotNull(AdminJobOps.Cancel(job, DateTime.UtcNow));
    }

    [Fact]
    public void Premium_after_plan_change_bypasses_free_cap()
    {
        var sub = new Subscription
        {
            Plan = PlanType.Free,
            AnalysesUsed = 3,
            PeriodStart = new DateTime(2026, 8, 1, 0, 0, 0, DateTimeKind.Utc),
        };
        Assert.False(Quota.CanAnalyze(sub, new DateTime(2026, 8, 15, 0, 0, 0, DateTimeKind.Utc)));
        sub.Plan = PlanType.Premium;
        Assert.True(Quota.CanAnalyze(sub, new DateTime(2026, 8, 15, 0, 0, 0, DateTimeKind.Utc)));
    }

    [Fact]
    public void Reset_quota_allows_free_user_again()
    {
        var sub = new Subscription
        {
            Plan = PlanType.Free,
            AnalysesUsed = 3,
            PeriodStart = new DateTime(2026, 8, 1, 0, 0, 0, DateTimeKind.Utc),
        };
        Assert.False(Quota.CanAnalyze(sub, new DateTime(2026, 8, 15, 0, 0, 0, DateTimeKind.Utc)));
        sub.AnalysesUsed = 0;
        Assert.True(Quota.CanAnalyze(sub, new DateTime(2026, 8, 15, 0, 0, 0, DateTimeKind.Utc)));
    }
}
