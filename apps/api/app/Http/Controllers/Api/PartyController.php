<?php

namespace App\Http\Controllers\Api;

use App\Enums\AuditAction;
use App\Enums\ConsentStatus;
use App\Http\Controllers\Controller;
use App\Http\Requests\StorePartyRequest;
use App\Http\Resources\PartyResource;
use App\Models\MediationCase;
use App\Models\Party;
use App\Services\AuditLogger;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class PartyController extends Controller
{
    public function __construct(private readonly AuditLogger $audit)
    {
    }

    public function store(StorePartyRequest $request, MediationCase $case): JsonResponse
    {
        $party = Party::create([
            'case_id' => $case->id,
            'role' => $request->string('role'),
            'display_name' => $request->string('display_name'),
            'contact_reference' => $request->input('contact_reference'),
            'consent_status' => $request->string('consent_status', ConsentStatus::PENDING->value),
        ]);

        $this->audit->record(
            action: AuditAction::PARTY_CREATED,
            entityType: 'party',
            entityId: $party->id,
            caseId: $case->id,
            after: ['role' => $party->role->value],
        );

        return (new PartyResource($party))->response()->setStatusCode(201);
    }

    /**
     * Explicit consent capture. No recording may be processed without it.
     * "This recording will be processed by AI to prepare a mediation case.
     *  It does not determine who is right."
     */
    public function consent(Request $request, Party $party): JsonResponse
    {
        $request->validate(['granted' => ['required', 'boolean']]);

        $party->update([
            'consent_status' => $request->boolean('granted') ? ConsentStatus::GRANTED : ConsentStatus::WITHDRAWN,
            'consent_recorded_at' => now(),
        ]);

        return (new PartyResource($party))->response();
    }
}
