<?php

namespace App\Models;

use App\Enums\BenchmarkRunStatus;
use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;

class BenchmarkRun extends Model
{
    use HasUuid;

    protected $fillable = [
        'name', 'dataset_version', 'split', 'pipeline_version', 'prompt_version',
        'git_commit', 'providers', 'status', 'results', 'sponsor_outcome_delta',
        'best_competitor', 'guard_enabled', 'failure_reason', 'started_at', 'completed_at',
    ];

    protected function casts(): array
    {
        return [
            'providers' => 'array',
            'results' => 'array',
            'status' => BenchmarkRunStatus::class,
            'guard_enabled' => 'boolean',
            'sponsor_outcome_delta' => 'float',
            'started_at' => 'datetime',
            'completed_at' => 'datetime',
        ];
    }

    public function metrics(): HasMany
    {
        return $this->hasMany(BenchmarkMetric::class, 'benchmark_run_id');
    }

    public function observations(): HasMany
    {
        return $this->hasMany(BenchmarkObservation::class, 'benchmark_run_id');
    }

    /**
     * Anti-MIRROR-OPS gate 1. Internal WUNZI discipline, not an Intron criterion.
     * STRONG_GO >= +10 pts, CONDITIONAL +5..+9, WEAK +1..+4, NO_GO <= 0.
     */
    public function sponsorNecessityVerdict(): string
    {
        $delta = $this->sponsor_outcome_delta;

        return match (true) {
            $delta === null => 'NOT_MEASURED',
            $delta >= 10.0 => 'STRONG_GO',
            $delta >= 5.0 => 'CONDITIONAL_GO',
            $delta > 0.0 => 'WEAK',
            default => 'NO_GO',
        };
    }
}
