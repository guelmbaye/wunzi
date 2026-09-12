<?php

namespace App\Http\Controllers\Api;

use App\Enums\AuditAction;
use App\Enums\CaseStatus;
use App\Enums\PartyRole;
use App\Enums\ProcessingStatus;
use App\Http\Controllers\Controller;
use App\Http\Requests\StoreRecordingRequest;
use App\Http\Resources\RecordingResource;
use App\Jobs\ProcessRecording;
use App\Models\AudioRecording;
use App\Models\MediationCase;
use App\Models\Party;
use App\Services\Audio\AudioStorage;
use App\Services\AuditLogger;
use App\Services\CaseStateMachine;
use Illuminate\Http\JsonResponse;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Symfony\Component\HttpFoundation\StreamedResponse;

class RecordingController extends Controller
{
    public function __construct(
        private readonly AudioStorage $storage,
        private readonly AuditLogger $audit,
        private readonly CaseStateMachine $stateMachine,
    ) {
    }

    /**
     * Recordings for one case, both parties.
     *
     * Case-scoped rather than party-scoped: the intake screen polls this while
     * transcription runs, and scoping to the case keeps authorization on the
     * one object that owns access to both accounts.
     */
    public function index(MediationCase $case): JsonResponse
    {
        $recordings = $case->recordings()
            ->with('transcriptRuns.segments')
            ->orderBy('created_at')
            ->get();

        return response()->json(['data' => RecordingResource::collection($recordings)]);
    }

    public function store(StoreRecordingRequest $request, Party $party): JsonResponse
    {
        abort_unless(
            $party->hasConsent() || $request->boolean('consent_recorded'),
            422,
            'Recording consent has not been captured for this party.'
        );

        if ($request->hasFile('audio')) {
            $meta = $this->storage->store($party, $request->file('audio'), $request->input('duration_ms'));
            $disk = $this->storage->disk();
            $fixtureKey = null;
        } else {
            // Fixture mode: replay of a previously recorded consented clip.
            $fixtureKey = $request->string('fixture_key')->toString();
            $meta = [
                'id' => (string) Str::uuid(),
                'storage_path' => 'fixtures/'.$fixtureKey,
                'mime_type' => 'audio/wav',
                'size_bytes' => null,
                'sha256' => hash('sha256', $fixtureKey),
                'duration_ms' => $request->input('duration_ms'),
            ];
            $disk = 'fixtures';
        }

        $recording = new AudioRecording([
            'case_id' => $party->case_id,
            'party_id' => $party->id,
            'disk' => $disk,
            'storage_path' => $meta['storage_path'],
            'duration_ms' => $meta['duration_ms'],
            'mime_type' => $meta['mime_type'],
            'size_bytes' => $meta['size_bytes'],
            'sha256' => $meta['sha256'],
            'consent_recorded' => true,
            'processing_status' => ProcessingStatus::UPLOADED,
            'fixture_key' => $fixtureKey,
        ]);
        $recording->id = $meta['id'];
        $recording->save();

        $this->audit->record(
            action: AuditAction::AUDIO_CAPTURED,
            entityType: 'audio_recording',
            entityId: $recording->id,
            caseId: $party->case_id,
            after: ['party_role' => $party->role->value, 'sha256' => $recording->sha256],
        );

        $this->stateMachine->transition(
            $party->mediationCase,
            $party->role === PartyRole::PARTY_A ? CaseStatus::PARTY_A_CAPTURE : CaseStatus::PARTY_B_CAPTURE,
            force: true,
        );

        ProcessRecording::dispatch(
            $recording->id,
            $request->string('provider', config('wunzi.asr.primary'))->toString()
        );

        return (new RecordingResource($recording))->response()->setStatusCode(202);
    }

    public function show(AudioRecording $recording): JsonResponse
    {
        $recording->load(['transcriptRuns' => fn ($q) => $q->orderByDesc('is_primary'), 'transcriptRuns.segments']);

        return (new RecordingResource($recording))->response();
    }

    /** Local/dev fallback when the object store cannot issue signed URLs. */
    public function stream(AudioRecording $recording): StreamedResponse
    {
        $disk = Storage::disk($recording->disk);

        abort_unless($disk->exists($recording->storage_path), 404);

        return $disk->response($recording->storage_path, null, [
            'Content-Type' => $recording->mime_type,
            'Cache-Control' => 'no-store',
        ]);
    }
}
