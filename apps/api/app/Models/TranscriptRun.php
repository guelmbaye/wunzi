<?php

namespace App\Models;

use App\Enums\AsrProvider;
use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

/** Immutable record of one ASR execution. Never updated in place. */
class TranscriptRun extends Model
{
    use HasUuid;

    protected $fillable = [
        'audio_id', 'provider', 'model', 'provider_version', 'status',
        'raw_payload', 'normalized_transcript', 'latency_ms',
        'idempotency_key', 'source_mode', 'fixture_origin', 'is_primary',
    ];

    protected function casts(): array
    {
        return [
            'provider' => AsrProvider::class,
            'raw_payload' => 'array',
            'is_primary' => 'boolean',
        ];
    }

    public function audio(): BelongsTo
    {
        return $this->belongsTo(AudioRecording::class, 'audio_id');
    }

    public function segments(): HasMany
    {
        return $this->hasMany(TranscriptSegment::class, 'transcript_run_id')->orderBy('sequence');
    }

    public function claims(): HasMany
    {
        return $this->hasMany(Claim::class, 'transcript_run_id');
    }
}
