<?php

namespace App\Models;

use App\Enums\AuditAction;
use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class AuditEvent extends Model
{
    use HasUuid;

    public $timestamps = false;

    protected $fillable = [
        'case_id', 'actor_type', 'actor_user_id', 'entity_type', 'entity_id',
        'action', 'before', 'after', 'request_id', 'created_at',
    ];

    protected function casts(): array
    {
        return [
            'action' => AuditAction::class,
            'before' => 'array',
            'after' => 'array',
            'created_at' => 'datetime',
        ];
    }

    public function mediationCase(): BelongsTo
    {
        return $this->belongsTo(MediationCase::class, 'case_id');
    }
}
