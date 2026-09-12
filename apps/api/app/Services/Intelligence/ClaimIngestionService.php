<?php

namespace App\Services\Intelligence;

use App\Enums\AuditAction;
use App\Enums\CriticalFieldStatus;
use App\Enums\ProcessingStatus;
use App\Models\AudioRecording;
use App\Models\Claim;
use App\Models\ClaimSource;
use App\Models\CriticalField;
use App\Models\TranscriptRun;
use App\Services\AuditLogger;
use Illuminate\Support\Facades\DB;

/**
 * Transcript → atomic attributed claims → Critical Speech Guard.
 * Party A and Party B are processed in complete isolation: no cross-turn
 * contamination, no premature reconciliation (blueprint §18).
 */
class ClaimIngestionService
{
    public function __construct(
        private readonly IntelligenceClient $client,
        private readonly AuditLogger $audit,
    ) {
    }

    public function ingest(AudioRecording $recording, TranscriptRun $run): array
    {
        $recording->markStatus(ProcessingStatus::EXTRACTING);

        $segments = $run->segments()->get()->map(fn ($s) => [
            'segment_id' => $s->id,
            'sequence' => $s->sequence,
            'start_ms' => $s->start_ms,
            'end_ms' => $s->end_ms,
            'text' => $s->text,
            'language' => $s->language_code,
            'confidence' => $s->confidence,
        ])->all();

        // Everything the intelligence layer needs for this turn goes out in one
        // POST: segments, ASR confidences, the canonical ontology. Extraction
        // and the guard then run back to back inside FastAPI. Splitting them
        // across two HTTP calls meant shipping the whole claim set out and
        // straight back in, doubling latency and failure surface for no gain in
        // auditability — both versions are recorded either way.
        $extraction = $this->client->analyzeTurn([
            'case_id' => $recording->case_id,
            'party_id' => $recording->party_id,
            'party_role' => $recording->party->role->value,
            'transcript_run_id' => $run->id,
            'provider' => $run->provider->value,
            'transcript' => $run->normalized_transcript,
            'segments' => $segments,
            'issue_types' => config('wunzi.issue_types'),
            'pipeline_version' => config('wunzi.pipeline_version'),
            'asr_metadata' => [
                'provider' => $run->provider->value,
                // array_column would silently re-index and lose the alignment
                // with segments; the guard reads these positionally.
                'segment_confidences' => array_map(
                    fn ($segment) => $segment['confidence'],
                    $segments
                ),
            ],
            'guard_enabled' => true,
        ]);

        $decisions = collect($extraction['decisions'] ?? [])->keyBy('claim_id');

        $created = DB::transaction(function () use ($recording, $run, $extraction, $decisions) {
            $claims = [];
            $externalToInternal = [];

            foreach (($extraction['claims'] ?? []) as $payload) {
                $claim = Claim::create([
                    'case_id' => $recording->case_id,
                    'party_id' => $recording->party_id,
                    'transcript_run_id' => $run->id,
                    'type' => $payload['type'],
                    'subject_ref' => $payload['subject'] ?? null,
                    'predicate' => $payload['predicate'],
                    'canonical_value' => $payload['canonical_value'] ?? null,
                    'polarity' => $payload['polarity'] ?? 'POSITIVE',
                    'certainty' => $payload['certainty'] ?? 'asserted',
                    'criticality' => $payload['criticality'] ?? 'MEDIUM',
                    'verification_status' => 'UNVERIFIED',
                    'extraction_confidence' => $payload['extraction_confidence'] ?? null,
                    'attribution_confidence' => $payload['attribution_confidence'] ?? null,
                    'reported_speech' => (bool) ($payload['reported_speech'] ?? false),
                    'extraction_version' => $extraction['extraction_version'] ?? null,
                ]);

                $externalToInternal[$payload['claim_id']] = $claim->id;

                foreach (($payload['source_segments'] ?? []) as $sourceSegmentId) {
                    ClaimSource::firstOrCreate([
                        'claim_id' => $claim->id,
                        'transcript_segment_id' => $sourceSegmentId,
                    ]);
                }

                $claims[] = $claim;
            }

            // Self-correction: "the tenth… no, the twelfth of August".
            foreach (($extraction['supersessions'] ?? []) as $supersession) {
                $oldId = $externalToInternal[$supersession['superseded_claim_id']] ?? null;
                $newId = $externalToInternal[$supersession['current_claim_id']] ?? null;

                if ($oldId && $newId) {
                    Claim::whereKey($oldId)->update(['is_superseded' => true, 'superseded_by' => $newId]);
                }
            }

            foreach ($claims as $claim) {
                $externalId = array_search($claim->id, $externalToInternal, true);
                $decision = $decisions->get($externalId);

                if (! $decision || ($decision['decision'] ?? 'ACCEPT_FOR_CASE') === 'ACCEPT_FOR_CASE') {
                    continue;
                }

                $status = ($decision['decision'] === 'REJECT_AS_UNRESOLVED')
                    ? CriticalFieldStatus::UNRESOLVED
                    : CriticalFieldStatus::NEEDS_CONFIRMATION;

                foreach (($decision['fields'] ?? []) as $field) {
                    $criticalField = CriticalField::create([
                        'claim_id' => $claim->id,
                        'field_type' => $field['field_type'],
                        'detected_value' => $field['detected_value'] ?? null,
                        'normalized_value' => $field['normalized_value'] ?? null,
                        'risk_level' => $decision['risk'] ?? 'HIGH',
                        'guard_reason' => $decision['reasons'] ?? [],
                        'status' => $status,
                        'prompt_text' => $field['prompt_text'] ?? null,
                    ]);

                    $this->audit->record(
                        action: AuditAction::CRITICAL_FIELD_FLAGGED,
                        entityType: 'critical_field',
                        entityId: $criticalField->id,
                        caseId: $recording->case_id,
                        after: [
                            'field_type' => $criticalField->field_type->value,
                            'reasons' => $criticalField->guard_reason,
                        ],
                    );
                }
            }

            return $claims;
        });

        $recording->markStatus(ProcessingStatus::CLAIMS_READY);

        $this->audit->record(
            action: AuditAction::CLAIM_EXTRACTED,
            entityType: 'audio_recording',
            entityId: $recording->id,
            caseId: $recording->case_id,
            after: ['claim_count' => count($created), 'provider' => $run->provider->value],
        );

        return $created;
    }
}
