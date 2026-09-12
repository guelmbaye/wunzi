<?php

namespace App\Models;

use App\Enums\CaseStatus;
use App\Enums\PartyRole;
use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\Relations\HasManyThrough;
use Illuminate\Database\Eloquent\SoftDeletes;

class MediationCase extends Model
{
    use HasUuid, SoftDeletes;

    protected $fillable = [
        'public_reference', 'category', 'status', 'title',
        'language_configuration', 'created_by', 'pipeline_version',
    ];

    protected function casts(): array
    {
        return ['status' => CaseStatus::class];
    }

    public function creator(): BelongsTo
    {
        return $this->belongsTo(User::class, 'created_by');
    }

    public function parties(): HasMany
    {
        return $this->hasMany(Party::class, 'case_id');
    }

    public function recordings(): HasMany
    {
        return $this->hasMany(AudioRecording::class, 'case_id');
    }

    public function claims(): HasMany
    {
        return $this->hasMany(Claim::class, 'case_id');
    }

    public function issues(): HasMany
    {
        return $this->hasMany(Issue::class, 'case_id');
    }

    public function evidenceReferences(): HasMany
    {
        return $this->hasMany(EvidenceReference::class, 'case_id');
    }

    public function packets(): HasMany
    {
        return $this->hasMany(CasePacket::class, 'case_id');
    }

    public function auditEvents(): HasMany
    {
        return $this->hasMany(AuditEvent::class, 'case_id');
    }

    public function criticalFields(): HasManyThrough
    {
        return $this->hasManyThrough(CriticalField::class, Claim::class, 'case_id', 'claim_id');
    }

    public function partyByRole(PartyRole $role): ?Party
    {
        return $this->parties->firstWhere('role', $role);
    }

    public function latestPacket(): ?CasePacket
    {
        return $this->packets()->orderByDesc('version')->first();
    }
}
