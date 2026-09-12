<?php

namespace App\Jobs;

use App\Enums\AsrProvider;
use App\Enums\ProcessingStatus;
use App\Exceptions\IntelligenceServiceException;
use App\Models\AudioRecording;
use App\Services\CaseStateMachine;
use App\Services\Intelligence\ClaimIngestionService;
use App\Services\Intelligence\TranscriptionService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldBeUnique;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Log;

/**
 * AudioUploaded → TranscriptReady → ClaimsReady → VerificationRequired?
 * Ordinary queued job. No Kafka, no multi-agent orchestration.
 *
 * TIMEOUT BUDGET — must stay above the HTTP client's worst case, or the job is
 * killed mid-flight and a transcript that was already paid for is discarded:
 *
 *     ASR provider call         120s
 *     FastAPI (1 retry)        ≤240s
 *     IntelligenceClient        300s
 *     this job                  420s   ← transcription + analysis + writes
 *
 * `ShouldBeUnique` is not decoration: a double dispatch means a second ASR call
 * on the same audio. The idempotency key protects a *sequential* retry; only the
 * unique lock protects a *concurrent* one.
 */
class ProcessRecording implements ShouldQueue, ShouldBeUnique
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 3;
    public int $timeout = 420;
    public array $backoff = [10, 30, 60];

    /** Released if the worker dies, so a crash cannot wedge a recording forever. */
    public int $uniqueFor = 900;

    public function __construct(
        public string $recordingId,
        public string $provider = 'sahara',
    ) {
    }

    public function uniqueId(): string
    {
        return $this->recordingId.':'.$this->provider;
    }

    public function handle(
        TranscriptionService $transcription,
        ClaimIngestionService $ingestion,
        CaseStateMachine $stateMachine,
    ): void {
        $recording = AudioRecording::with('party', 'mediationCase')->findOrFail($this->recordingId);
        $provider = AsrProvider::from($this->provider);

        $run = $transcription->transcribe($recording, $provider, primary: $provider->isSponsor());
        $ingestion->ingest($recording, $run);

        $stateMachine->recompute($recording->mediationCase);
    }

    /**
     * A malformed request will not become well-formed on retry. Burning three
     * attempts on a 4xx only delays the real error reaching an operator.
     */
    public function retryUntil(): \DateTimeInterface
    {
        return now()->addMinutes(30);
    }

    public function failed(\Throwable $e): void
    {
        AudioRecording::whereKey($this->recordingId)->update([
            'processing_status' => ProcessingStatus::FAILED->value,
            'failure_reason' => substr($e->getMessage(), 0, 250),
        ]);

        Log::error('recording.processing_failed', [
            'event' => 'recording.processing_failed',
            'recording_id' => $this->recordingId,
            'provider' => $this->provider,
            'status' => $e instanceof IntelligenceServiceException ? $e->statusCode : null,
            'message' => $e->getMessage(),
        ]);
    }
}
