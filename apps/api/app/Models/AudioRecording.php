<?php

namespace App\Models;

use App\Enums\ProcessingStatus;
use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class AudioRecording extends Model
{
    use HasUuid;

    protected $fillable = [
        'case_id', 'party_id', 'disk', 'storage_path', 'duration_ms', 'mime_type',
        'size_bytes', 'sha256', 'consent_recorded', 'processing_status',
        'failure_reason', 'fixture_key',
    ];

    protected function casts(): array
    {
        return [
            'processing_status' => ProcessingStatus::class,
            'consent_recorded' => 'boolean',
        ];
    }

    public function mediationCase(): BelongsTo
    {
        return $this->belongsTo(MediationCase::class, 'case_id');
    }

    public function party(): BelongsTo
    {
        return $this->belongsTo(Party::class, 'party_id');
    }

    public function transcriptRuns(): HasMany
    {
        return $this->hasMany(TranscriptRun::class, 'audio_id');
    }

    public function primaryTranscriptRun(): ?TranscriptRun
    {
        return $this->transcriptRuns()->where('is_primary', true)->latest()->first();
    }

    public function markStatus(ProcessingStatus $status, ?string $reason = null): void
    {
        $this->update(['processing_status' => $status, 'failure_reason' => $reason]);
    }
}
