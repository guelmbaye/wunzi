<?php

namespace App\Services\Intelligence;

use App\Enums\AuditAction;
use App\Enums\CaseStatus;
use App\Models\CasePacket;
use App\Models\MediationCase;
use App\Services\AuditLogger;
use App\Services\CaseStateMachine;
use App\Services\Safety\HallucinationValidator;
use App\Services\Safety\NeutralityFilter;
use Illuminate\Support\Facades\Auth;

/**
 * The real downstream action: a structured, traceable mediator-ready case.
 * The generator receives structured objects only — never raw speculation.
 */
class CasePacketService
{
    public function __construct(
        private readonly IntelligenceClient $client,
        private readonly NeutralityFilter $neutrality,
        private readonly HallucinationValidator $hallucination,
        private readonly CaseStateMachine $stateMachine,
        private readonly AuditLogger $audit,
    ) {
    }

    public function generate(MediationCase $case): CasePacket
    {
        // Hard gate: no packet while consequential uncertainty is unresolved.
        $this->stateMachine->assertNoBlockingCriticalFields($case);

        $case->load(['parties', 'claims.party', 'claims.criticalFields', 'issues.issueClaims', 'evidenceReferences']);

        $response = $this->client->generateCase([
            'case_id' => $case->id,
            'public_reference' => $case->public_reference,
            'category' => $case->category,
            'parties' => $case->parties->map(fn ($p) => [
                'party_id' => $p->id,
                'role' => $p->role->value,
                'display_name' => $p->display_name,
            ])->all(),
            'claims' => $case->claims->where('is_superseded', false)->map(fn ($c) => [
                'claim_id' => $c->id,
                'party_role' => $c->party->role->value,
                'type' => $c->type,
                'subject' => $c->subject_ref,
                'predicate' => $c->predicate,
                'canonical_value' => $c->canonical_value,
                'polarity' => $c->polarity->value,
                'reported_speech' => $c->reported_speech,
                'verification_status' => $c->verification_status->value,
            ])->values()->all(),
            'issues' => $case->issues->map(fn ($i) => [
                'issue_id' => $i->id,
                'canonical_type' => $i->canonical_type,
                'status' => $i->status->value,
                'reason' => $i->classification_reason,
                'party_a_value' => $i->party_a_value,
                'party_b_value' => $i->party_b_value,
            ])->values()->all(),
            'evidence' => $case->evidenceReferences->map(fn ($e) => [
                'evidence_id' => $e->id,
                'type' => $e->type,
                'availability' => $e->availability->value,
                'description' => $e->description,
            ])->values()->all(),
        ]);

        $payload = $response['packet'] ?? [];
        $statements = $response['statements'] ?? [];

        $this->neutrality->assertPayload($payload);
        $this->hallucination->assert(
            $statements,
            $case->claims->pluck('id')->all(),
            $case->issues->pluck('id')->all(),
        );

        $version = ((int) $case->packets()->max('version')) + 1;

        $packet = CasePacket::create([
            'case_id' => $case->id,
            'version' => $version,
            'payload' => $payload,
            'provenance_index' => $statements,
            'neutrality_check_passed' => true,
            'hallucination_check_passed' => true,
            'generation_model' => $response['model'] ?? null,
            'prompt_version' => $response['prompt_version'] ?? null,
            'generated_by' => Auth::id(),
            'generated_at' => now(),
        ]);

        $this->stateMachine->transition($case, CaseStatus::MEDIATOR_REVIEW, force: true);
        $this->stateMachine->transition($case, CaseStatus::READY);

        $this->audit->record(
            action: AuditAction::CASE_PACKET_CREATED,
            entityType: 'case_packet',
            entityId: $packet->id,
            caseId: $case->id,
            after: ['version' => $version],
        );

        return $packet;
    }
}
