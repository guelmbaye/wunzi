<?php

namespace App\Models;

use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class BenchmarkMetric extends Model
{
    use HasUuid;

    protected $fillable = [
        'benchmark_run_id', 'provider', 'metric', 'value',
        'ci_low', 'ci_high', 'scope', 'sample_count',
    ];

    protected function casts(): array
    {
        return ['value' => 'float', 'ci_low' => 'float', 'ci_high' => 'float'];
    }

    public function run(): BelongsTo
    {
        return $this->belongsTo(BenchmarkRun::class, 'benchmark_run_id');
    }
}
