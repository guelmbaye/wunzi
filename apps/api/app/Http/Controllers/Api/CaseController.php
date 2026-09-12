<?php

namespace App\Http\Controllers\Api;

use App\Enums\AuditAction;
use App\Enums\CaseStatus;
use App\Enums\ConsentStatus;
use App\Http\Controllers\Controller;
use App\Http\Requests\StoreCaseRequest;
use App\Http\Resources\CaseResource;
use App\Models\MediationCase;
use App\Models\Party;
use App\Services\Audio\AudioStorage;
use App\Services\AuditLogger;
use App\Services\CaseStateMachine;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;

class CaseController extends Controller
{
    public function __construct(
        private readonly AuditLogger $audit,
        private readonly CaseStateMachine $stateMachine,
        private readonly AudioStorage $storage,
    ) {
    }

    public function index(Request $request): JsonResponse
    {
        $cases = MediationCase::query()
            ->with('parties')
            ->withCount([
                'claims',
                'issues',
                'issues as disputed_issues_count' => fn ($q) => $q->where('status', 'DISPUTED'),
                'issues as missing_issues_count' => fn ($q) => $q->where('status', 'MISSING'),
                'issues as unverified_issues_count' => fn ($q) => $q->where('status', 'UNVERIFIED'),
            ])
            ->when($request->filled('status'), fn ($q) => $q->where('status', $request->string('status')))
            ->latest()
            ->paginate((int) $request->integer('per_page', 20));

        return CaseResource::collection($cases)->response();
    }

    public function store(StoreCaseRequest $request): JsonResponse
    {
        $case = DB::transaction(function () use ($request) {
            $case = MediationCase::create([
                'public_reference' => $this->nextReference(),
                'title' => $request->string('title'),
                'category' => $request->string('category', 'rental_deposit_dispute'),
                'language_configuration' => $request->string('language_configuration', 'rw-en-fr'),
                'status' => CaseStatus::DRAFT,
                'created_by' => Auth::id(),
                'pipeline_version' => config('wunzi.pipeline_version'),
            ]);

            foreach ($request->input('parties', []) as $party) {
                Party::create([
                    'case_id' => $case->id,
                    'role' => $party['role'],
                    'display_name' => $party['display_name'],
                    'contact_reference' => $party['contact_reference'] ?? null,
                    'consent_status' => ConsentStatus::PENDING,
                ]);
            }

            $this->audit->record(
                action: AuditAction::CASE_CREATED,
                entityType: 'mediation_case',
                entityId: $case->id,
                caseId: $case->id,
                after: ['title' => $case->title, 'category' => $case->category],
            );

            return $case;
        });

        return (new CaseResource($case->load('parties')))->response()->setStatusCode(201);
    }

    public function show(MediationCase $case): JsonResponse
    {
        $case->load(['parties', 'issues', 'evidenceReferences'])
            ->loadCount(['claims', 'issues']);

        $pendingVerifications = $this->stateMachine->pendingCriticalFieldsQuery($case)->count();

        return response()->json([
            'data' => (new CaseResource($case))->resolve(),
            'meta' => [
                'pending_verifications' => $pendingVerifications,
                'issue_states' => $case->issues->countBy(fn ($i) => $i->status->value),
                'can_create_packet' => $pendingVerifications === 0 && $case->issues->isNotEmpty(),
            ],
        ]);
    }

    /** Overview hero: what the mediator sees before opening anything. */
    public function overview(MediationCase $case): JsonResponse
    {
        $case->load(['parties', 'issues', 'claims', 'recordings', 'evidenceReferences']);

        return response()->json([
            'case' => (new CaseResource($case))->resolve(),
            'progress' => [
                'party_a' => $case->recordings->where('party_id', optional($case->partyByRole(\App\Enums\PartyRole::PARTY_A))->id)->isNotEmpty(),
                'party_b' => $case->recordings->where('party_id', optional($case->partyByRole(\App\Enums\PartyRole::PARTY_B))->id)->isNotEmpty(),
                'verification' => $this->stateMachine->pendingCriticalFieldsQuery($case)->count() === 0,
                'issue_map' => $case->issues->isNotEmpty(),
                'packet' => $case->packets()->exists(),
            ],
            'summary' => [
                'agreed' => $case->issues->where('status', \App\Enums\IssueStatus::AGREED)->count(),
                'disputed' => $case->issues->where('status', \App\Enums\IssueStatus::DISPUTED)->count(),
                'missing' => $case->issues->where('status', \App\Enums\IssueStatus::MISSING)->count(),
                'unverified' => $case->issues->where('status', \App\Enums\IssueStatus::UNVERIFIED)->count(),
                'fields_needing_verification' => $this->stateMachine->pendingCriticalFieldsQuery($case)->count(),
            ],
        ]);
    }

    /** Data transparency + retention: deletes audio, transcripts, claims, graph, packet. */
    public function destroy(MediationCase $case): JsonResponse
    {
        DB::transaction(function () use ($case) {
            foreach ($case->recordings as $recording) {
                $this->storage->delete($recording);
            }

            $this->audit->record(
                action: AuditAction::CASE_DELETED,
                entityType: 'mediation_case',
                entityId: $case->id,
                caseId: null,
                before: ['public_reference' => $case->public_reference],
            );

            $case->forceDelete();
        });

        return response()->json([
            'message' => 'This permanently removes the case data used in this session.',
        ], 200);
    }

    private function nextReference(): string
    {
        $sequence = MediationCase::withTrashed()->count() + 1;

        return sprintf('WZ-%03d', $sequence);
    }
}
