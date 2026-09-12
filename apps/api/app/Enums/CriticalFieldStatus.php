<?php

namespace App\Enums;

enum CriticalFieldStatus: string
{
    case ACCEPTED = 'ACCEPTED';
    case NEEDS_CONFIRMATION = 'NEEDS_CONFIRMATION';
    case CONFIRMED = 'CONFIRMED';
    case CORRECTED = 'CORRECTED';
    case UNRESOLVED = 'UNRESOLVED';

    public function blocksCaseReadiness(): bool
    {
        return in_array($this->value, config('wunzi.case_readiness.blocking_field_statuses', []), true);
    }
}
