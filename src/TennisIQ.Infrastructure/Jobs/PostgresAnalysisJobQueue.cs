using Microsoft.EntityFrameworkCore;
using TennisIQ.Domain;
using TennisIQ.Infrastructure.Persistence;

namespace TennisIQ.Infrastructure.Jobs;

public sealed class PostgresAnalysisJobQueue(AppDbContext db) : IAnalysisJobQueue
{
    private const int MaxAttempts = 3;

    public async Task EnqueueAsync(AnalysisJob job, CancellationToken ct = default)
    {
        db.AnalysisJobs.Add(job);
        await db.SaveChangesAsync(ct);
    }

    public async Task<AnalysisJob?> ClaimNextAsync(CancellationToken ct = default)
    {
        await using var tx = await db.Database.BeginTransactionAsync(ct);

        var jobId = await db.AnalysisJobs
            .FromSqlRaw("""
                SELECT * FROM "AnalysisJobs"
                WHERE "Status" = {0}
                ORDER BY "CreatedAt"
                FOR UPDATE SKIP LOCKED
                LIMIT 1
                """, (int)JobStatus.Pending)
            .AsNoTracking()
            .Select(j => j.Id)
            .FirstOrDefaultAsync(ct);

        if (jobId == Guid.Empty)
        {
            await tx.CommitAsync(ct);
            return null;
        }

        var job = await db.AnalysisJobs
            .Include(j => j.Video)
            .FirstAsync(j => j.Id == jobId, ct);

        job.Status = JobStatus.Running;
        job.ClaimedAt = DateTime.UtcNow;
        job.Attempts += 1;
        await db.SaveChangesAsync(ct);
        await tx.CommitAsync(ct);
        return job;
    }

    public async Task CompleteAsync(AnalysisJob job, CancellationToken ct = default)
    {
        job.Status = JobStatus.Succeeded;
        job.CompletedAt = DateTime.UtcNow;
        job.Error = null;
        await db.SaveChangesAsync(ct);
    }

    public async Task FailAsync(AnalysisJob job, string error, bool retryable, CancellationToken ct = default)
    {
        job.Error = error;
        if (retryable && job.Attempts < MaxAttempts)
        {
            job.Status = JobStatus.Pending;
            job.ClaimedAt = null;
        }
        else
        {
            job.Status = JobStatus.Failed;
            job.CompletedAt = DateTime.UtcNow;
        }
        await db.SaveChangesAsync(ct);
    }
}
