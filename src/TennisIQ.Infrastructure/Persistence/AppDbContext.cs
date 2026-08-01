using Microsoft.EntityFrameworkCore;
using TennisIQ.Domain;

namespace TennisIQ.Infrastructure.Persistence;

public class AppDbContext(DbContextOptions<AppDbContext> options) : DbContext(options)
{
    public DbSet<User> Users => Set<User>();
    public DbSet<Subscription> Subscriptions => Set<Subscription>();
    public DbSet<Video> Videos => Set<Video>();
    public DbSet<AnalysisJob> AnalysisJobs => Set<AnalysisJob>();
    public DbSet<Analysis> Analyses => Set<Analysis>();
    public DbSet<PhaseScoreEntity> PhaseScores => Set<PhaseScoreEntity>();
    public DbSet<PracticePlan> PracticePlans => Set<PracticePlan>();
    public DbSet<Drill> Drills => Set<Drill>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<User>(e =>
        {
            e.HasIndex(x => x.Email).IsUnique();
            e.Property(x => x.Email).HasMaxLength(320);
            e.HasOne(x => x.Subscription).WithOne(x => x.User).HasForeignKey<Subscription>(x => x.UserId);
        });

        modelBuilder.Entity<Video>(e =>
        {
            e.HasOne(x => x.Job).WithOne(x => x.Video).HasForeignKey<AnalysisJob>(x => x.VideoId);
            e.HasOne(x => x.Analysis).WithOne(x => x.Video).HasForeignKey<Analysis>(x => x.VideoId);
        });

        modelBuilder.Entity<Analysis>(e =>
        {
            e.Property(x => x.ResultJson).HasColumnType("jsonb");
            e.HasMany(x => x.PhaseScores).WithOne(x => x.Analysis).HasForeignKey(x => x.AnalysisId);
            e.HasIndex(x => new { x.UserId, x.Stroke, x.CreatedAt });
        });

        modelBuilder.Entity<AnalysisJob>(e =>
        {
            e.HasIndex(x => new { x.Status, x.CreatedAt });
        });

        modelBuilder.Entity<PracticePlan>(e =>
        {
            e.Property(x => x.ItemsJson).HasColumnType("jsonb");
        });

        modelBuilder.Entity<Drill>(e =>
        {
            e.HasIndex(x => new { x.Stroke, x.Focus });
        });
    }
}
