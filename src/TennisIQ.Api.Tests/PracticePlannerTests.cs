using System.Text.Json;
using TennisIQ.Domain;

namespace TennisIQ.Api.Tests;

public class PracticePlannerTests
{
    [Fact]
    public void Plan_targets_weakest_phase()
    {
        var user = new User { DisplayName = "Chris" };
        var analysis = new Analysis
        {
            Stroke = "forehand",
            Status = "ok",
            PhaseScores =
            [
                new PhaseScoreEntity { Phase = "contact", Score = 90, Feedback = "Good" },
                new PhaseScoreEntity { Phase = "takeback", Score = 40, Feedback = "Short" },
            ],
        };
        var drills = new List<Drill>
        {
            new() { Name = "Warm", Focus = "warmup", Stroke = "any" },
            new() { Name = "Takeback mirror", Focus = "takeback", Stroke = "forehand" },
            new() { Name = "Footwork", Focus = "footwork", Stroke = "any" },
            new() { Name = "Cool", Focus = "cooldown", Stroke = "any" },
        };

        var plan = new PracticePlanner().CreatePlan(user, analysis, drills);
        Assert.Contains("takeback", plan.Goal);
        var items = JsonSerializer.Deserialize<JsonElement>(plan.ItemsJson);
        Assert.Equal(JsonValueKind.Array, items.ValueKind);
        Assert.True(items.GetArrayLength() >= 3);
    }
}
