using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using TennisIQ.Api.Auth;
using TennisIQ.Domain;
using TennisIQ.Infrastructure.Persistence;

namespace TennisIQ.Api.Controllers;

public record RegisterRequest(string Email, string Password, string DisplayName, string Handedness = "right");
public record LoginRequest(string Email, string Password);
public record AuthResponse(string Token, Guid UserId, string Email, string DisplayName, string Plan, bool IsAdmin);

[ApiController]
[Route("api/auth")]
public sealed class AuthController(AppDbContext db, JwtTokenService jwt, IConfiguration config) : ControllerBase
{
    private readonly PasswordHasher<User> _hasher = new();

    [HttpPost("register")]
    public async Task<ActionResult<AuthResponse>> Register(RegisterRequest req, CancellationToken ct)
    {
        var email = req.Email.Trim().ToLowerInvariant();
        if (string.IsNullOrWhiteSpace(email) || string.IsNullOrWhiteSpace(req.Password) || req.Password.Length < 8)
            return BadRequest(new { error = "Email and password (8+ chars) required." });

        if (await db.Users.AnyAsync(u => u.Email == email, ct))
            return Conflict(new { error = "Email already registered." });

        var user = new User
        {
            Email = email,
            DisplayName = string.IsNullOrWhiteSpace(req.DisplayName) ? email.Split('@')[0] : req.DisplayName.Trim(),
            Handedness = req.Handedness is "left" or "right" ? req.Handedness : "right",
            IsAdmin = IsBootstrapEmail(email),
            Subscription = new Subscription(),
        };
        user.PasswordHash = _hasher.HashPassword(user, req.Password);
        db.Users.Add(user);
        await db.SaveChangesAsync(ct);
        return Ok(ToAuth(user));
    }

    [HttpPost("login")]
    public async Task<ActionResult<AuthResponse>> Login(LoginRequest req, CancellationToken ct)
    {
        var email = req.Email.Trim().ToLowerInvariant();
        var user = await db.Users.Include(u => u.Subscription).FirstOrDefaultAsync(u => u.Email == email, ct);
        if (user is null)
            return Unauthorized(new { error = "Invalid credentials." });

        var result = _hasher.VerifyHashedPassword(user, user.PasswordHash, req.Password);
        if (result == PasswordVerificationResult.Failed)
            return Unauthorized(new { error = "Invalid credentials." });

        return Ok(ToAuth(user));
    }

    [Authorize]
    [HttpGet("me")]
    public async Task<ActionResult<object>> Me(CancellationToken ct)
    {
        var userId = UserId();
        var user = await db.Users.Include(u => u.Subscription).FirstAsync(u => u.Id == userId, ct);
        Quota.EnsurePeriod(user.Subscription, DateTime.UtcNow);
        await db.SaveChangesAsync(ct);
        return Ok(new
        {
            user.Id,
            user.Email,
            user.DisplayName,
            user.Handedness,
            plan = user.Subscription.Plan.ToString(),
            analysesUsed = user.Subscription.AnalysesUsed,
            analysesLimit = user.Subscription.Plan == PlanType.Premium ? (int?)null : Quota.FreeMonthlyLimit,
            periodStart = user.Subscription.PeriodStart,
            isAdmin = user.IsAdmin,
        });
    }

    private bool IsBootstrapEmail(string email)
    {
        var bootstrap = BootstrapEmail();
        return !string.IsNullOrWhiteSpace(bootstrap)
               && string.Equals(bootstrap, email, StringComparison.OrdinalIgnoreCase);
    }

    private string? BootstrapEmail() =>
        config["Admin:BootstrapEmail"]
        ?? Environment.GetEnvironmentVariable("TENNISIQ_BOOTSTRAP_ADMIN_EMAIL");

    private AuthResponse ToAuth(User user) =>
        new(jwt.CreateToken(user), user.Id, user.Email, user.DisplayName, user.Subscription.Plan.ToString(), user.IsAdmin);

    private Guid UserId() => Guid.Parse(User.FindFirstValue(ClaimTypes.NameIdentifier)
        ?? User.FindFirstValue("sub")!);
}
