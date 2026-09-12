<?php

namespace App\Models;

use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ClaimSource extends Model
{
    use HasUuid;

    protected $fillable = ['claim_id', 'transcript_segment_id', 'start_offset_ms', 'end_offset_ms'];

    public function claim(): BelongsTo
    {
        return $this->belongsTo(Claim::class, 'claim_id');
    }

    public function segment(): BelongsTo
    {
        return $this->belongsTo(TranscriptSegment::class, 'transcript_segment_id');
    }
}
