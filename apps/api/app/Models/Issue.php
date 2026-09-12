<?php

namespace App\Models;

use App\Enums\Criticality;
use App\Enums\IssueStatus;
use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Issue extends Model
{
    use HasUuid;

    protected $fillable = [
        'case_id', 'canonical_type', 'status', 'criticality', 'summary',
        'classification_reason', 'party_a_value', 'party_b_value',
        'comparison_confidence', 'mediator_overridden',
    ];

    protected function casts(): array
    {
        return [
            'status' => IssueStatus::class,
            'criticality' => Criticality::class,
            'party_a_value' => 'array',
            'party_b_value' => 'array',
            'mediator_overridden' => 'boolean',
        ];
    }

    public function mediationCase(): BelongsTo
    {
        return $this->belongsTo(MediationCase::class, 'case_id');
    }

    public function issueClaims(): HasMany
    {
        return $this->hasMany(IssueClaim::class, 'issue_id');
    }

    public function evidenceReferences(): HasMany
    {
        return $this->hasMany(EvidenceReference::class, 'issue_id');
    }

    public function isCritical(): bool
    {
        return in_array($this->canonical_type, config('wunzi.critical_issue_types', []), true);
    }
}
