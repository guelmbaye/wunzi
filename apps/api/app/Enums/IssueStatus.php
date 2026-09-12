<?php

namespace App\Enums;

enum IssueStatus: string
{
    case AGREED = 'AGREED';
    case DISPUTED = 'DISPUTED';
    case MISSING = 'MISSING';
    case UNVERIFIED = 'UNVERIFIED';
}
