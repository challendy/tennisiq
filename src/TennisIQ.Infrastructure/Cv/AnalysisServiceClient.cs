using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace TennisIQ.Infrastructure.Cv;

public sealed class AnalysisServiceClient(HttpClient http)
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        PropertyNameCaseInsensitive = true,
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    };

    public async Task<AnalysisServiceResponse> AnalyzeAsync(
        Stream videoStream,
        string fileName,
        string stroke,
        string handedness,
        CancellationToken ct = default)
    {
        using var form = new MultipartFormDataContent();
        var streamContent = new StreamContent(videoStream);
        streamContent.Headers.ContentType = new MediaTypeHeaderValue("video/mp4");
        form.Add(streamContent, "video", fileName);
        form.Add(new StringContent(stroke), "stroke");
        form.Add(new StringContent(handedness), "handedness");
        form.Add(new StringContent("side"), "view");
        form.Add(new StringContent("true"), "allow_synthetic_fallback");

        using var response = await http.PostAsync("/analyze", form, ct);
        var body = await response.Content.ReadAsStringAsync(ct);
        if (!response.IsSuccessStatusCode)
            throw new InvalidOperationException($"Analysis service error {(int)response.StatusCode}: {body}");

        var parsed = JsonSerializer.Deserialize<AnalysisServiceResponse>(body, JsonOptions)
            ?? throw new InvalidOperationException("Empty analysis response");

        if (parsed.OverlayReady && !string.IsNullOrEmpty(parsed.OverlayToken))
        {
            using var overlayResp = await http.GetAsync($"/overlay/{parsed.OverlayToken}", ct);
            overlayResp.EnsureSuccessStatusCode();
            parsed.OverlayBytes = await overlayResp.Content.ReadAsByteArrayAsync(ct);
        }

        return parsed;
    }
}

public sealed class AnalysisServiceResponse
{
    public string Stroke { get; set; } = "";
    public string Status { get; set; } = "ok";
    public double OverallScore { get; set; }
    public string Grade { get; set; } = "";
    public double Confidence { get; set; }
    public List<string> Strengths { get; set; } = [];
    public List<string> Weaknesses { get; set; } = [];
    public string TopFix { get; set; } = "";
    public List<PhaseDto> Phases { get; set; } = [];
    public Dictionary<string, double> Metrics { get; set; } = new();
    public List<QualityIssueDto> QualityIssues { get; set; } = [];
    public bool ContactEstimated { get; set; } = true;
    public int FrameCount { get; set; }
    public double Fps { get; set; }
    public bool OverlayReady { get; set; }
    public string? OverlayToken { get; set; }

    [JsonIgnore]
    public byte[]? OverlayBytes { get; set; }
}

public sealed class PhaseDto
{
    public string Name { get; set; } = "";
    public double Score { get; set; }

    /// How much this phase contributes to the overall grade for its stroke.
    public double Weight { get; set; } = 1;
    public string Feedback { get; set; } = "";
    public string IdealComparison { get; set; } = "";
    public List<string> Observations { get; set; } = [];
}

public sealed class QualityIssueDto
{
    public string Code { get; set; } = "";
    public string Message { get; set; } = "";
    public string Tip { get; set; } = "";
}
