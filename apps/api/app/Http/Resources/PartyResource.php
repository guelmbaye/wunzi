<?php

namespace App\Http\Resources;

use Illuminate\Http\Resources\Json\JsonResource;

class PartyResource extends JsonResource
{
    public function toArray($request): array
    {
        return [
            'id' => $this->id,
            'role' => $this->role->value,
            'display_name' => $this->display_name,
            'consent_status' => $this->consent_status->value,
            'consent_recorded_at' => $this->consent_recorded_at,
        ];
    }
}
