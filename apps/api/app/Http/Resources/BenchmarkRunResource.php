<?php

namespace App\Http\Resources;

use Illuminate\Http\Resources\Json\JsonResource;

class BenchmarkRunResource extends JsonResource
{
    public function toArray($request): array
    {
        return [
            'id' => $this->id,
            'name' => $this->name,
            'dataset_version' => $this->dataset_version,
            'split' => $this->split,
            'pipeline_version' => $this->pipeline_version,
            'prompt_version' => $this->prompt_version,
            'git_commit' => $this->git_commit,
            'providers' => $this->providers,
            'guard_enabled' => $this->guard_enabled,
            'status' => $this->status->value,
            'results' => $this->results,
            'sponsor_outcome_delta' => $this->sponsor_outcome_delta,
            'sponsor_outcome_delta_unit' => 'percentage_points',
            'best_competitor' => $this->best_competitor,
            'sponsor_necessity_verdict' => $this->sponsorNecessityVerdict(),
            'threshold_note' => 'The +10 pt target is an internal WUNZI anti-MIRROR-OPS discipline, not an official Intron criterion.',
            'metrics' => $this->whenLoaded('metrics', fn () => $this->metrics->map(fn ($m) => [
                'provider' => $m->provider,
                'metric' => $m->metric,
                'value' => $m->value,
                'ci_low' => $m->ci_low,
                'ci_high' => $m->ci_high,
                'scope' => $m->scope,
                'sample_count' => $m->sample_count,
            ])),
            'started_at' => $this->started_at,
            'completed_at' => $this->completed_at,
        ];
    }
}
