namespace TennisIQ.Domain;

/// <summary>Pure job state transitions used by the admin API (unit-tested).</summary>
public static class AdminJobOps
{
    public static string? Retry(AnalysisJob job)
    {
        if (job.Status != JobStatus.Failed)
            return "Only failed jobs can be retried.";

        job.Status = JobStatus.Pending;
        job.Attempts = 0;
        job.Error = null;
        job.ClaimedAt = null;
        job.CompletedAt = null;
        return null;
    }

    public static string? Cancel(AnalysisJob job, DateTime utcNow)
    {
        if (job.Status == JobStatus.Succeeded)
            return "Succeeded jobs cannot be cancelled.";

        job.Status = JobStatus.Failed;
        job.Error = "Cancelled by admin";
        job.ClaimedAt = null;
        job.CompletedAt = utcNow;
        return null;
    }
}
