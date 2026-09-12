<?php

namespace App\Http\Controllers\Api;

use App\Enums\CriticalFieldStatus;
use App\Enums\ResolutionType;
use App\Http\Controllers\Controller;
use App\Http\Requests\ResolveVerificationRequest;
use App\Http\Resources\CriticalFieldResource;
use App\Models\CriticalField;
use App\Models\MediationCase;
use App\Services\VerificationService;
use Illuminate\Http\JsonResponse;

class VerificationController extends Controller
{
    public function __construct(private readonly VerificationService $verification)
    {
    }

    /** "Verify What Matters" — only consequential uncertainty, never every sentence. */
    public function index(MediationCase $case): JsonResponse
    {
        $fields = CriticalField::query()
            ->whereIn('claim_id', $case->claims()->select('id'))
            ->whereIn('status', [
                CriticalFieldStatus::NEEDS_CONFIRMATION->value,
                CriticalFieldStatus::UNRESOLVED->value,
            ])
            ->with(['claim.party'])
            ->get();

        return response()->json([
            'data' => CriticalFieldResource::collection($fields)->resolve(),
            'meta' => [
                'headline' => 'Verify What Matters',
                'subtitle' => 'WUNZI found a few details that could materially change the case.',
                'pending' => $fields->where('status', CriticalFieldStatus::NEEDS_CONFIRMATION)->count(),
            ],
        ]);
    }

    public function resolve(ResolveVerificationRequest $request, CriticalField $field): JsonResponse
    {
        $event = $this->verification->resolve(
            field: $field,
            resolution: ResolutionType::from($request->string('resolution')->toString()),
            value: $request->input('value'),
            responseText: $request->input('response_text'),
            verifiedBy: $request->string('verified_by', 'speaker')->toString(),
        );

        return response()->json([
            'data' => (new CriticalFieldResource($field->fresh(['claim.party'])))->resolve(),
            'verification_event' => [
                'id' => $event->id,
                'resolution_type' => $event->resolution_type->value,
                'previous_value' => $event->previous_value,
                'resolved_value' => $event->resolved_value,
            ],
            'note' => 'Speaker confirmation means WUNZI captured the intended claim correctly. It does not establish that the claim is objectively true.',
        ]);
    }
}
