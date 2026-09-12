<?php

namespace App\Jobs;

use App\Models\MediationCase;
use App\Services\CaseStateMachine;
use App\Services\Intelligence\IssueGraphService;
use Illuminate\Bus\Queueable;
use Illuminate\Contracts\Queue\ShouldBeUnique;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Bus\Dispatchable;
use Illuminate\Queue\InteractsWithQueue;
use Illuminate\Queue\SerializesModels;
use Illuminate\Support\Facades\Cache;

/**
 * Rebuilds the Issue Graph for one case.
 *
 * The build is destructive by design — issues are deleted and recreated so the
 * graph always reflects the current claim set rather than accumulating stale
 * states. That makes concurrency dangerous: two workers finishing Party A and
 * Party B at the same moment would both delete and both rebuild, and the loser's
 * issues would vanish. Hence a unique job AND a lock around the write.
 */
class BuildIssueGraph implements ShouldQueue, ShouldBeUnique
{
    use Dispatchable, InteractsWithQueue, Queueable, SerializesModels;

    public int $tries = 2;
    public int $timeout = 300;
    public int $uniqueFor = 600;

    public function __construct(public string $caseId)
    {
    }

    public function uniqueId(): string
    {
        return $this->caseId;
    }

    public function handle(IssueGraphService $issueGraph, CaseStateMachine $stateMachine): void
    {
        $lock = Cache::lock("issue-graph:{$this->caseId}", 300);

        // Block rather than skip: a rebuild triggered by the second party's
        // claims must not be dropped just because the first one is still running.
        $lock->block(60, function () use ($issueGraph, $stateMachine) {
            $case = MediationCase::findOrFail($this->caseId);

            $issueGraph->build($case);
            $stateMachine->recompute($case);
        });
    }
}
