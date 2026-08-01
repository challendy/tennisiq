namespace TennisIQ.Domain;

public enum PlanType
{
    Free = 0,
    Premium = 1
}

public enum JobStatus
{
    Pending = 0,
    Running = 1,
    Succeeded = 2,
    Failed = 3
}

public class User
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Email { get; set; } = "";
    public string PasswordHash { get; set; } = "";
    public string DisplayName { get; set; } = "";
    public string Handedness { get; set; } = "right";
    public bool IsAdmin { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public Subscription Subscription { get; set; } = null!;
    public List<Video> Videos { get; set; } = [];
    public List<Analysis> Analyses { get; set; } = [];
    public List<PracticePlan> PracticePlans { get; set; } = [];
}

public class Subscription
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid UserId { get; set; }
    public User User { get; set; } = null!;
    public PlanType Plan { get; set; } = PlanType.Free;
    public DateTime PeriodStart { get; set; } = new(DateTime.UtcNow.Year, DateTime.UtcNow.Month, 1, 0, 0, 0, DateTimeKind.Utc);
    public int AnalysesUsed { get; set; }
}

public class Video
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid UserId { get; set; }
    public User User { get; set; } = null!;
    public string StorageKey { get; set; } = "";
    public string Stroke { get; set; } = "forehand";
    public string Handedness { get; set; } = "right";
    public string? OriginalFileName { get; set; }
    public long SizeBytes { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public AnalysisJob? Job { get; set; }
    public Analysis? Analysis { get; set; }
}

public class AnalysisJob
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid VideoId { get; set; }
    public Video Video { get; set; } = null!;
    public JobStatus Status { get; set; } = JobStatus.Pending;
    public int Attempts { get; set; }
    public string? Error { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public DateTime? ClaimedAt { get; set; }
    public DateTime? CompletedAt { get; set; }
}

public class Analysis
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid UserId { get; set; }
    public User User { get; set; } = null!;
    public Guid VideoId { get; set; }
    public Video Video { get; set; } = null!;
    public string Stroke { get; set; } = "forehand";
    public string Status { get; set; } = "ok";
    public double OverallScore { get; set; }
    public string Grade { get; set; } = "";
    public double Confidence { get; set; }
    public string TopFix { get; set; } = "";
    public string CoachingScript { get; set; } = "";
    public string ResultJson { get; set; } = "{}";
    public string? OverlayKey { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
    public List<PhaseScoreEntity> PhaseScores { get; set; } = [];
}

public class PhaseScoreEntity
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid AnalysisId { get; set; }
    public Analysis Analysis { get; set; } = null!;
    public string Phase { get; set; } = "";
    public double Score { get; set; }
    public string Feedback { get; set; } = "";
}

public class PracticePlan
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public Guid UserId { get; set; }
    public User User { get; set; } = null!;
    public Guid? GeneratedFromAnalysisId { get; set; }
    public string Goal { get; set; } = "";
    public string ItemsJson { get; set; } = "[]";
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}

public class Drill
{
    public Guid Id { get; set; } = Guid.NewGuid();
    public string Name { get; set; } = "";
    public string Focus { get; set; } = "";
    public string Stroke { get; set; } = "forehand";
    public string Equipment { get; set; } = "basket";
    public string Instructions { get; set; } = "";
    public int DefaultReps { get; set; } = 20;
}
