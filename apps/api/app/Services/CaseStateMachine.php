<?php

namespace App\Services;

use App\Enums\AuditAction;
use App\Enums\CaseStatus;
use App\Enums\CriticalFieldStatus;
use App\Exceptions\InvalidCaseTransitionException;
use App\Models\CriticalField;
use App\Models\MediationCase;

/**
 * Explicit system logic governs state transitions. The LLM interprets language;
 * it never decides case readiness (blueprint P6).
 */
class CaseStateMachine
{
    public function __construct(private readonly AuditLogger $audit)
    {
    }

    public function transition(MediationCase $case, CaseStatus $target, bool $force = false): MediationCase
    {
        $from = $case->status;

        if ($from === $target) {
            return $case;
        }

        if (! $force && ! $from->canTransitionTo($target)) {
            throw InvalidCaseTransitionException::between($from, $target);
        }

        if ($target === CaseStatus::READY) {
            $this->assertNoBlockingCriticalFields($case);
        }

        $case->update(['status' => $target]);

        $this->audit->record(
            action: AuditAction::CASE_STATE_CHANGED,
            entityType: 'mediation_case',
            entityId: $case->id,
            caseId: $case->id,
            before: ['status' => $from->value],
            after: ['status' => $target->value],
        );

        return $case->refresh();
    }

    /**
     * Recomputes the case status from its actual contents. Called after every
     * pipeline step so the status can never drift from reality.
     */
    public function recompute(MediationCase $case): MediationCase
    {
        $case->loadMissing('parties', 'claims', 'issues');

        $pendingCritical = $this->pendingCriticalFieldsQuery($case)->count();

        $partyAReady = $case->claims->where('party_id', optional($case->partyByRole(\App\Enums\PartyRole::PARTY_A))->id)->isNotEmpty();
        $partyBReady = $case->claims->where('party_id', optional($case->partyByRole(\App\Enums\PartyRole::PARTY_B))->id)->isNotEmpty();

        $target = match (true) {
            $case->status === CaseStatus::READY => CaseStatus::READY,
            $pendingCritical > 0 => CaseStatus::VERIFICATION_REQUIRED,
            $case->issues->isNotEmpty() => CaseStatus::ISSUE_GRAPH_READY,
            $partyAReady && $partyBReady => CaseStatus::PARTY_B_CAPTURE,
            $partyAReady => CaseStatus::PARTY_A_CAPTURE,
            default => $case->status,
        };

        return $this->transition($case, $target, force: true);
    }

    public function assertNoBlockingCriticalFields(MediationCase $case): void
    {
        $pending = $this->pendingCriticalFieldsQuery($case)->count();

        if ($pending > 0) {
            throw InvalidCaseTransitionException::pendingCriticalFields($pending);
        }
    }

    public function pendingCriticalFieldsQuery(MediationCase $case)
    {
        return CriticalField::query()
            ->whereIn('claim_id', $case->claims()->select('id'))
            ->whereIn('status', config('wunzi.case_readiness.blocking_field_statuses', [
                CriticalFieldStatus::NEEDS_CONFIRMATION->value,
            ]));
    }
}
