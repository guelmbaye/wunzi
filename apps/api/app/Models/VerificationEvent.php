<?php

namespace App\Models;

use App\Enums\ResolutionType;
use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class VerificationEvent extends Model
{
    use HasUuid;

    protected $fillable = [
        'critical_field_id', 'prompt_text', 'response_text', 'previous_value',
        'resolved_value', 'resolution_type', 'verified_by', 'actor_user_id',
    ];

    protected function casts(): array
    {
        return ['resolution_type' => ResolutionType::class];
    }

    public function criticalField(): BelongsTo
    {
        return $this->belongsTo(CriticalField::class, 'critical_field_id');
    }
}
