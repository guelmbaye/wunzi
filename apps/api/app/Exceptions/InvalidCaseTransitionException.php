<?php

namespace App\Exceptions;

use App\Enums\CaseStatus;
use DomainException;

class InvalidCaseTransitionException extends DomainException
{
    public static function between(CaseStatus $from, CaseStatus $to, ?string $reason = null): self
    {
        return new self(sprintf(
            'Cannot move case from %s to %s.%s',
            $from->value,
            $to->value,
            $reason ? ' '.$reason : ''
        ));
    }

    public static function pendingCriticalFields(int $count): self
    {
        return new self(sprintf(
            '%d critical field(s) still require confirmation. A case cannot be marked ready '.
            'while consequential uncertainty is unresolved.',
            $count
        ));
    }
}
