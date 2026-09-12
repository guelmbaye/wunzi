<?php

namespace App\Console\Commands;

use App\Enums\BenchmarkRunStatus;
use App\Models\BenchmarkRun;
use App\Services\BenchmarkService;
use Illuminate\Console\Command;

class RunBenchmarkCommand extends Command
{
    protected $signature = 'wunzi:benchmark
                            {--name=Official Demo Benchmark}
                            {--dataset=}
                            {--split=holdout}
                            {--providers=sahara,whisper,model_b,model_c}
                            {--no-guard : Ablation run without the Critical Speech Guard}';

    protected $description = 'Run the multi-ASR benchmark and compute the Sponsor Outcome Delta';

    public function handle(BenchmarkService $benchmark): int
    {
        $providers = explode(',', $this->option('providers'));

        if (count($providers) < 4) {
            $this->error('The challenge requires Sahara plus at least three comparison models.');

            return self::FAILURE;
        }

        $run = BenchmarkRun::create([
            'name' => $this->option('name'),
            'dataset_version' => $this->option('dataset') ?: config('wunzi.dataset_version'),
            'split' => $this->option('split'),
            'pipeline_version' => config('wunzi.pipeline_version'),
            'providers' => $providers,
            'guard_enabled' => ! $this->option('no-guard'),
            'status' => BenchmarkRunStatus::PENDING,
        ]);

        $this->info("Benchmark run {$run->id} started…");

        $run = $benchmark->start($run);

        $this->newLine();
        $this->table(
            ['Provider', 'WER ↓', 'Critical Facts ↑', 'Attribution ↑', 'Issue Graph ↑', 'CMSR ↑'],
            collect($run->providers)->map(function (string $provider) use ($run) {
                $get = fn (string $metric) => optional(
                    $run->metrics->firstWhere(fn ($m) => $m->provider === $provider && $m->metric === $metric && $m->scope === 'overall')
                )->value;

                return [
                    $provider,
                    $this->fmt($get('wer')),
                    $this->fmt($get('critical_fact_accuracy')),
                    $this->fmt($get('claim_attribution_accuracy')),
                    $this->fmt($get('issue_graph_accuracy')),
                    $this->fmt($get('cmsr')),
                ];
            })->all()
        );

        $this->newLine();
        $this->info(sprintf(
            'Sponsor Outcome Delta: %+.1f pts vs %s → %s',
            $run->sponsor_outcome_delta ?? 0,
            $run->best_competitor ?? 'n/a',
            $run->sponsorNecessityVerdict()
        ));
        $this->comment('The +10 pt target is an internal WUNZI discipline, not an official Intron criterion.');

        return self::SUCCESS;
    }

    private function fmt(?float $value): string
    {
        return $value === null ? '—' : number_format($value * 100, 1).'%';
    }
}
