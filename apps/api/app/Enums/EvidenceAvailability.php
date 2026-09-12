<?php

namespace App\Enums;

enum EvidenceAvailability: string
{
    case AVAILABLE = 'AVAILABLE';
    case MENTIONED_NOT_PROVIDED = 'MENTIONED_NOT_PROVIDED';
    case MISSING = 'MISSING';
    case DISPUTED = 'DISPUTED';
}
