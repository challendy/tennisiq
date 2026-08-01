using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using TennisIQ.Domain;
using TennisIQ.Infrastructure.Cv;
using TennisIQ.Infrastructure.Persistence;

namespace TennisIQ.Api.Workers;

public sealed class AnalysisWorker(
    IServiceScopeFactory scopeFactory,
    ILogger<AnalysisWorker> logger) : BackgroundService
{
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        logger.LogInformation("AnalysisWorker started");
        while (!stoppingToken.IsCancellationRequested)
        {
            try
            {
                var processed = await ProcessOneAsync(stoppingToken);
                if (!processed)
                    await Task.Delay(1000, stoppingToken);
            }
            catch (OperationCanceledException) when (stoppingToken.IsCancellationRequested)
            {
                break;
            }
            catch (Exception ex)
            {
                logger.LogError(ex, "Worker loop error");
                await Task.Delay(2000, stoppingToken);
            }
        }
    }

    private async Task<bool> ProcessOneAsync(CancellationToken ct)
    {
        await using var scope = scopeFactory.CreateAsyncScope();
        var queue = scope.ServiceProvider.GetRequiredService<IAnalysisJobQueue>();
        var storage = scope.ServiceProvider.GetRequiredService<IVideoStorage>();
        var client = scope.ServiceProvider.GetRequiredService<AnalysisServiceClient>();
        var narrator = scope.ServiceProvider.GetRequiredService<ICoachNarrator>();
        var db = scope.ServiceProvider.GetRequiredService<AppDbContext>();

        var job = await queue.ClaimNextAsync(ct);
        if (job is null)
            return false;

        try
        {
            await using var stream = await storage.OpenReadAsync(job.Video.StorageKey, ct);
            var result = await client.AnalyzeAsync(
                stream,
                Path.GetFileName(job.Video.StorageKey),
                job.Video.Stroke,
                job.Video.Handedness,
                ct);

            string? overlayKey = null;
            if (result.OverlayBytes is { Length: > 0 })
            {
                await using var overlayStream = new MemoryStream(result.OverlayBytes);
                overlayKey = await storage.SaveOverlayAsync(overlayStream, $"{job.VideoId:N}.mp4", ct);
            }

            // Multi-hit: replace the stored basket with the kept single-stroke cut.
            if (result.ClipBytes is { Length: > 0 })
            {
                await using var clipStream = new MemoryStream(result.ClipBytes);
                await storage.ReplaceAsync(job.Video.StorageKey, clipStream, ct);
            }

            var analysis = new Analysis
            {
                UserId = job.Video.UserId,
                VideoId = job.VideoId,
                Stroke = result.Stroke,
                Status = result.Status,
                OverallScore = result.OverallScore,
                Grade = result.Grade,
                Confidence = result.Confidence,
                TopFix = result.TopFix,
                ResultJson = JsonSerializer.Serialize(result),
                OverlayKey = overlayKey,
                PhaseScores = result.Phases.Select(p => new PhaseScoreEntity
                {
                    Phase = p.Name,
                    Score = p.Score,
                    Feedback = p.Feedback,
                }).ToList(),
            };

            // Only count quota for successful usable analyses.
            if (result.Status == "ok")
            {
                var sub = await db.Subscriptions.FirstAsync(s => s.UserId == job.Video.UserId, ct);
                Quota.RecordAnalysis(sub, DateTime.UtcNow);
            }

            analysis.CoachingScript = await narrator.NarrateAsync(analysis, ct);
            db.Analyses.Add(analysis);
            await db.SaveChangesAsync(ct);
            await queue.CompleteAsync(job, ct);
            logger.LogInformation("Job {JobId} succeeded ({Status})", job.Id, result.Status);
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "Job {JobId} failed attempt {Attempt}", job.Id, job.Attempts);
            await queue.FailAsync(job, ex.Message, retryable: true, ct);
        }

        return true;
    }
}
