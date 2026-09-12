<?php

namespace App\Services\Intelligence;

use App\Enums\AuditAction;
use App\Enums\EvidenceAvailability;
use App\Enums\IssueRelationship;
use App\Enums\PartyRole;
use App\Models\EvidenceReference;
use App\Models\Issue;
use App\Models\IssueClaim;
use App\Models\MediationCase;
use App\Services\AuditLogger;
use App\Services\Safety\NeutralityFilter;
use Illuminate\Support\Facades\DB;

/**
 * Builds the Mediation Issue Graph. The comparison is deterministic given
 * (claims + verification states + comparison relations); the LLM only proposes
 * semantic equivalence for free-text propositions.
 */
class IssueGraphService
{
    public function __construct(
        private readonly IntelligenceClient $client,
        private readonly AuditLogger $audit,
        private readonly NeutralityFilter $neutrality,
    ) {
    }

    public function build(MediationCase $case): array
    {
        $case->load(['parties', 'claims.party', 'claims.criticalFields']);

        $partyA = $case->partyByRole(PartyRole::PARTY_A);
        $partyB = $case->partyByRole(PartyRole::PARTY_B);

        $response = $this->client->buildIssueGraph([
            'case_id' => $case->id,
            'issue_types' => config('wunzi.issue_types'),
            'critical_issue_types' => config('wunzi.critical_issue_types'),
            'party_a' => $this->serialiseClaims($case, $partyA?->id),
            'party_b' => $this->serialiseClaims($case, $partyB?->id),
            'pipeline_version' => config('wunzi.pipeline_version'),
        ]);

        // Neutrality guard runs before anything generated is persisted.
        $this->neutrality->assertPayload($response['issues'] ?? []);

        $partyIdsByRole = $case->parties->mapWithKeys(
            fn ($party) => [$party->role->value => $party->id]
        )->all();

        return DB::transaction(function () use ($case, $response, $partyIdsByRole) {
            $case->issues()->delete();
            $case->evidenceReferences()->delete();

            $issues = [];

            foreach (($response['issues'] ?? []) as $payload) {
                $issue = Issue::create([
                    'case_id' => $case->id,
                    'canonical_type' => $payload['canonical_type'],
                    'status' => $payload['status'],
                    'criticality' => $payload['criticality'] ?? 'HIGH',
                    'summary' => $payload['summary'] ?? null,
                    'classification_reason' => $payload['reason'] ?? null,
                    'party_a_value' => $payload['party_a_value'] ?? null,
                    'party_b_value' => $payload['party_b_value'] ?? null,
                    'comparison_confidence' => $payload['confidence'] ?? null,
                ]);

                foreach (($payload['supporting_claim_ids'] ?? []) as $claimId) {
                    IssueClaim::firstOrCreate([
                        'issue_id' => $issue->id,
                        'claim_id' => $claimId,
                    ], ['relationship' => IssueRelationship::SUPPORTS->value]);
                }

                foreach (($payload['conflicting_claim_ids'] ?? []) as $claimId) {
                    IssueClaim::updateOrCreate([
                        'issue_id' => $issue->id,
                        'claim_id' => $claimId,
                    ], ['relationship' => IssueRelationship::CONFLICTS->value]);
                }

                $issues[] = $issue;
            }

            foreach (($response['evidence'] ?? []) as $evidence) {
                EvidenceReference::create([
                    'case_id' => $case->id,
                    'issue_id' => $this->issueIdForType($issues, $evidence['issue_type'] ?? null),
                    // FastAPI has no party ids and must not appear to supply
                    // one. It names a role; the System of Record resolves it.
                    'party_id' => $partyIdsByRole[$evidence['mentioned_by_role'] ?? ''] ?? null,
                    'type' => $evidence['type'],
                    'description' => $evidence['description'] ?? null,
                    // "mentioned, not provided" is NOT "does not exist"
                    'availability' => $evidence['availability'] ?? EvidenceAvailability::MISSING->value,
                ]);
            }

            $this->audit->record(
                action: AuditAction::ISSUE_GRAPH_GENERATED,
                entityType: 'mediation_case',
                entityId: $case->id,
                caseId: $case->id,
                after: [
                    'issue_count' => count($issues),
                    'states' => collect($issues)->countBy(fn ($i) => $i->status->value)->all(),
                ],
            );

            return $issues;
        });
    }

    private function serialiseClaims(MediationCase $case, ?string $partyId): array
    {
        if (! $partyId) {
            return [];
        }

        return $case->claims
            ->where('party_id', $partyId)
            ->where('is_superseded', false)
            ->map(fn ($claim) => [
                'claim_id' => $claim->id,
                'type' => $claim->type,
                'subject' => $claim->subject_ref,
                'predicate' => $claim->predicate,
                'canonical_value' => $claim->canonical_value,
                'polarity' => $claim->polarity->value,
                'criticality' => $claim->criticality->value,
                'verification_status' => $claim->verification_status->value,
                'reported_speech' => $claim->reported_speech,
                'has_pending_critical_field' => $claim->criticalFields
                    ->contains(fn ($f) => $f->isPending()),
            ])->values()->all();
    }

    private function issueIdForType(array $issues, ?string $type): ?string
    {
        if (! $type) {
            return null;
        }

        foreach ($issues as $issue) {
            if ($issue->canonical_type === $type) {
                return $issue->id;
            }
        }

        return null;
    }
}
