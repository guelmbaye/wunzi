<?php

namespace App\Enums;

enum ResolutionType: string
{
    case CONFIRMED = 'CONFIRMED';
    case CORRECTED = 'CORRECTED';
    case UNRESOLVED = 'UNRESOLVED';
}
