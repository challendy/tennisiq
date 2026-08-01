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
[Route("api/practice")]
public sealed class PracticeController(AppDbContext db, IPracticePlanner planner) : ControllerBase
{
    [HttpPost("plans")]
    public async Task<ActionResult<object>> Create([FromQuery] Guid? analysisId, CancellationToken ct)
    {
        var userId = Guid.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub")!);

        Analysis? analysis;
        if (analysisId is Guid id)
        {
            analysis = await db.Analyses.Include(a => a.PhaseScores)
                .FirstOrDefaultAsync(a => a.Id == id && a.UserId == userId, ct);
        }
        else
        {
            analysis = await db.Analyses.Include(a => a.PhaseScores)
                .Where(a => a.UserId == userId && a.Status == "ok")
                .OrderByDescending(a => a.CreatedAt)
                .FirstOrDefaultAsync(ct);
        }

        if (analysis is null)
            return BadRequest(new { error = "No analysis available to build a plan from." });

        var user = await db.Users.FirstAsync(u => u.Id == userId, ct);
        var drills = await db.Drills.AsNoTracking().ToListAsync(ct);
        var plan = planner.CreatePlan(user, analysis, drills);
        db.PracticePlans.Add(plan);
        await db.SaveChangesAsync(ct);

        return Ok(new
        {
            plan.Id,
            plan.Goal,
            plan.GeneratedFromAnalysisId,
            items = JsonSerializer.Deserialize<JsonElement>(plan.ItemsJson),
            plan.CreatedAt,
        });
    }

    [HttpGet("plans")]
    public async Task<ActionResult<object>> List(CancellationToken ct)
    {
        var userId = Guid.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub")!);
        var plans = await db.PracticePlans.AsNoTracking()
            .Where(p => p.UserId == userId)
            .OrderByDescending(p => p.CreatedAt)
            .Take(20)
            .ToListAsync(ct);

        return Ok(plans.Select(p => new
        {
            p.Id,
            p.Goal,
            p.GeneratedFromAnalysisId,
            items = JsonSerializer.Deserialize<JsonElement>(p.ItemsJson),
            p.CreatedAt,
        }));
    }
}
