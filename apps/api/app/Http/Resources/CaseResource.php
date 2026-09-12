<?php

namespace App\Http\Resources;

use Illuminate\Http\Resources\Json\JsonResource;

class CaseResource extends JsonResource
{
    public function toArray($request): array
    {
        return [
            'id' => $this->id,
            'public_reference' => $this->public_reference,
            'title' => $this->title,
            'category' => $this->category,
            'status' => $this->status->value,
            'language_configuration' => $this->language_configuration,
            'parties' => PartyResource::collection($this->whenLoaded('parties')),
            'counts' => $this->when(isset($this->counts), fn () => $this->counts),
            'ai_assisted' => true, // SR-07: generated structures are always identified as AI-assisted
            'human_authority_note' => 'WUNZI prepared this case. The mediator remains responsible for interpretation, dialogue and resolution.',
            'created_at' => $this->created_at,
            'updated_at' => $this->updated_at,
        ];
    }
}
