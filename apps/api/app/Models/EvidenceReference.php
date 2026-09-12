<?php

namespace App\Models;

use App\Enums\EvidenceAvailability;
use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class EvidenceReference extends Model
{
    use HasUuid;

    protected $fillable = ['case_id', 'issue_id', 'party_id', 'type', 'description', 'availability'];

    protected function casts(): array
    {
        return ['availability' => EvidenceAvailability::class];
    }

    public function mediationCase(): BelongsTo
    {
        return $this->belongsTo(MediationCase::class, 'case_id');
    }

    public function issue(): BelongsTo
    {
        return $this->belongsTo(Issue::class, 'issue_id');
    }

    public function party(): BelongsTo
    {
        return $this->belongsTo(Party::class, 'party_id');
    }
}
