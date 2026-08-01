using System.Security.Claims;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using TennisIQ.Domain;
using TennisIQ.Infrastructure.Persistence;

namespace TennisIQ.Api.Controllers;

[ApiController]
[Authorize]
[Route("api")]
public sealed class AnalysesController(
    AppDbContext db,
    IVideoStorage storage) : ControllerBase
{
    [HttpPost("videos")]
    [RequestSizeLimit(200_000_000)]
    public async Task<ActionResult<object>> Upload(
        IFormFile file,
        [FromForm] string stroke = "forehand",
        [FromForm] string? handedness = null,
        CancellationToken ct = default)
    {
        if (file is null || file.Length == 0)
            return BadRequest(new { error = "Video file required." });

        var allowed = new[] { ".mp4", ".mov", ".webm", ".m4v" };
        var ext = Path.GetExtension(file.FileName).ToLowerInvariant();
        if (!allowed.Contains(ext))
            return BadRequest(new { error = "Unsupported format. Use mp4, mov, webm, or m4v." });

        var user = await db.Users.Include(u => u.Subscription).FirstAsync(u => u.Id == UserId(), ct);
        if (!Quota.CanAnalyze(user.Subscription, DateTime.UtcNow))
        {
            return StatusCode(StatusCodes.Status402PaymentRequired, new
            {
                error = "Free plan limit reached (3 analyses/month).",
                plan = user.Subscription.Plan.ToString(),
                analysesUsed = user.Subscription.AnalysesUsed,
                periodStart = user.Subscription.PeriodStart,
            });
        }

        await using var stream = file.OpenReadStream();
        var key = await storage.SaveAsync(stream, file.FileName, ct);
        var video = new Video
        {
            UserId = user.Id,
            StorageKey = key,
            Stroke = NormalizeStroke(stroke),
            Handedness = handedness is "left" or "right" ? handedness : user.Handedness,
            OriginalFileName = file.FileName,
            SizeBytes = file.Length,
            Job = new AnalysisJob(),
        };
        db.Videos.Add(video);
        await db.SaveChangesAsync(ct);

        return Accepted(new
        {
            videoId = video.Id,
            jobId = video.Job!.Id,
            status = video.Job.Status.ToString(),
        });
    }

    [HttpGet("jobs/{jobId:guid}")]
    public async Task<ActionResult<object>> GetJob(Guid jobId, CancellationToken ct)
    {
        var job = await db.AnalysisJobs.Include(j => j.Video)
            .FirstOrDefaultAsync(j => j.Id == jobId && j.Video.UserId == UserId(), ct);
        if (job is null) return NotFound();

        Guid? analysisId = null;
        if (job.Status == JobStatus.Succeeded)
        {
            analysisId = await db.Analyses.Where(a => a.VideoId == job.VideoId)
                .Select(a => (Guid?)a.Id).FirstOrDefaultAsync(ct);
        }

        return Ok(new
        {
            jobId = job.Id,
            videoId = job.VideoId,
            status = job.Status.ToString(),
            attempts = job.Attempts,
            error = job.Error,
            analysisId,
        });
    }

    [HttpGet("analyses")]
    public async Task<ActionResult<object>> List(CancellationToken ct)
    {
        var items = await db.Analyses.AsNoTracking()
            .Where(a => a.UserId == UserId())
            .OrderByDescending(a => a.CreatedAt)
            .Select(a => new
            {
                a.Id,
                a.Stroke,
                a.Status,
                a.OverallScore,
                a.Grade,
                a.Confidence,
                a.TopFix,
                a.CreatedAt,
                a.VideoId,
            })
            .Take(50)
            .ToListAsync(ct);
        return Ok(items);
    }

    [HttpGet("analyses/{id:guid}")]
    public async Task<ActionResult<object>> Get(Guid id, CancellationToken ct)
    {
        var a = await db.Analyses.AsNoTracking()
            .Include(x => x.PhaseScores)
            .FirstOrDefaultAsync(x => x.Id == id && x.UserId == UserId(), ct);
        if (a is null) return NotFound();

        var result = JsonSerializer.Deserialize<JsonElement>(
            string.IsNullOrWhiteSpace(a.ResultJson) ? "{}" : a.ResultJson);
        return Ok(new
        {
            a.Id,
            a.VideoId,
            a.Stroke,
            a.Status,
            a.OverallScore,
            a.Grade,
            a.Confidence,
            a.TopFix,
            a.CoachingScript,
            a.OverlayKey,
            overlayUrl = a.OverlayKey is null ? null : $"/api/overlays/{a.Id}",
            phases = a.PhaseScores.Select(p => new { p.Phase, p.Score, p.Feedback }),
            result,
            a.CreatedAt,
        });
    }

    [HttpGet("overlays/{analysisId:guid}")]
    public async Task<IActionResult> Overlay(Guid analysisId, CancellationToken ct)
    {
        var a = await db.Analyses.AsNoTracking()
            .FirstOrDefaultAsync(x => x.Id == analysisId && x.UserId == UserId(), ct);
        if (a?.OverlayKey is null) return NotFound();
        var path = storage.GetAbsolutePath(a.OverlayKey);
        if (!System.IO.File.Exists(path)) return NotFound();
        return PhysicalFile(path, "video/mp4", enableRangeProcessing: true);
    }

    [HttpGet("analyses/compare")]
    public async Task<ActionResult<object>> Compare([FromQuery] Guid a, [FromQuery] Guid b, CancellationToken ct)
    {
        var userId = UserId();
        var left = await db.Analyses.Include(x => x.PhaseScores)
            .FirstOrDefaultAsync(x => x.Id == a && x.UserId == userId, ct);
        var right = await db.Analyses.Include(x => x.PhaseScores)
            .FirstOrDefaultAsync(x => x.Id == b && x.UserId == userId, ct);
        if (left is null || right is null) return NotFound();
        if (left.Stroke != right.Stroke)
            return BadRequest(new { error = "Compare analyses of the same stroke." });

        var phases = left.PhaseScores.Select(lp =>
        {
            var rp = right.PhaseScores.FirstOrDefault(x => x.Phase == lp.Phase);
            var delta = (rp?.Score ?? 0) - lp.Score;
            return new
            {
                phase = lp.Phase,
                a = lp.Score,
                b = rp?.Score ?? 0,
                delta,
                direction = delta > 0.5 ? "improved" : delta < -0.5 ? "regressed" : "stable",
            };
        }).ToList();

        return Ok(new
        {
            stroke = left.Stroke,
            a = new { left.Id, left.OverallScore, left.Grade, left.CreatedAt },
            b = new { right.Id, right.OverallScore, right.Grade, right.CreatedAt },
            overallDelta = right.OverallScore - left.OverallScore,
            phases,
        });
    }

    private Guid UserId() => Guid.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)
        ?? User.FindFirstValue("sub")!);

    private static string NormalizeStroke(string stroke) =>
        stroke.ToLowerInvariant() switch
        {
            "serve" or "forehand" or "backhand" or "volley" or "overhead" => stroke.ToLowerInvariant(),
            _ => "forehand",
        };
}
