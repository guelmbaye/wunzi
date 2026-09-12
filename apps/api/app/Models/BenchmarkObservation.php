<?php

namespace App\Models;

use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

/** One (clip × provider) row — the raw material of the same-audio proof. */
class BenchmarkObservation extends Model
{
    use HasUuid;

    protected $fillable = [
        'benchmark_run_id', 'clip_id', 'scenario_id', 'provider', 'transcript',
        'critical_facts', 'claims', 'issue_states', 'expected_issue_states',
        'case_state_correct', 'error_taxonomy', 'latency_ms', 'provider_failed',
        'used_placeholder_fixture',
    ];

    protected function casts(): array
    {
        return [
            'critical_facts' => 'array',
            'claims' => 'array',
            'issue_states' => 'array',
            'expected_issue_states' => 'array',
            'error_taxonomy' => 'array',
            'case_state_correct' => 'boolean',
            'provider_failed' => 'boolean',
            'used_placeholder_fixture' => 'boolean',
        ];
    }

    public function run(): BelongsTo
    {
        return $this->belongsTo(BenchmarkRun::class, 'benchmark_run_id');
    }
}
