<?php

namespace App\Enums;

enum ConsentStatus: string
{
    case PENDING = 'PENDING';
    case GRANTED = 'GRANTED';
    case WITHDRAWN = 'WITHDRAWN';
}
