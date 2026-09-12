<?php

namespace App\Models;

use App\Enums\ConsentStatus;
use App\Enums\PartyRole;
use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class Party extends Model
{
    use HasUuid;

    protected $fillable = [
        'case_id', 'role', 'display_name', 'contact_reference',
        'consent_status', 'consent_recorded_at',
    ];

    protected function casts(): array
    {
        return [
            'role' => PartyRole::class,
            'consent_status' => ConsentStatus::class,
            'consent_recorded_at' => 'datetime',
        ];
    }

    public function mediationCase(): BelongsTo
    {
        return $this->belongsTo(MediationCase::class, 'case_id');
    }

    public function recordings(): HasMany
    {
        return $this->hasMany(AudioRecording::class, 'party_id');
    }

    public function claims(): HasMany
    {
        return $this->hasMany(Claim::class, 'party_id');
    }

    public function hasConsent(): bool
    {
        return $this->consent_status === ConsentStatus::GRANTED;
    }
}
