<?php

namespace App\Exceptions;

use DomainException;

class HallucinationViolationException extends DomainException
{
    /** @param array<int, string> $unbackedStatements */
    public function __construct(public readonly array $unbackedStatements)
    {
        parent::__construct(sprintf(
            '%d generated statement(s) have no source claim, issue or system metadata backing.',
            count($unbackedStatements)
        ));
    }
}
