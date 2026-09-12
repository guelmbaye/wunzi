<?php

namespace App\Http\Controllers\Api;

use App\Enums\AuditAction;
use App\Http\Controllers\Controller;
use App\Http\Resources\ClaimResource;
use App\Models\Claim;
use App\Models\MediationCase;
use App\Services\Audio\AudioStorage;
use App\Services\AuditLogger;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class ClaimController extends Controller
{
    public function __construct(
        private readonly AudioStorage $storage,
        private readonly AuditLogger $audit,
    ) {
    }

    public function index(Request $request, MediationCase $case): JsonResponse
    {
        $claims = $case->claims()
            ->with(['party', 'criticalFields'])
            ->when($request->filled('party_role'), function ($q) use ($request, $case) {
                $party = $case->parties()->where('role', $request->string('party_role'))->first();
                $q->where('party_id', $party?->id);
            })
            ->when(! $request->boolean('include_superseded'), fn ($q) => $q->where('is_superseded', false))
            ->orderBy('created_at')
            ->get();

        return ClaimResource::collection($claims)->response();
    }

    /**
     * Audio provenance. The AI interpretation is never the final authority
     * over the source: the mediator can always return to the exact segment.
     */
    public function audioSource(Claim $claim): JsonResponse
    {
        $source = $claim->sources()->with('segment.transcriptRun.audio')->first();

        abort_if($source === null, 404, 'No audio provenance recorded for this claim.');

        $segment = $source->segment;
        $recording = $segment->transcriptRun->audio;

        return response()->json([
            'claim_id' => $claim->id,
            'audio_url' => $this->storage->signedUrl($recording),
            'start_ms' => $source->start_offset_ms ?? $segment->start_ms,
            'end_ms' => $source->end_offset_ms ?? $segment->end_ms,
            'transcript_snippet' => $segment->text,
            'language' => $segment->language_code,
            'provider' => $segment->transcriptRun->provider->value,
            'expires_in_minutes' => (int) config('wunzi.audio.signed_url_ttl_minutes'),
        ]);
    }

    /** Mediator override of an extracted claim. Provenance is never overwritten silently. */
    public function correct(Request $request, Claim $claim): JsonResponse
    {
        $validated = $request->validate([
            'canonical_value' => ['required', 'array'],
            'note' => ['nullable', 'string', 'max:500'],
        ]);

        $before = $claim->canonical_value;

        $claim->update([
            'canonical_value' => $validated['canonical_value'],
            'mediator_corrected' => true,
        ]);

        $this->audit->record(
            action: AuditAction::CLAIM_CORRECTED_BY_MEDIATOR,
            entityType: 'claim',
            entityId: $claim->id,
            caseId: $claim->case_id,
            before: ['canonical_value' => $before],
            after: ['canonical_value' => $claim->canonical_value, 'note' => $validated['note'] ?? null],
            actorType: 'user',
        );

        return (new ClaimResource($claim->load('party', 'criticalFields')))->response();
    }
}
