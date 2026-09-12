<?php

namespace App\Http\Resources;

use Illuminate\Http\Resources\Json\JsonResource;

class CriticalFieldResource extends JsonResource
{
    public function toArray($request): array
    {
        return [
            'id' => $this->id,
            'claim_id' => $this->claim_id,
            'field_type' => $this->field_type->value,
            'detected_value' => $this->detected_value,
            'normalized_value' => $this->normalized_value,
            'risk_level' => $this->risk_level,
            'status' => $this->status->value,
            // Neutral, non-leading prompt: "I heard X. Is that correct?"
            'prompt_text' => $this->prompt_text,
            // Internal routing signals; not shown as a user-facing probability.
            'guard_reason' => $this->guard_reason,
            'claim' => new ClaimResource($this->whenLoaded('claim')),
        ];
    }
}
