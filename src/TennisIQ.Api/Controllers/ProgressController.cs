using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using TennisIQ.Infrastructure.Persistence;

namespace TennisIQ.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/progress")]
public sealed class ProgressController(AppDbContext db) : ControllerBase
{
    [HttpGet]
    public async Task<ActionResult<object>> Get(CancellationToken ct)
    {
        var userId = Guid.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)
            ?? User.FindFirstValue("sub")!);

        var analyses = await db.Analyses.AsNoTracking()
            .Where(a => a.UserId == userId && a.Status == "ok")
            .OrderBy(a => a.CreatedAt)
            .Select(a => new { a.Id, a.Stroke, a.OverallScore, a.Grade, a.CreatedAt })
            .ToListAsync(ct);

        var byStroke = analyses
            .GroupBy(a => a.Stroke)
            .Select(g => new
            {
                stroke = g.Key,
                latest = g.Last().OverallScore,
                best = g.Max(x => x.OverallScore),
                count = g.Count(),
                history = g.Select(x => new { x.CreatedAt, x.OverallScore, x.Grade, x.Id }),
            })
            .ToList();

        var overall = analyses.Count == 0 ? 0 : analyses.Average(a => a.OverallScore);

        return Ok(new
        {
            tennisIqScore = Math.Round(overall, 1),
            totalAnalyses = analyses.Count,
            strokes = byStroke,
        });
    }
}
