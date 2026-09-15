<?php

namespace App\Services\Intelligence;

use App\Enums\AsrProvider;
use App\Enums\AuditAction;
use App\Enums\ProcessingStatus;
use App\Models\AudioRecording;
use App\Models\TranscriptRun;
use App\Models\TranscriptSegment;
use App\Services\Audio\AudioStorage;
use App\Services\AuditLogger;
use Illuminate\Support\Facades\DB;

class TranscriptionService
{
    public function __construct(
        private readonly IntelligenceClient $client,
        private readonly AudioStorage $storage,
        private readonly AuditLogger $audit,
    ) {
    }

    /**
     * Runs one ASR provider over one recording and persists an immutable
     * TranscriptRun. Idempotent on hash(audio_sha256 + provider + model).
     */
    public function transcribe(AudioRecording $recording, AsrProvider $provider, bool $primary = false): TranscriptRun
    {
        $model = $this->modelFor($provider);
        $idempotencyKey = hash('sha256', implode('|', [
            $recording->sha256,
            $provider->value,
            $model,
            (string) config('wunzi.pipeline_version'),
        ]));

        $existing = TranscriptRun::where('audio_id', $recording->id)
            ->where('provider', $provider->value)
            ->where('idempotency_key', $idempotencyKey)
            ->where('status', 'COMPLETED')
            ->first();

        if ($existing) {
            return $existing;
        }

        $recording->markStatus(ProcessingStatus::TRANSCRIBING);

        // The same key that guarantees one TranscriptRun per (audio, provider,
        // model, pipeline) also tells FastAPI that a retry is a retry, so a
        // requeued job replays the result instead of buying a second ASR call.
        $response = $this->client->transcribe([
            'audio_id' => $recording->id,
            // A URI, not bytes: FastAPI reads the object from private storage
            // directly. Base64 audio through Laravel would double the transfer
            // and put a multi-megabyte body in the PHP request lifecycle.
            'audio_uri' => $this->storage->readableUri($recording),
            'audio_sha256' => $recording->sha256,
            'provider' => $provider->value,
            'mode' => config('wunzi.mode'),
            'fixture_key' => $recording->fixture_key,
            'pipeline_version' => config('wunzi.pipeline_version'),
        ], idempotencyKey: $idempotencyKey);

        return DB::transaction(function () use ($recording, $provider, $model, $idempotencyKey, $response, $primary) {
            $run = TranscriptRun::create([
                'audio_id' => $recording->id,
                'provider' => $provider->value,
                'model' => $response['model'] ?? $model,
                'provider_version' => $response['provider_version'] ?? null,
                'status' => 'COMPLETED',
                'raw_payload' => $response['raw'] ?? null,
                'normalized_transcript' => $response['text'] ?? '',
                'latency_ms' => $response['latency_ms'] ?? $response['_latency_ms'] ?? null,
                'idempotency_key' => $idempotencyKey,
                'source_mode' => $response['source_mode'] ?? config('wunzi.mode'),
                'fixture_origin' => $response['fixture_origin'] ?? null,
                'is_primary' => $primary,
            ]);

            foreach (($response['segments'] ?? []) as $i => $segment) {
                TranscriptSegment::create([
                    'transcript_run_id' => $run->id,
                    'sequence' => $i,
                    'start_ms' => (int) ($segment['start_ms'] ?? 0),
                    'end_ms' => (int) ($segment['end_ms'] ?? 0),
                    'text' => (string) ($segment['text'] ?? ''),
                    // null when the provider does not expose it — never fabricated
                    'language_code' => $segment['language'] ?? null,
                    'confidence' => $segment['confidence'] ?? null,
                ]);
            }

            $recording->markStatus(ProcessingStatus::TRANSCRIBED);

            $this->audit->record(
                action: AuditAction::TRANSCRIPT_GENERATED,
                entityType: 'transcript_run',
                entityId: $run->id,
                caseId: $recording->case_id,
                after: [
                    'provider' => $provider->value,
                    'model' => $run->model,
                    'segments' => count($response['segments'] ?? []),
                    'latency_ms' => $run->latency_ms,
                    'source_mode' => $run->source_mode,
                ],
            );

            return $run;
        });
    }

    private function modelFor(AsrProvider $provider): string
    {
        return match ($provider) {
            AsrProvider::SAHARA => (string) env('SAHARA_MODEL', 'sahara'),
            AsrProvider::WHISPER => (string) env('WHISPER_MODEL', 'whisper-large-v3'),
            AsrProvider::MODEL_B => (string) env('MODEL_B_MODEL', 'model_b'),
            AsrProvider::MODEL_C => (string) env('MODEL_C_MODEL', 'model_c'),
        };
    }
}
