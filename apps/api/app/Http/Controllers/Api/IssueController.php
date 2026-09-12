<?php

namespace App\Http\Controllers\Api;

use App\Enums\AuditAction;
use App\Enums\IssueStatus;
use App\Http\Controllers\Controller;
use App\Http\Requests\OverrideIssueRequest;
use App\Http\Resources\IssueResource;
use App\Jobs\BuildIssueGraph;
use App\Models\Issue;
use App\Models\MediationCase;
use App\Services\AuditLogger;
use App\Services\Intelligence\IssueGraphService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class IssueController extends Controller
{
    public function __construct(
        private readonly IssueGraphService $issueGraph,
        private readonly AuditLogger $audit,
    ) {
    }

    /** The Issue Map: four states, equal visual weight, no correctness marks. */
    public function index(MediationCase $case): JsonResponse
    {
        $issues = $case->issues()->with('issueClaims')->get();

        $grouped = collect(IssueStatus::cases())->mapWithKeys(fn (IssueStatus $status) => [
            $status->value => IssueResource::collection(
                $issues->where('status', $status)->values()
            )->resolve(),
        ]);

        return response()->json([
            'data' => $grouped,
            'evidence' => $case->evidenceReferences()->get()->map(fn ($e) => [
                'id' => $e->id,
                'type' => $e->type,
                'availability' => $e->availability->value,
                // "mentioned, not provided" ≠ "does not exist"
                'label' => $e->availability->value === 'MENTIONED_NOT_PROVIDED'
                    ? 'Mentioned, not provided'
                    : ucfirst(strtolower(str_replace('_', ' ', $e->availability->value))),
                'description' => $e->description,
            ]),
            'meta' => [
                'total' => $issues->count(),
                'neutrality_note' => 'WUNZI does not decide who is right. It preserves what each side actually states.',
            ],
        ]);
    }

    public function build(Request $request, MediationCase $case): JsonResponse
    {
        if ($request->boolean('sync')) {
            $issues = $this->issueGraph->build($case);

            return response()->json([
                'data' => IssueResource::collection(collect($issues))->resolve(),
            ]);
        }

        BuildIssueGraph::dispatch($case->id);

        return response()->json(['status' => 'queued'], 202);
    }

    public function override(OverrideIssueRequest $request, Issue $issue): JsonResponse
    {
        $before = $issue->status->value;

        $issue->update([
            'status' => $request->string('status')->toString(),
            'mediator_overridden' => true,
            'classification_reason' => 'Set by mediator review.',
        ]);

        $this->audit->record(
            action: AuditAction::ISSUE_OVERRIDDEN_BY_MEDIATOR,
            entityType: 'issue',
            entityId: $issue->id,
            caseId: $issue->case_id,
            before: ['status' => $before],
            after: ['status' => $issue->status->value, 'note' => $request->input('note')],
            actorType: 'user',
        );

        return (new IssueResource($issue))->response();
    }
}
