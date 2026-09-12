<?php

namespace App\Services\Audio;

use App\Models\AudioRecording;
use App\Models\Party;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class AudioStorage
{
    public function disk(): string
    {
        return (string) config('wunzi.audio.disk', 's3');
    }

    /** Stores an uploaded recording in a private bucket and returns its metadata. */
    public function store(Party $party, UploadedFile $file, ?int $durationMs = null): array
    {
        $audioId = (string) Str::uuid();
        $extension = $file->getClientOriginalExtension() ?: $this->extensionFor($file->getMimeType());

        $path = strtr(config('wunzi.audio.path_template'), [
            '{case}' => $party->case_id,
            '{party}' => $party->id,
            '{audio}' => $audioId,
            '{ext}' => $extension,
        ]);

        Storage::disk($this->disk())->put($path, file_get_contents($file->getRealPath()), 'private');

        return [
            'id' => $audioId,
            'storage_path' => $path,
            'mime_type' => $file->getMimeType() ?: 'application/octet-stream',
            'size_bytes' => $file->getSize(),
            'sha256' => hash_file('sha256', $file->getRealPath()),
            'duration_ms' => $durationMs,
        ];
    }

    /** Time-limited signed URL. Buckets stay private; no public objects. */
    public function signedUrl(AudioRecording $recording, ?int $ttlMinutes = null): string
    {
        $ttl = $ttlMinutes ?? (int) config('wunzi.audio.signed_url_ttl_minutes', 10);
        $disk = Storage::disk($recording->disk ?: $this->disk());

        if (method_exists($disk, 'temporaryUrl')) {
            try {
                return $disk->temporaryUrl($recording->storage_path, now()->addMinutes($ttl));
            } catch (\Throwable) {
                // local driver fallback below
            }
        }

        return route('api.recordings.stream', ['recording' => $recording->id]);
    }

    /** URI handed to the intelligence service (it re-reads the object itself). */
    public function readableUri(AudioRecording $recording): string
    {
        if ($recording->disk === 'fixtures' || config('wunzi.mode') === 'fixture') {
            return 'fixture://'.($recording->fixture_key ?: $recording->storage_path);
        }

        return 's3://'.config('filesystems.disks.s3.bucket').'/'.$recording->storage_path;
    }

    public function delete(AudioRecording $recording): void
    {
        Storage::disk($recording->disk ?: $this->disk())->delete($recording->storage_path);
    }

    private function extensionFor(?string $mime): string
    {
        return match ($mime) {
            'audio/webm' => 'webm',
            'audio/ogg' => 'ogg',
            'audio/wav', 'audio/x-wav' => 'wav',
            'audio/mpeg' => 'mp3',
            'audio/mp4' => 'm4a',
            'audio/flac' => 'flac',
            default => 'bin',
        };
    }
}
