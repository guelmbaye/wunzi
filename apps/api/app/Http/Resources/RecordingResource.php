<?php

namespace App\Http\Resources;

use Illuminate\Http\Resources\Json\JsonResource;

class RecordingResource extends JsonResource
{
    public function toArray($request): array
    {
        return [
            'id' => $this->id,
            'party_id' => $this->party_id,
            'duration_ms' => $this->duration_ms,
            'mime_type' => $this->mime_type,
            'processing_status' => $this->processing_status->value,
            'failure_reason' => $this->failure_reason,
            'consent_recorded' => $this->consent_recorded,
            'transcript_runs' => TranscriptRunResource::collection($this->whenLoaded('transcriptRuns')),
            'created_at' => $this->created_at,
        ];
    }
}
