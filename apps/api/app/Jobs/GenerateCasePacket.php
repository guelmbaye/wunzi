<?php

namespace App\Jobs;

use App\Models\MediationCase;
use App\Services\Intelligence\CasePacketService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;

class GenerateCasePacket implements ShouldQueue
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 2;
    public int $timeout = 300;

    public function __construct(public string $caseId)
    {
    }

    public function handle(CasePacketService $packets): void
    {
        $packets->generate(MediationCase::findOrFail($this->caseId));
    }
}
