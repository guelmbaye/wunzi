<?php

namespace App\Exceptions;

use DomainException;

class NeutralityViolationException extends DomainException
{
    /** @param array<int, string> $matches */
    public function __construct(public readonly array $matches)
    {
        parent::__construct(
            'Generated content failed the neutrality guard: '.implode(', ', $matches)
        );
    }
}
