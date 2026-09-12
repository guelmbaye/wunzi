<?php

namespace App\Http\Resources;

use Illuminate\Http\Resources\Json\JsonResource;

class TranscriptRunResource extends JsonResource
{
    public function toArray($request): array
    {
        return [
            'id' => $this->id,
            'provider' => $this->provider->value,
            'model' => $this->model,
            'is_primary' => $this->is_primary,
            'latency_ms' => $this->latency_ms,
            'source_mode' => $this->source_mode,
            'fixture_origin' => $this->fixture_origin,
            'transcript' => $this->normalized_transcript,
            'segments' => $this->whenLoaded('segments', fn () => $this->segments->map(fn ($s) => [
                'id' => $s->id,
                'sequence' => $s->sequence,
                'start_ms' => $s->start_ms,
                'end_ms' => $s->end_ms,
                'text' => $s->text,
                'language' => $s->language_code,
                'confidence' => $s->confidence,
            ])),
        ];
    }
}
