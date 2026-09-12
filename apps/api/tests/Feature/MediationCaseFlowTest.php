<?php

namespace Tests\Feature;

use App\Enums\CaseStatus;
use App\Enums\CriticalFieldStatus;
use App\Exceptions\InvalidCaseTransitionException;
use App\Models\Claim;
use App\Models\CriticalField;
use App\Models\MediationCase;
use App\Models\Party;
use App\Models\User;
use App\Services\CaseStateMachine;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Laravel\Sanctum\Sanctum;
use Tests\TestCase;

class MediationCaseFlowTest extends TestCase
{
    use RefreshDatabase;

    public function test_a_case_can_be_created_with_two_parties(): void
    {
        Sanctum::actingAs(User::factory()->create());

        $response = $this->postJson('/api/cases', [
            'title' => 'Rental Deposit Dispute — Test',
            'parties' => [
                ['role' => 'PARTY_A', 'display_name' => 'Party A'],
                ['role' => 'PARTY_B', 'display_name' => 'Party B'],
            ],
        ]);

        $response->assertCreated()
            ->assertJsonPath('data.status', CaseStatus::DRAFT->value)
            ->assertJsonPath('data.ai_assisted', true);

        $this->assertDatabaseCount('parties', 2);
    }

    public function test_case_cannot_be_marked_ready_while_a_critical_field_is_pending(): void
    {
        $case = MediationCase::create([
            'public_reference' => 'WZ-999',
            'title' => 'Test',
            'status' => CaseStatus::ISSUE_GRAPH_READY,
        ]);

        $party = Party::create([
            'case_id' => $case->id,
            'role' => 'PARTY_A',
            'display_name' => 'Party A',
        ]);

        $claim = Claim::create([
            'case_id' => $case->id,
            'party_id' => $party->id,
            'type' => 'deposit_amount',
            'predicate' => 'paid_deposit',
            'canonical_value' => ['amount_minor' => 150000, 'currency' => 'RWF'],
        ]);

        CriticalField::create([
            'claim_id' => $claim->id,
            'field_type' => 'AMOUNT',
            'detected_value' => '150000',
            'status' => CriticalFieldStatus::NEEDS_CONFIRMATION,
        ]);

        $this->expectException(InvalidCaseTransitionException::class);

        app(CaseStateMachine::class)->transition($case, CaseStatus::READY, force: true);
    }

    public function test_recording_requires_explicit_consent(): void
    {
        Sanctum::actingAs(User::factory()->create());

        $case = MediationCase::create([
            'public_reference' => 'WZ-998',
            'title' => 'Test',
            'status' => CaseStatus::DRAFT,
        ]);

        $party = Party::create([
            'case_id' => $case->id,
            'role' => 'PARTY_A',
            'display_name' => 'Party A',
        ]);

        $this->postJson("/api/parties/{$party->id}/recordings", [
            'fixture_key' => 'WZ_DEMO_001_A',
            'consent_recorded' => false,
        ])->assertStatus(422);
    }
}
