<?php

namespace App\Http\Resources;

use Illuminate\Http\Resources\Json\JsonResource;

class CasePacketResource extends JsonResource
{
    public function toArray($request): array
    {
        return [
            'id' => $this->id,
            'case_id' => $this->case_id,
            'version' => $this->version,
            'payload' => $this->payload,
            'provenance_index' => $this->provenance_index,
            'checks' => [
                'neutrality' => $this->neutrality_check_passed,
                'hallucination' => $this->hallucination_check_passed,
            ],
            'generated_at' => $this->generated_at,
            'status_label' => 'Ready for Human Mediator',
        ];
    }
}
