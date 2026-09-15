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
    /**
     * The neutral sentence a mediator reads.
     *
     * An explicit phrase table rather than string assembly. The extractor emits
     * predicates already conjugated (`states_deposit_amount`, `caused_damage`),
     * so gluing "states" and "did not" in front produced "states states deposit
     * amount" and "did not caused damage" — ungrammatical text on the most-read
     * surface of a legal tool.
     *
     * A table is also safer than a conjugator: negation is where a mediation
     * turns, and "is responsible" negates to "is not responsible", not to
     * "did not is responsible". Every phrase here is written once and reviewed.
     */
    private const PHRASES = [
        //                             positive                          negative                                impersonal                                    self (speaker is the subject)
        'paid_deposit'           => ['paid the deposit',              'did not pay the deposit',              'a deposit was paid',                         null],
        'states_deposit_amount'  => ['stated the deposit amount',     'disputed the deposit amount',          'a deposit amount was stated',                'states the deposit amount'],
        'caused_damage'          => ['caused damage to the property', 'did not cause damage to the property', 'damage to the property occurred',            null],
        'bears_responsibility'   => ['was responsible for the damage','was not responsible for the damage',   'responsibility for the damage was asserted', null],
        'promised_refund'        => ['promised a full refund',        'did not promise a full refund',        'a full refund was promised',                 null],
        'states_move_out_date'   => ['gave the tenancy end date as',  'disputed the tenancy end date',        'a tenancy end date was stated',              'gives the tenancy end date as'],
        'states_payment_date'    => ['gave the payment date as',      'disputed the payment date',            'a payment date was stated',                  'gives the payment date as'],
        'claims_repair_cost'     => ['stated the repair cost',        'disputed the repair cost',             'a repair cost was stated',                   'states the repair cost'],
        'mentions_evidence'      => ['referred to evidence',          'had no evidence to refer to',          'evidence was referred to',                   'refers to evidence'],
        'requests_outcome'       => ['requested an outcome',          'requested no outcome',                 'an outcome was requested',                   'requests an outcome'],
        'requests_refund_amount' => ['requested a refund amount',     'requested no refund',                  'a refund was requested',                     'requests a refund amount'],
    ];

    public function neutralStatement(): string
    {
        $speaker = $this->party?->role?->value === 'PARTY_A' ? 'Party A' : 'Party B';

        $subject = match ($this->subject_ref) {
            'party_a' => 'Party A',
            'party_b' => 'Party B',
            null, '' => null,
            default => 'a third person',
        };

        $negative = $this->polarity === Polarity::NEGATIVE;
        $phrases = self::PHRASES[$this->predicate] ?? null;

        if ($phrases === null) {
            // An unknown predicate is rendered plainly rather than guessed at.
            // Losing the attribution would be worse than an awkward sentence.
            $fallback = str_replace('_', ' ', $this->predicate);

            return $subject === null
                ? sprintf('%s states: %s.', $speaker, $fallback)
                : sprintf('%s states that %s: %s.', $speaker, $subject, $fallback);
        }

        [$positive, $negated, $impersonal, $self] = $phrases;

        // No subject means an existential statement — "there was damage to the
        // wall". Naming a person there would invent an accusation.
        if ($subject === null) {
            return sprintf(
                '%s states that %s%s.',
                $speaker,
                $negative ? 'no ' : '',
                $impersonal
            );
        }

        // Some predicates are themselves speech acts, so reporting them through
        // "states that" doubles the verb: "Party A states that Party A stated
        // the deposit amount". Those carry a direct form used when the speaker
        // is also the subject.
        if ($self !== null && $subject === $speaker && ! $negative) {
            return sprintf('%s %s.', $speaker, $self);
        }

        // Otherwise the party is named, even when it repeats the speaker.
        // "states that they…" would need plural agreement ("they were") while a
        // named party needs singular ("Party B was"), and one table cannot serve
        // both. Repeating the name is also how a case file avoids ambiguity.
        return sprintf(
            '%s states that %s %s.',
            $speaker,
            $subject,
            $negative ? $negated : $positive
        );
    }

}
