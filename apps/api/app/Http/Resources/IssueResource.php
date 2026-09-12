<?php

namespace App\Http\Resources;

use Illuminate\Http\Resources\Json\JsonResource;

class IssueResource extends JsonResource
{
    public function toArray($request): array
    {
        return [
            'id' => $this->id,
            'canonical_type' => $this->canonical_type,
            'status' => $this->status->value,
            'criticality' => $this->criticality->value,
            'summary' => $this->summary,
            'reason' => $this->classification_reason,
            'party_a_value' => $this->party_a_value,
            'party_b_value' => $this->party_b_value,
            'mediator_overridden' => $this->mediator_overridden,
            'claims' => $this->whenLoaded('issueClaims', fn () => $this->issueClaims->map(fn ($link) => [
                'claim_id' => $link->claim_id,
                'relationship' => $link->relationship->value,
            ])),
        ];
    }
}
