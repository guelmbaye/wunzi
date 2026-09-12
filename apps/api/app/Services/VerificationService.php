<?php

namespace App\Services;

use App\Enums\AuditAction;
use App\Enums\CriticalFieldStatus;
use App\Enums\ResolutionType;
use App\Enums\VerificationStatus;
use App\Models\CriticalField;
use App\Models\VerificationEvent;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\DB;

/**
 * Targeted verification. Confirmation means "WUNZI captured your intended
 * claim correctly" — never "your claim is true".
 */
class VerificationService
{
    public function __construct(
        private readonly AuditLogger $audit,
        private readonly CaseStateMachine $stateMachine,
    ) {
    }

    public function resolve(
        CriticalField $field,
        ResolutionType $resolution,
        ?string $value = null,
        ?string $responseText = null,
        string $verifiedBy = 'speaker',
    ): VerificationEvent {
        return DB::transaction(function () use ($field, $resolution, $value, $responseText, $verifiedBy) {
            $previous = $field->normalized_value ?? $field->detected_value;

            $resolvedValue = match ($resolution) {
                ResolutionType::CORRECTED => $value,
                ResolutionType::CONFIRMED => $previous,
                ResolutionType::UNRESOLVED => null,
            };

            $event = VerificationEvent::create([
                'critical_field_id' => $field->id,
                'prompt_text' => $field->prompt_text ?? '',
                'response_text' => $responseText,
                'previous_value' => $previous,
                'resolved_value' => $resolvedValue,
                'resolution_type' => $resolution->value,
                'verified_by' => $verifiedBy,
                'actor_user_id' => Auth::id(),
            ]);

            $field->update([
                'status' => match ($resolution) {
                    ResolutionType::CONFIRMED => CriticalFieldStatus::CONFIRMED,
                    ResolutionType::CORRECTED => CriticalFieldStatus::CORRECTED,
                    ResolutionType::UNRESOLVED => CriticalFieldStatus::UNRESOLVED,
                },
                'normalized_value' => $resolvedValue ?? $field->normalized_value,
            ]);

            $claim = $field->claim;

            if ($resolution === ResolutionType::CORRECTED && $value !== null) {
                $canonical = $claim->canonical_value ?? [];
                $canonical['value'] = $value;
                $canonical['corrected_from'] = $previous;
                $claim->canonical_value = $canonical;
            }

            $claim->verification_status = match ($resolution) {
                ResolutionType::CONFIRMED => VerificationStatus::CONFIRMED_BY_SPEAKER,
                ResolutionType::CORRECTED => VerificationStatus::CORRECTED_BY_SPEAKER,
                ResolutionType::UNRESOLVED => VerificationStatus::UNRESOLVED,
            };
            $claim->save();

            $this->audit->record(
                action: match ($resolution) {
                    ResolutionType::CONFIRMED => AuditAction::CRITICAL_FIELD_CONFIRMED,
                    ResolutionType::CORRECTED => AuditAction::CRITICAL_FIELD_CORRECTED,
                    ResolutionType::UNRESOLVED => AuditAction::CRITICAL_FIELD_UNRESOLVED,
                },
                entityType: 'critical_field',
                entityId: $field->id,
                caseId: $claim->case_id,
                before: ['value' => $previous, 'status' => 'NEEDS_CONFIRMATION'],
                after: ['value' => $resolvedValue, 'status' => $field->fresh()->status->value],
                actorType: $verifiedBy,
            );

            $this->stateMachine->recompute($claim->mediationCase);

            return $event;
        });
    }
}
