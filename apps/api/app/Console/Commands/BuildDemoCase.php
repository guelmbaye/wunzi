<?php

namespace App\Console\Commands;

use App\Enums\AsrProvider;
use App\Enums\CaseStatus;
use App\Enums\ConsentStatus;
use App\Enums\PartyRole;
use App\Enums\ProcessingStatus;
use App\Models\AudioRecording;
use App\Models\MediationCase;
use App\Models\Party;
use App\Models\User;
use App\Services\CaseStateMachine;
use App\Services\Intelligence\ClaimIngestionService;
use App\Services\Intelligence\IssueGraphService;
use App\Services\Intelligence\TranscriptionService;
use Illuminate\Console\Command;
use Illuminate\Support\Str;

/**
 * Builds the deterministic demo case from consented fixture recordings.
 * Demo mode never fabricates results: fixtures replay previously observed
 * provider outputs and keep their fixture_origin.
 */
class BuildDemoCase extends Command
{
    protected $signature = 'wunzi:demo-case
                            {--fixture-a=WZ_DEMO_001_A : Party A fixture key}
                            {--fixture-b=WZ_DEMO_001_B : Party B fixture key}
                            {--provider=sahara : Primary ASR provider}';

    protected $description = 'Create the WUNZI demo rental-deposit case from fixture audio';

    public function handle(
        TranscriptionService $transcription,
        ClaimIngestionService $ingestion,
        IssueGraphService $issueGraph,
        CaseStateMachine $stateMachine,
    ): int {
        $provider = AsrProvider::from($this->option('provider'));
        $mediator = User::firstOrCreate(
            ['email' => 'mediator@wunzi.demo'],
            ['name' => 'Demo Mediator', 'password' => bcrypt('wunzi-demo'), 'role' => 'MEDIATOR']
        );

        $case = MediationCase::create([
            'public_reference' => 'WZ-'.str_pad((string) (MediationCase::count() + 1), 3, '0', STR_PAD_LEFT),
            'title' => 'Rental Deposit Dispute — Demo',
            'category' => 'rental_deposit_dispute',
            'language_configuration' => 'rw-en-fr',
            'status' => CaseStatus::DRAFT,
            'created_by' => $mediator->id,
            'pipeline_version' => config('wunzi.pipeline_version'),
        ]);

        $this->info("Created case {$case->public_reference}");

        foreach ([
            [PartyRole::PARTY_A, 'Party A', $this->option('fixture-a')],
            [PartyRole::PARTY_B, 'Party B', $this->option('fixture-b')],
        ] as [$role, $name, $fixtureKey]) {
            $party = Party::create([
                'case_id' => $case->id,
                'role' => $role->value,
                'display_name' => $name,
                'consent_status' => ConsentStatus::GRANTED,
                'consent_recorded_at' => now(),
            ]);

            $recording = new AudioRecording([
                'case_id' => $case->id,
                'party_id' => $party->id,
                'disk' => 'fixtures',
                'storage_path' => 'audio/'.$fixtureKey.'.wav',
                'mime_type' => 'audio/wav',
                'sha256' => hash('sha256', $fixtureKey),
                'consent_recorded' => true,
                'processing_status' => ProcessingStatus::UPLOADED,
                'fixture_key' => $fixtureKey,
            ]);
            $recording->id = (string) Str::uuid();
            $recording->save();

            $run = $transcription->transcribe($recording, $provider, primary: true);
            $claims = $ingestion->ingest($recording, $run);

            $this->line(sprintf('  %s → %d claims (%s)', $role->value, count($claims), $provider->value));
        }

        $issues = $issueGraph->build($case);
        $stateMachine->recompute($case);

        $this->newLine();
        $this->info('Issue Map');
        foreach ($issues as $issue) {
            $this->line(sprintf('  %-24s %s', $issue->canonical_type, $issue->status->value));
        }

        $pending = $stateMachine->pendingCriticalFieldsQuery($case)->count();
        $this->newLine();
        $this->comment("{$pending} critical field(s) require confirmation before the case can be created.");
        $this->comment('Case id: '.$case->id);

        return self::SUCCESS;
    }
}
