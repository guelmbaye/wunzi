<?php

namespace App\Http\Resources;

use Illuminate\Http\Resources\Json\JsonResource;

class ClaimResource extends JsonResource
{
    public function toArray($request): array
    {
        return [
            'id' => $this->id,
            'party_id' => $this->party_id,
            'party_role' => $this->whenLoaded('party', fn () => $this->party->role->value),
            'type' => $this->type,
            'subject' => $this->subject_ref,
            'predicate' => $this->predicate,
            'canonical_value' => $this->canonical_value,
            'polarity' => $this->polarity->value,
            'criticality' => $this->criticality->value,
            'verification_status' => $this->verification_status->value,
            'reported_speech' => $this->reported_speech,
            'is_superseded' => $this->is_superseded,
            'extraction_confidence' => $this->extraction_confidence,
            'attribution_confidence' => $this->attribution_confidence,
            // Attribution is never flattened into a bare fact.
            'neutral_statement' => $this->neutralStatement(),
            'has_audio_source' => $this->sources()->exists(),
            'critical_fields' => CriticalFieldResource::collection($this->whenLoaded('criticalFields')),
        ];
    }
}
