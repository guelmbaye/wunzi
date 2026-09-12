<?php

namespace Tests\Unit;

use App\Enums\CaseStatus;
use PHPUnit\Framework\TestCase;

class CaseStateMachineTest extends TestCase
{
    public function test_draft_can_only_move_to_party_a_capture(): void
    {
        $this->assertTrue(CaseStatus::DRAFT->canTransitionTo(CaseStatus::PARTY_A_CAPTURE));
        $this->assertFalse(CaseStatus::DRAFT->canTransitionTo(CaseStatus::READY));
        $this->assertFalse(CaseStatus::DRAFT->canTransitionTo(CaseStatus::ISSUE_GRAPH_READY));
    }

    public function test_ready_is_terminal(): void
    {
        $this->assertSame([], CaseStatus::READY->allowedNext());
    }

    public function test_issue_graph_can_fall_back_to_verification(): void
    {
        $this->assertTrue(CaseStatus::ISSUE_GRAPH_READY->canTransitionTo(CaseStatus::VERIFICATION_REQUIRED));
    }
}
