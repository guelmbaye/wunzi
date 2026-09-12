<?php

namespace App\Enums;

/** Negation is a first-class semantic class: losing it reverses a claim. */
enum Polarity: string
{
    case POSITIVE = 'POSITIVE';
    case NEGATIVE = 'NEGATIVE';
    case UNCLEAR = 'UNCLEAR';
}
