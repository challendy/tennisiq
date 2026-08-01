using System.Security.Claims;
using System.Text;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using TennisIQ.Api.Auth;
using TennisIQ.Api.Workers;
using TennisIQ.Domain;
using TennisIQ.Infrastructure.Cv;
using TennisIQ.Infrastructure.Jobs;
using TennisIQ.Infrastructure.Persistence;
using TennisIQ.Infrastructure.Storage;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();
builder.Services.AddCors(o => o.AddDefaultPolicy(p =>
    p.AllowAnyHeader().AllowAnyMethod().AllowAnyOrigin()));

var conn = builder.Configuration.GetConnectionString("Default")
    ?? "Host=localhost;Database=tennisiq;Username=chrishallendy;Password=";

builder.Services.AddDbContext<AppDbContext>(opt => opt.UseNpgsql(conn));

var configuredStorage = builder.Configuration["Storage:Root"];
var storageRoot = string.IsNullOrWhiteSpace(configuredStorage)
    ? Path.GetFullPath(Path.Combine(builder.Environment.ContentRootPath, "..", "..", "storage"))
    : Path.GetFullPath(configuredStorage);
builder.Services.AddSingleton<IVideoStorage>(_ => new LocalVideoStorage(storageRoot));
builder.Services.AddScoped<IAnalysisJobQueue, PostgresAnalysisJobQueue>();
builder.Services.AddSingleton<ICoachNarrator, RuleBasedCoachNarrator>();
builder.Services.AddSingleton<IPracticePlanner, PracticePlanner>();
builder.Services.AddSingleton<JwtTokenService>();

var analysisBase = builder.Configuration["Analysis:BaseUrl"] ?? "http://localhost:8090";
builder.Services.AddHttpClient<AnalysisServiceClient>(c =>
{
    c.BaseAddress = new Uri(analysisBase);
    c.Timeout = TimeSpan.FromMinutes(3);
});

var jwtKey = builder.Configuration["Jwt:Key"] ?? "tennisiq-dev-key-change-me-32chars!!";
builder.Services.AddAuthentication(JwtBearerDefaults.AuthenticationScheme)
    .AddJwtBearer(o =>
    {
        o.TokenValidationParameters = new TokenValidationParameters
        {
            ValidateIssuer = true,
            ValidateAudience = true,
            ValidateIssuerSigningKey = true,
            ValidIssuer = builder.Configuration["Jwt:Issuer"] ?? "tennisiq",
            ValidAudience = builder.Configuration["Jwt:Audience"] ?? "tennisiq",
            IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey)),
            NameClaimType = "sub",
        };
    });
builder.Services.AddAuthorization(o =>
{
    o.AddPolicy("AdminOnly", p =>
        p.RequireAuthenticatedUser()
            .RequireClaim(JwtTokenService.AdminClaim, "true"));
});
builder.Services.AddHostedService<AnalysisWorker>();

var app = builder.Build();

using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    await db.Database.EnsureCreatedAsync();
    // EnsureCreated does not alter existing tables — add IsAdmin for upgraded DBs.
    await db.Database.ExecuteSqlRawAsync(
        """ALTER TABLE "Users" ADD COLUMN IF NOT EXISTS "IsAdmin" boolean NOT NULL DEFAULT false;""");
    await SeedData.EnsureSeededAsync(db);
    await BootstrapAdminAsync(db, app.Configuration, app.Logger);
}

app.UseCors();
app.UseAuthentication();
app.UseAuthorization();
app.MapControllers();
app.MapGet("/health", () => Results.Ok(new { status = "ok" }));

app.Run();

static async Task BootstrapAdminAsync(AppDbContext db, IConfiguration config, ILogger logger)
{
    var email = (config["Admin:BootstrapEmail"]
                 ?? Environment.GetEnvironmentVariable("TENNISIQ_BOOTSTRAP_ADMIN_EMAIL")
                 ?? "").Trim().ToLowerInvariant();
    if (string.IsNullOrWhiteSpace(email))
        return;

    var user = await db.Users.FirstOrDefaultAsync(u => u.Email == email);
    if (user is null || user.IsAdmin)
        return;

    user.IsAdmin = true;
    await db.SaveChangesAsync();
    logger.LogInformation("Bootstrapped admin flag for {Email}", email);
}

public partial class Program;
