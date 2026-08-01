using System.Text.Json;

namespace TennisIQ.Domain;

public interface IVideoStorage
{
    Task<string> SaveAsync(Stream content, string fileName, CancellationToken ct = default);
    Task<Stream> OpenReadAsync(string storageKey, CancellationToken ct = default);
    Task<string> SaveOverlayAsync(Stream content, string preferredName, CancellationToken ct = default);
    string GetAbsolutePath(string storageKey);
}

public interface IAnalysisJobQueue
{
    Task EnqueueAsync(AnalysisJob job, CancellationToken ct = default);
    Task<AnalysisJob?> ClaimNextAsync(CancellationToken ct = default);
    Task CompleteAsync(AnalysisJob job, CancellationToken ct = default);
    Task FailAsync(AnalysisJob job, string error, bool retryable, CancellationToken ct = default);
}

public interface ICoachNarrator
{
    Task<string> NarrateAsync(Analysis analysis, CancellationToken ct = default);
}

public interface IPracticePlanner
{
    PracticePlan CreatePlan(User user, Analysis analysis, IReadOnlyList<Drill> drills);
}

public static class Quota
{
    public const int FreeMonthlyLimit = 3;

    public static bool CanAnalyze(Subscription sub, DateTime utcNow)
    {
        EnsurePeriod(sub, utcNow);
        return sub.Plan == PlanType.Premium || sub.AnalysesUsed < FreeMonthlyLimit;
    }

    public static void RecordAnalysis(Subscription sub, DateTime utcNow)
    {
        EnsurePeriod(sub, utcNow);
        sub.AnalysesUsed += 1;
    }

    public static void EnsurePeriod(Subscription sub, DateTime utcNow)
    {
        var periodStart = new DateTime(utcNow.Year, utcNow.Month, 1, 0, 0, 0, DateTimeKind.Utc);
        if (sub.PeriodStart < periodStart)
        {
            sub.PeriodStart = periodStart;
            sub.AnalysesUsed = 0;
        }
    }
}

public sealed class RuleBasedCoachNarrator : ICoachNarrator
{
    public Task<string> NarrateAsync(Analysis analysis, CancellationToken ct = default)
    {
        if (analysis.Status != "ok")
        {
            return Task.FromResult(
                "I couldn't get a clean read on that clip. Re-film from the side in good light, " +
                "keep your full body in frame, and capture from ready position through the finish.");
        }

        var script =
            $"Here's your {analysis.Stroke} check-in. Overall grade {analysis.Grade}, score {analysis.OverallScore:0}. " +
            $"What looked solid: {string.Join(" ", analysis.PhaseScores.OrderByDescending(p => p.Score).Take(2).Select(p => p.Feedback))} " +
            $"Your highest-impact fix: {analysis.TopFix} " +
            "Nail that one thing in practice this week before adding anything else.";
        return Task.FromResult(script);
    }
}

public sealed class PracticePlanner : IPracticePlanner
{
    public PracticePlan CreatePlan(User user, Analysis analysis, IReadOnlyList<Drill> drills)
    {
        var weakest = analysis.PhaseScores.OrderBy(p => p.Score).FirstOrDefault();
        var focus = weakest?.Phase ?? "contact";
        var strokeDrills = drills
            .Where(d => d.Stroke == analysis.Stroke || d.Stroke == "any")
            .Where(d => d.Focus == focus || d.Focus == "footwork" || d.Focus == "warmup" || d.Focus == "cooldown")
            .ToList();

        if (strokeDrills.Count == 0)
            strokeDrills = drills.Take(4).ToList();

        var items = new List<object>
        {
            new { section = "Warm-up", drill = strokeDrills.FirstOrDefault(d => d.Focus == "warmup")?.Name ?? "Dynamic stretch + shadow swings", reps = 5, minutes = 8 },
            new { section = "Focus basket", drill = strokeDrills.FirstOrDefault(d => d.Focus == focus)?.Name ?? $"{analysis.Stroke} feeds focusing on {focus}", reps = 30, minutes = 15 },
            new { section = "Footwork", drill = strokeDrills.FirstOrDefault(d => d.Focus == "footwork")?.Name ?? "Split-step recovery ladders", reps = 12, minutes = 10 },
            new { section = "Cool down", drill = strokeDrills.FirstOrDefault(d => d.Focus == "cooldown")?.Name ?? "Band stretch + breathing", reps = 1, minutes = 5 },
        };

        return new PracticePlan
        {
            UserId = user.Id,
            GeneratedFromAnalysisId = analysis.Id,
            Goal = $"Improve {analysis.Stroke} {focus.Replace('_', ' ')}",
            ItemsJson = JsonSerializer.Serialize(items),
        };
    }
}
