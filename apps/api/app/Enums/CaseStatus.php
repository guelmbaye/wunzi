<?php

namespace App\Enums;

enum CaseStatus: string
{
    case DRAFT = 'DRAFT';
    case PARTY_A_CAPTURE = 'PARTY_A_CAPTURE';
    case PARTY_B_CAPTURE = 'PARTY_B_CAPTURE';
    case VERIFICATION_REQUIRED = 'VERIFICATION_REQUIRED';
    case ISSUE_GRAPH_READY = 'ISSUE_GRAPH_READY';
    case MEDIATOR_REVIEW = 'MEDIATOR_REVIEW';
    case READY = 'READY';

    /** Allowed forward transitions. The machine never skips required verification. */
    public function allowedNext(): array
    {
        return match ($this) {
            self::DRAFT => [self::PARTY_A_CAPTURE],
            self::PARTY_A_CAPTURE => [self::PARTY_B_CAPTURE, self::VERIFICATION_REQUIRED],
            self::PARTY_B_CAPTURE => [self::VERIFICATION_REQUIRED, self::ISSUE_GRAPH_READY],
            self::VERIFICATION_REQUIRED => [self::PARTY_B_CAPTURE, self::ISSUE_GRAPH_READY],
            self::ISSUE_GRAPH_READY => [self::MEDIATOR_REVIEW, self::VERIFICATION_REQUIRED],
            self::MEDIATOR_REVIEW => [self::READY, self::VERIFICATION_REQUIRED],
            self::READY => [],
        };
    }

    public function canTransitionTo(self $target): bool
    {
        return in_array($target, $this->allowedNext(), true);
    }
}
