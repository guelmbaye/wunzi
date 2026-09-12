<?php

namespace App\Services;

use App\Enums\AuditAction;
use App\Models\AuditEvent;
use Illuminate\Support\Facades\Auth;
use Illuminate\Support\Facades\Log;

class AuditLogger
{
    public function record(
        AuditAction $action,
        string $entityType,
        ?string $entityId = null,
        ?string $caseId = null,
        ?array $before = null,
        ?array $after = null,
        string $actorType = 'system',
    ): AuditEvent {
        $event = AuditEvent::create([
            'case_id' => $caseId,
            'actor_type' => Auth::id() ? 'user' : $actorType,
            'actor_user_id' => Auth::id(),
            'entity_type' => $entityType,
            'entity_id' => $entityId,
            'action' => $action->value,
            'before' => $before,
            'after' => $after,
            'request_id' => request()?->header('X-Request-Id'),
            'created_at' => now(),
        ]);

        // Structured log — never contains raw audio or full transcripts.
        Log::info('audit', [
            'event' => 'audit.'.strtolower($action->value),
            'case_id' => $caseId,
            'entity_type' => $entityType,
            'entity_id' => $entityId,
        ]);

        return $event;
    }
}
