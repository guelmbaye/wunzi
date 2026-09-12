<?php

namespace App\Jobs;

use App\Models\BenchmarkRun;
use App\Services\BenchmarkService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;

/** Provider matrix execution. Failures are recorded as failures, never silently substituted. */
class RunBenchmark implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 1;
    public int $timeout = 3600;

    public function __construct(public string $benchmarkRunId)
    {
    }

    public function handle(BenchmarkService $benchmark): void
    {
        $benchmark->start(BenchmarkRun::findOrFail($this->benchmarkRunId));
    }
}
