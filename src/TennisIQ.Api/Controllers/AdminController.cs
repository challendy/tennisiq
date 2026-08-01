using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using TennisIQ.Domain;
using TennisIQ.Infrastructure.Persistence;

namespace TennisIQ.Api.Controllers;

public record SetPlanRequest(string Plan);

[ApiController]
[Authorize(Policy = "AdminOnly")]
[Route("api/admin")]
public sealed class AdminController(AppDbContext db) : ControllerBase
{
    [HttpGet("users")]
    public async Task<ActionResult<object>> ListUsers([FromQuery] string? q, [FromQuery] int take = 50, CancellationToken ct = default)
    {
        take = Math.Clamp(take, 1, 200);
        var query = db.Users.AsNoTracking().Include(u => u.Subscription).AsQueryable();
        if (!string.IsNullOrWhiteSpace(q))
        {
            var term = q.Trim().ToLowerInvariant();
            query = query.Where(u => u.Email.Contains(term));
        }

        var users = await query
            .OrderByDescending(u => u.CreatedAt)
            .Take(take)
            .ToListAsync(ct);

        return Ok(new
        {
            users = users.Select(SummarizeUser),
        });
    }

    [HttpPost("users/{id:guid}/plan")]
    public async Task<ActionResult<object>> SetPlan(Guid id, [FromBody] SetPlanRequest req, CancellationToken ct)
    {
        if (!Enum.TryParse<PlanType>(req.Plan, ignoreCase: true, out var plan)
            || (plan is not PlanType.Free and not PlanType.Premium))
        {
            return BadRequest(new { error = "Plan must be Free or Premium." });
        }

        var user = await db.Users.Include(u => u.Subscription).FirstOrDefaultAsync(u => u.Id == id, ct);
        if (user is null) return NotFound();

        user.Subscription.Plan = plan;
        await db.SaveChangesAsync(ct);
        return Ok(SummarizeUser(user));
    }

    [HttpPost("users/{id:guid}/reset-quota")]
    public async Task<ActionResult<object>> ResetQuota(Guid id, CancellationToken ct)
    {
        var user = await db.Users.Include(u => u.Subscription).FirstOrDefaultAsync(u => u.Id == id, ct);
        if (user is null) return NotFound();

        user.Subscription.AnalysesUsed = 0;
        await db.SaveChangesAsync(ct);
        return Ok(SummarizeUser(user));
    }

    [HttpGet("jobs")]
    public async Task<ActionResult<object>> ListJobs([FromQuery] string? status, [FromQuery] int take = 50, CancellationToken ct = default)
    {
        take = Math.Clamp(take, 1, 200);
        var query = db.AnalysisJobs.AsNoTracking()
            .Include(j => j.Video).ThenInclude(v => v.User)
            .AsQueryable();

        if (!string.IsNullOrWhiteSpace(status)
            && Enum.TryParse<JobStatus>(status, ignoreCase: true, out var st))
        {
            query = query.Where(j => j.Status == st);
        }

        var jobs = await query
            .OrderByDescending(j => j.CreatedAt)
            .Take(take)
            .ToListAsync(ct);

        return Ok(new
        {
            jobs = jobs.Select(j => new
            {
                id = j.Id,
                videoId = j.VideoId,
                userId = j.Video.UserId,
                userEmail = j.Video.User.Email,
                stroke = j.Video.Stroke,
                status = j.Status.ToString(),
                attempts = j.Attempts,
                error = j.Error,
                createdAt = j.CreatedAt,
                claimedAt = j.ClaimedAt,
            }),
        });
    }

    [HttpPost("jobs/{id:guid}/retry")]
    public async Task<ActionResult<object>> RetryJob(Guid id, CancellationToken ct)
    {
        var job = await db.AnalysisJobs
            .Include(j => j.Video).ThenInclude(v => v.User)
            .FirstOrDefaultAsync(j => j.Id == id, ct);
        if (job is null) return NotFound();

        var err = AdminJobOps.Retry(job);
        if (err is not null) return BadRequest(new { error = err });

        await db.SaveChangesAsync(ct);
        return Ok(new
        {
            id = job.Id,
            status = job.Status.ToString(),
            attempts = job.Attempts,
            error = job.Error,
        });
    }

    [HttpPost("jobs/{id:guid}/cancel")]
    public async Task<ActionResult<object>> CancelJob(Guid id, CancellationToken ct)
    {
        var job = await db.AnalysisJobs
            .Include(j => j.Video).ThenInclude(v => v.User)
            .FirstOrDefaultAsync(j => j.Id == id, ct);
        if (job is null) return NotFound();

        var err = AdminJobOps.Cancel(job, DateTime.UtcNow);
        if (err is not null) return BadRequest(new { error = err });

        await db.SaveChangesAsync(ct);
        return Ok(new
        {
            id = job.Id,
            status = job.Status.ToString(),
            attempts = job.Attempts,
            error = job.Error,
        });
    }

    private static object SummarizeUser(User user) => new
    {
        id = user.Id,
        email = user.Email,
        displayName = user.DisplayName,
        plan = user.Subscription.Plan.ToString(),
        analysesUsed = user.Subscription.AnalysesUsed,
        analysesLimit = user.Subscription.Plan == PlanType.Premium ? (int?)null : Quota.FreeMonthlyLimit,
        periodStart = user.Subscription.PeriodStart,
        isAdmin = user.IsAdmin,
        createdAt = user.CreatedAt,
    };
}
