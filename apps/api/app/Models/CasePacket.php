<?php

namespace App\Models;

use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class CasePacket extends Model
{
    use HasUuid;

    protected $fillable = [
        'case_id', 'version', 'payload', 'provenance_index',
        'neutrality_check_passed', 'hallucination_check_passed',
        'generation_model', 'prompt_version', 'generated_by', 'generated_at',
    ];

    protected function casts(): array
    {
        return [
            'payload' => 'array',
            'provenance_index' => 'array',
            'neutrality_check_passed' => 'boolean',
            'hallucination_check_passed' => 'boolean',
            'generated_at' => 'datetime',
        ];
    }

    public function mediationCase(): BelongsTo
    {
        return $this->belongsTo(MediationCase::class, 'case_id');
    }
}
