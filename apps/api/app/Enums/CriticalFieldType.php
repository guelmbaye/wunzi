<?php

namespace App\Enums;

enum CriticalFieldType: string
{
    case AMOUNT = 'AMOUNT';
    case DATE = 'DATE';
    case PERSON = 'PERSON';
    case NEGATION = 'NEGATION';
    case COMMITMENT = 'COMMITMENT';
    case OWNERSHIP = 'OWNERSHIP';
    case RESPONSIBILITY = 'RESPONSIBILITY';
    case REQUESTED_OUTCOME = 'REQUESTED_OUTCOME';
    case CASE_REFERENCE = 'CASE_REFERENCE';
    case QUOTED_STATEMENT = 'QUOTED_STATEMENT';
}
