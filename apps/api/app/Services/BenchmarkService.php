<?php

namespace App\Services;

use App\Enums\AsrProvider;
use App\Enums\AuditAction;
use App\Enums\BenchmarkRunStatus;
use App\Models\BenchmarkMetric;
use App\Models\BenchmarkObservation;
use App\Models\BenchmarkRun;
use App\Services\Intelligence\IntelligenceClient;
use Illuminate\Support\Facades\DB;

/**
 * Benchmark is part of the product, not a side notebook.
 * Benchmark integrity rule: only the ASR provider varies. The claim engine,
 * prompts, ontology, issue rules and evaluator are frozen for the whole run.
 */
class BenchmarkService
{
    public function __construct(
        private readonly IntelligenceClient $client,
        private readonly AuditLogger $audit,
    ) {
    }

    public function start(BenchmarkRun $run): BenchmarkRun
    {
        $run->update(['status' => BenchmarkRunStatus::RUNNING, 'started_at' => now()]);

        $this->audit->record(
            action: AuditAction::BENCHMARK_RUN_STARTED,
            entityType: 'benchmark_run',
            entityId: $run->id,
            after: ['providers' => $run->providers, 'dataset' => $run->dataset_version],
        );

        try {
            // Accepted, not awaited. A four-provider run over the holdout split
            // is minutes of work; holding an HTTP connection open for that long
            // is how a run dies to a proxy idle timeout with nothing written
            // down. FastAPI returns 202 immediately and this job polls.
            $this->client->startBenchmark([
                'run_id' => $run->id,
                'dataset_version' => $run->dataset_version,
                'split' => $run->split,
                'providers' => $run->providers,
                'guard_enabled' => $run->guard_enabled,
                'pipeline_version' => $run->pipeline_version,
                'prompt_version' => $run->prompt_version,
            ]);

            $response = $this->awaitCompletion($run);
        } catch (\Throwable $e) {
            $run->update([
                'status' => BenchmarkRunStatus::FAILED,
                'failure_reason' => $e->getMessage(),
                'completed_at' => now(),
            ]);

            throw $e;
        }

        return $this->persistResults($run, $response);
    }

    /**
     * Polls the intelligence service until the run finishes.
     *
     * The waiting happens in a queue worker, which can be observed, retried and
     * killed independently — unlike a socket held open by a web request. The
     * poll interval backs off so a long run does not generate thousands of
     * status calls.
     */
    private function awaitCompletion(BenchmarkRun $run): array
    {
        $deadline = now()->addSeconds((int) config('wunzi.benchmark.max_wait_seconds', 3300));
        $interval = 2;

        while (now()->lessThan($deadline)) {
            sleep($interval);
            $interval = min($interval * 2, 30);

            $status = $this->client->benchmarkStatus($run->id);
            $state = $status['state'] ?? 'RUNNING';

            if ($state === 'COMPLETED') {
                $result = $status['result'] ?? null;

                if (! is_array($result)) {
                    throw new \RuntimeException("Benchmark run {$run->id} completed without a result payload.");
                }

                return $result;
            }

            if ($state === 'FAILED') {
                throw new \RuntimeException(
                    "Benchmark run {$run->id} failed: ".($status['error'] ?? 'no reason reported')
                );
            }
        }

        throw new \RuntimeException("Benchmark run {$run->id} did not finish before the deadline.");
    }

    public function persistResults(BenchmarkRun $run, array $response): BenchmarkRun
    {
        return DB::transaction(function () use ($run, $response) {
            // A run scored from placeholder fixtures is a pipeline smoke test,
            // not a measurement. The verdict is stored so no dashboard can show
            // the number without the warning attached to it.
            $publishable = (bool) ($response['publishable'] ?? true);

            $run->metrics()->delete();
            $run->observations()->delete();

            foreach (($response['metrics'] ?? []) as $metric) {
                BenchmarkMetric::create([
                    'benchmark_run_id' => $run->id,
                    'provider' => $metric['provider'],
                    'metric' => $metric['metric'],
                    'value' => $metric['value'],
                    'ci_low' => $metric['ci_low'] ?? null,
                    'ci_high' => $metric['ci_high'] ?? null,
                    'scope' => $metric['scope'] ?? 'overall',
                    'sample_count' => $metric['sample_count'] ?? null,
                ]);
            }

            foreach (($response['observations'] ?? []) as $observation) {
                BenchmarkObservation::create([
                    'benchmark_run_id' => $run->id,
                    'clip_id' => $observation['clip_id'],
                    'scenario_id' => $observation['scenario_id'],
                    'provider' => $observation['provider'],
                    'transcript' => $observation['transcript'] ?? null,
                    'critical_facts' => $observation['critical_facts'] ?? null,
                    'claims' => $observation['claims'] ?? null,
                    'issue_states' => $observation['issue_states'] ?? null,
                    'expected_issue_states' => $observation['expected_issue_states'] ?? null,
                    'case_state_correct' => $observation['case_state_correct'] ?? null,
                    'error_taxonomy' => $observation['error_taxonomy'] ?? null,
                    'latency_ms' => $observation['latency_ms'] ?? null,
                    'provider_failed' => $observation['provider_failed'] ?? false,
                    'used_placeholder_fixture' => $observation['used_placeholder_fixture'] ?? false,
                ]);
            }

            $run->update([
                'status' => BenchmarkRunStatus::COMPLETED,
                'results' => array_merge($response['summary'] ?? [], [
                    'publishable' => $publishable,
                    'publishability_note' => $response['publishability_note'] ?? null,
                    'integrity' => $response['integrity'] ?? null,
                ]),
                'sponsor_outcome_delta' => $response['sponsor_outcome_delta'] ?? null,
                'best_competitor' => $response['best_competitor'] ?? null,
                'git_commit' => $response['git_commit'] ?? $run->git_commit,
                'completed_at' => now(),
            ]);

            $this->audit->record(
                action: AuditAction::BENCHMARK_RUN_COMPLETED,
                entityType: 'benchmark_run',
                entityId: $run->id,
                after: [
                    'sod' => $run->fresh()->sponsor_outcome_delta,
                    'verdict' => $run->fresh()->sponsorNecessityVerdict(),
                    'publishable' => $publishable,
                ],
            );

            return $run->fresh(['metrics', 'observations']);
        });
    }

    /**
     * Same-Audio / Different-ASR view — the 20-second sponsor proof.
     * Returns one row per critical element across providers for a given clip.
     */
    public function sameAudioComparison(BenchmarkRun $run, string $clipId): array
    {
        $observations = $run->observations()->where('clip_id', $clipId)->get();

        if ($observations->isEmpty()) {
            return ['clip_id' => $clipId, 'rows' => [], 'issue_states' => []];
        }

        $factKeys = $observations
            ->flatMap(fn ($o) => array_keys($o->critical_facts ?? []))
            ->unique()
            ->values();

        $rows = $factKeys->map(function (string $key) use ($observations) {
            return [
                'critical_field' => $key,
                'by_provider' => $observations->mapWithKeys(fn ($o) => [
                    $o->provider => [
                        'value' => data_get($o->critical_facts, $key.'.value'),
                        'correct' => (bool) data_get($o->critical_facts, $key.'.correct', false),
                    ],
                ])->all(),
            ];
        })->all();

        $issueStates = $observations->mapWithKeys(fn ($o) => [
            $o->provider => [
                'issue_states' => $o->issue_states,
                'expected' => $o->expected_issue_states,
                'case_state_correct' => $o->case_state_correct,
            ],
        ])->all();

        return [
            'clip_id' => $clipId,
            'scenario_id' => $observations->first()->scenario_id,
            'rows' => $rows,
            'issue_states' => $issueStates,
            'integrity_note' => 'Same audio · same claim engine · same Issue Graph logic — only the ASR provider changed.',
        ];
    }

    /** @return array<int, string> */
    public function defaultProviders(): array
    {
        return array_map(fn (AsrProvider $p) => $p->value, AsrProvider::benchmarkSet());
    }
}
