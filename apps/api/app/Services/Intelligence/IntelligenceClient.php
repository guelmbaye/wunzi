<?php

namespace App\Services\Intelligence;

use App\Exceptions\IntelligenceServiceException;
use Illuminate\Http\Client\ConnectionException;
use Illuminate\Http\Client\Response;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

/**
 * The single HTTP client between the System of Record (Laravel) and the
 * intelligence layer (FastAPI). Laravel is the only production client of the
 * FastAPI surface.
 *
 * TIMEOUT BUDGET — the three layers must nest, or the outer layer kills work the
 * inner layer already paid for:
 *
 *     ASR provider call   ASR_TIMEOUT_SECONDS        120s   (FastAPI → provider)
 *     FastAPI handler     ASR_MAX_RETRIES = 1        ≤240s
 *     this client         INTELLIGENCE_TIMEOUT       300s   (> FastAPI worst case)
 *     queue job           ProcessRecording::$timeout 420s   (> client worst case)
 *
 * Retries live in exactly ONE place. FastAPI retries the provider; this client
 * does not retry a call that FastAPI already retried, because 2 layers of 3
 * attempts is 9 ASR calls for one recording — and with the job's own 3 tries,
 * 27. Retryable transport faults are left to the queue, which has backoff and a
 * visible failure record.
 */
class IntelligenceClient
{
    /** Endpoints safe to retry in-process: no upstream cost, no side effects. */
    private const IDEMPOTENT_PATHS = [
        '/health',
        '/v1/intelligence/build-issue-graph',
        '/v1/intelligence/generate-case',
    ];

    public function __construct(
        private readonly ?string $baseUrl = null,
        private readonly ?string $secret = null,
        private readonly ?int $timeout = null,
    ) {
    }

    public function transcribe(array $payload, ?string $idempotencyKey = null): array
    {
        return $this->post('/v1/speech/transcribe', $payload, idempotencyKey: $idempotencyKey);
    }

    /**
     * Extraction + Critical Speech Guard in one round trip. Nothing between the
     * two steps needs the database, so a second hop bought latency and a second
     * chance to fail without buying any auditability.
     */
    public function analyzeTurn(array $payload): array
    {
        return $this->post('/v1/intelligence/analyze-turn', $payload);
    }

    public function extractClaims(array $payload): array
    {
        return $this->post('/v1/intelligence/extract-claims', $payload);
    }

    public function evaluateCriticality(array $payload): array
    {
        return $this->post('/v1/intelligence/evaluate-criticality', $payload);
    }

    public function buildIssueGraph(array $payload): array
    {
        return $this->post('/v1/intelligence/build-issue-graph', $payload);
    }

    public function generateCase(array $payload): array
    {
        return $this->post('/v1/intelligence/generate-case', $payload);
    }

    /** Accepted, not awaited: returns 202 with a run id to poll. */
    public function startBenchmark(array $payload): array
    {
        return $this->post('/v1/benchmark/run', $payload, timeout: 30);
    }

    public function benchmarkStatus(string $runId): array
    {
        return $this->get('/v1/benchmark/runs/'.$runId, timeout: 30);
    }

    public function health(): array
    {
        return $this->get('/health', timeout: 5);
    }

    private function post(string $path, array $payload, ?int $timeout = null, ?string $idempotencyKey = null): array
    {
        return $this->request('post', $path, $payload, $timeout, $idempotencyKey);
    }

    private function get(string $path, ?int $timeout = null): array
    {
        return $this->request('get', $path, [], $timeout, null);
    }

    private function request(
        string $method,
        string $path,
        array $payload,
        ?int $timeout,
        ?string $idempotencyKey,
    ): array {
        $base = rtrim($this->baseUrl ?? (string) config('wunzi.intelligence.base_url'), '/');
        $url = $base.$path;
        $started = microtime(true);

        $headers = [
            'X-Internal-Service-Token' => $this->secret ?? (string) config('wunzi.intelligence.secret'),
            'X-Request-Id' => (string) (request()?->header('X-Request-Id') ?? uniqid('wz_', true)),
            'Accept' => 'application/json',
        ];

        if ($idempotencyKey !== null) {
            // Lets FastAPI return the first result for a retried call instead of
            // buying a second ASR run over identical audio.
            $headers['Idempotency-Key'] = $idempotencyKey;
        }

        $request = Http::withHeaders($headers)
            ->timeout($timeout ?? $this->timeout ?? (int) config('wunzi.intelligence.timeout', 300))
            ->connectTimeout((int) config('wunzi.intelligence.connect_timeout', 5));

        if (in_array($path, self::IDEMPOTENT_PATHS, true)) {
            $request = $request->retry(
                (int) config('wunzi.intelligence.retries', 2),
                500,
                // 4xx never becomes 2xx on retry; spending attempts on it only
                // delays the real error reaching the operator.
                fn ($exception, $req) => $exception instanceof ConnectionException,
                throw: false,
            );
        }

        try {
            /** @var Response $response */
            $response = $request->{$method}($url, $payload);
        } catch (ConnectionException $e) {
            throw new IntelligenceServiceException(
                'Intelligence service unreachable: '.$e->getMessage(),
                $path
            );
        }

        $latencyMs = (int) ((microtime(true) - $started) * 1000);

        Log::info('intelligence.request', [
            'event' => 'intelligence.request',
            'endpoint' => $path,
            'status' => $response->status(),
            'latency_ms' => $latencyMs,
            'success' => $response->successful(),
            'idempotent' => $idempotencyKey !== null,
        ]);

        if ($response->failed()) {
            throw new IntelligenceServiceException(
                sprintf('Intelligence call %s failed (%d): %s', $path, $response->status(), $response->body()),
                $path,
                $response->status()
            );
        }

        $data = $response->json();

        if (! is_array($data)) {
            throw new IntelligenceServiceException("Malformed response from {$path}", $path, $response->status());
        }

        $data['_latency_ms'] = $latencyMs;

        return $data;
    }
}
