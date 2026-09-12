<?php

namespace App\Models;

use App\Enums\CriticalFieldStatus;
use App\Enums\CriticalFieldType;
use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;
use Illuminate\Database\Eloquent\Relations\HasMany;

class CriticalField extends Model
{
    use HasUuid;

    protected $fillable = [
        'claim_id', 'field_type', 'detected_value', 'normalized_value',
        'risk_level', 'guard_reason', 'status', 'prompt_text',
    ];

    protected function casts(): array
    {
        return [
            'field_type' => CriticalFieldType::class,
            'status' => CriticalFieldStatus::class,
            'guard_reason' => 'array',
        ];
    }

    public function claim(): BelongsTo
    {
        return $this->belongsTo(Claim::class, 'claim_id');
    }

    public function verificationEvents(): HasMany
    {
        return $this->hasMany(VerificationEvent::class, 'critical_field_id');
    }

    public function isPending(): bool
    {
        return $this->status === CriticalFieldStatus::NEEDS_CONFIRMATION;
    }
}
