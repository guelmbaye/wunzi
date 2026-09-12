<?php

namespace App\Models;

use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class TranscriptSegment extends Model
{
    use HasUuid;

    protected $fillable = [
        'transcript_run_id', 'sequence', 'start_ms', 'end_ms',
        'text', 'language_code', 'confidence',
    ];

    protected function casts(): array
    {
        return ['confidence' => 'float'];
    }

    public function transcriptRun(): BelongsTo
    {
        return $this->belongsTo(TranscriptRun::class, 'transcript_run_id');
    }

    public function claimSources(): HasMany
    {
        return $this->hasMany(ClaimSource::class, 'transcript_segment_id');
    }
}
