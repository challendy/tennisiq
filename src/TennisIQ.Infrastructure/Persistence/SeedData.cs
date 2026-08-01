using Microsoft.EntityFrameworkCore;
using TennisIQ.Domain;

namespace TennisIQ.Infrastructure.Persistence;

public static class SeedData
{
    public static async Task EnsureSeededAsync(AppDbContext db)
    {
        if (await db.Drills.AnyAsync())
            return;

        db.Drills.AddRange(
            new Drill { Name = "Jog + shadow swings", Focus = "warmup", Stroke = "any", Equipment = "none", DefaultReps = 10, Instructions = "Light jog around the court, 10 shadow forehands and backhands." },
            new Drill { Name = "Unit turn feeds", Focus = "unit_turn", Stroke = "forehand", Equipment = "basket", DefaultReps = 30, Instructions = "Coach feeds to forehand. Freeze after unit turn for 1 second before swinging." },
            new Drill { Name = "Takeback mirror", Focus = "takeback", Stroke = "forehand", Equipment = "none", DefaultReps = 20, Instructions = "Shadow swings in a mirror focusing on a full takeback past the back hip." },
            new Drill { Name = "Slot drop tosses", Focus = "racquet_drop", Stroke = "forehand", Equipment = "basket", DefaultReps = 25, Instructions = "Self-feeds. Pause at the racquet drop / slot before accelerating." },
            new Drill { Name = "Contact out-front cones", Focus = "contact", Stroke = "forehand", Equipment = "basket", DefaultReps = 30, Instructions = "Place a cone as a contact marker; meet every ball at the cone." },
            new Drill { Name = "Extension finish holds", Focus = "extension", Stroke = "forehand", Equipment = "basket", DefaultReps = 20, Instructions = "Hit and hold the extension pose for 2 seconds toward the target." },
            new Drill { Name = "Over-shoulder finishes", Focus = "finish", Stroke = "forehand", Equipment = "basket", DefaultReps = 25, Instructions = "Exaggerate a high finish over the opposite shoulder." },
            new Drill { Name = "Split-step recovery ladders", Focus = "footwork", Stroke = "any", Equipment = "ladder", DefaultReps = 12, Instructions = "Split-step, wide recovery shuffle, reset. 12 repetitions each side." },
            new Drill { Name = "Serve trophy coil", Focus = "unit_turn", Stroke = "serve", Equipment = "basket", DefaultReps = 20, Instructions = "Pause in the trophy pose, check coil, then finish the serve." },
            new Drill { Name = "Band stretch + breathing", Focus = "cooldown", Stroke = "any", Equipment = "band", DefaultReps = 1, Instructions = "Shoulder and hip flexor stretches, 3 minutes of nasal breathing." }
        );
        await db.SaveChangesAsync();
    }
}
