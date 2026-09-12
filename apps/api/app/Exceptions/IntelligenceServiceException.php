<?php

namespace App\Exceptions;

use RuntimeException;

class IntelligenceServiceException extends RuntimeException
{
    public function __construct(
        string $message,
        public readonly ?string $endpoint = null,
        public readonly ?int $statusCode = null,
    ) {
        parent::__construct($message);
    }
}
