<?php

namespace App\Models;

use App\Enums\Criticality;
use App\Enums\Polarity;
use App\Enums\VerificationStatus;
use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Builder;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Claim extends Model
{
    use HasUuid;

    protected $fillable = [
        'case_id', 'party_id', 'transcript_run_id', 'type', 'subject_ref', 'predicate',
        'canonical_value', 'polarity', 'certainty', 'criticality', 'verification_status',
        'extraction_confidence', 'attribution_confidence', 'reported_speech',
        'superseded_by', 'is_superseded', 'extraction_version', 'mediator_corrected',
    ];

    protected function casts(): array
    {
        return [
            'canonical_value' => 'array',
            'polarity' => Polarity::class,
            'criticality' => Criticality::class,
            'verification_status' => VerificationStatus::class,
            'reported_speech' => 'boolean',
            'is_superseded' => 'boolean',
            'mediator_corrected' => 'boolean',
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

    public function sources(): HasMany
    {
        return $this->hasMany(ClaimSource::class, 'claim_id');
    }

    public function criticalFields(): HasMany
    {
        return $this->hasMany(CriticalField::class, 'claim_id');
    }

    public function issueLinks(): HasMany
    {
        return $this->hasMany(IssueClaim::class, 'claim_id');
    }

    public function scopeCurrent(Builder $query): Builder
    {
        return $query->where('is_superseded', false);
    }

    public function scopeCritical(Builder $query): Builder
    {
        return $query->where('criticality', Criticality::HIGH->value);
    }

    /**
     * Neutral rendering. A claim is always attributed, never asserted as fact.
     * "Party A states that Party B promised a full refund."
     */
    public function neutralStatement(): string
    {
        $speaker = $this->party?->role?->value === 'PARTY_A' ? 'Party A' : 'Party B';
        $subject = match ($this->subject_ref) {
            'party_a' => 'Party A',
            'party_b' => 'Party B',
            null, '' => null,
            default => 'a third person',
        };

        $negated = $this->polarity === Polarity::NEGATIVE ? ' did not ' : ' ';
        $predicate = str_replace('_', ' ', $this->predicate);

        if ($this->reported_speech && $subject !== null) {
            return sprintf('%s states that %s%s%s.', $speaker, $subject, $negated, $predicate);
        }

        return sprintf('%s states%s%s.', $speaker, $negated, $predicate);
    }
}
