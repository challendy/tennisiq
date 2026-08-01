using TennisIQ.Domain;

namespace TennisIQ.Infrastructure.Storage;

public sealed class LocalVideoStorage : IVideoStorage
{
    private readonly string _root;

    public LocalVideoStorage(string rootDirectory)
    {
        _root = Path.GetFullPath(rootDirectory);
        Directory.CreateDirectory(Path.Combine(_root, "videos"));
        Directory.CreateDirectory(Path.Combine(_root, "overlays"));
    }

    public async Task<string> SaveAsync(Stream content, string fileName, CancellationToken ct = default)
    {
        var key = $"videos/{Guid.NewGuid():N}{Path.GetExtension(fileName)}";
        var path = GetAbsolutePath(key);
        await using var fs = File.Create(path);
        await content.CopyToAsync(fs, ct);
        return key;
    }

    public Task<Stream> OpenReadAsync(string storageKey, CancellationToken ct = default)
    {
        Stream stream = File.OpenRead(GetAbsolutePath(storageKey));
        return Task.FromResult(stream);
    }

    public async Task<string> SaveOverlayAsync(Stream content, string preferredName, CancellationToken ct = default)
    {
        var key = $"overlays/{preferredName}";
        var path = GetAbsolutePath(key);
        await using var fs = File.Create(path);
        await content.CopyToAsync(fs, ct);
        return key;
    }

    public async Task ReplaceAsync(string storageKey, Stream content, CancellationToken ct = default)
    {
        var path = GetAbsolutePath(storageKey);
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        await using var fs = File.Create(path);
        await content.CopyToAsync(fs, ct);
    }

    public string GetAbsolutePath(string storageKey)
    {
        var full = Path.GetFullPath(Path.Combine(_root, storageKey));
        if (!full.StartsWith(_root, StringComparison.Ordinal))
            throw new InvalidOperationException("Invalid storage key");
        return full;
    }
}
