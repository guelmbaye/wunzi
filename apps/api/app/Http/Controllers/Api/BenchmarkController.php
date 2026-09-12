<?php

namespace App\Http\Controllers\Api;

use App\Enums\BenchmarkRunStatus;
use App\Http\Controllers\Controller;
use App\Http\Requests\StoreBenchmarkRunRequest;
use App\Http\Resources\BenchmarkRunResource;
use App\Jobs\RunBenchmark;
use App\Models\BenchmarkRun;
use App\Services\BenchmarkService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class BenchmarkController extends Controller
{
    public function __construct(private readonly BenchmarkService $benchmark)
    {
    }

    public function index(): JsonResponse
    {
        return BenchmarkRunResource::collection(
            BenchmarkRun::with('metrics')->latest()->paginate(20)
        )->response();
    }

    public function store(StoreBenchmarkRunRequest $request): JsonResponse
    {
        $run = BenchmarkRun::create([
            'name' => $request->string('name'),
            'dataset_version' => $request->string('dataset_version', config('wunzi.dataset_version')),
            'split' => $request->string('split', 'holdout'),
            'pipeline_version' => config('wunzi.pipeline_version'),
            'prompt_version' => $request->input('prompt_version'),
            'providers' => $request->input('providers', $this->benchmark->defaultProviders()),
            'guard_enabled' => $request->boolean('guard_enabled', true),
            'status' => BenchmarkRunStatus::PENDING,
        ]);

        RunBenchmark::dispatch($run->id);

        return (new BenchmarkRunResource($run))->response()->setStatusCode(202);
    }

    public function show(BenchmarkRun $benchmarkRun): JsonResponse
    {
        return (new BenchmarkRunResource($benchmarkRun->load('metrics')))->response();
    }

    /**
     * Judge-facing dashboard: 5 numbers maximum, consequence first.
     * "Did the speech model preserve the dispute?"
     */
    public function dashboard(BenchmarkRun $benchmarkRun): JsonResponse
    {
        $headline = ['wer', 'critical_fact_accuracy', 'claim_attribution_accuracy', 'issue_graph_accuracy', 'cmsr'];

        $metrics = $benchmarkRun->metrics()
            ->whereIn('metric', $headline)
            ->where('scope', 'overall')
            ->get()
            ->groupBy('provider')
            ->map(fn ($rows) => $rows->mapWithKeys(fn ($m) => [$m->metric => [
                'value' => $m->value,
                'ci' => $m->ci_low !== null ? [$m->ci_low, $m->ci_high] : null,
            ]]));

        return response()->json([
            'headline' => 'Did the speech model preserve the dispute?',
            'metrics' => $metrics,
            'sponsor_outcome_delta' => [
                'value' => $benchmarkRun->sponsor_outcome_delta,
                'unit' => 'percentage_points',
                'best_competitor' => $benchmarkRun->best_competitor,
                'verdict' => $benchmarkRun->sponsorNecessityVerdict(),
            ],
            'integrity' => 'Same audio · same claim engine · same Issue Graph logic',
            'dataset' => [
                'version' => $benchmarkRun->dataset_version,
                'split' => $benchmarkRun->split,
                'pipeline_version' => $benchmarkRun->pipeline_version,
                'git_commit' => $benchmarkRun->git_commit,
            ],
        ]);
    }

    /** The 20-second proof: same audio, different ASR, different mediation state. */
    public function sameAudio(Request $request, BenchmarkRun $benchmarkRun): JsonResponse
    {
        $request->validate(['clip_id' => ['required', 'string']]);

        return response()->json(
            $this->benchmark->sameAudioComparison($benchmarkRun, $request->string('clip_id')->toString())
        );
    }

    public function observations(Request $request, BenchmarkRun $benchmarkRun): JsonResponse
    {
        $observations = $benchmarkRun->observations()
            ->when($request->filled('provider'), fn ($q) => $q->where('provider', $request->string('provider')))
            ->when($request->filled('scenario_id'), fn ($q) => $q->where('scenario_id', $request->string('scenario_id')))
            ->get();

        return response()->json(['data' => $observations]);
    }
}
