<?php

namespace App\Enums;

enum IssueRelationship: string
{
    case SUPPORTS = 'SUPPORTS';
    case CONFLICTS = 'CONFLICTS';
    case REQUIRES = 'REQUIRES';
}
