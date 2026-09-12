<?php

namespace App\Enums;

/** Neutral roles only. Never store legal roles (liable / victim / offender). */
enum PartyRole: string
{
    case PARTY_A = 'PARTY_A';
    case PARTY_B = 'PARTY_B';

    public function other(): self
    {
        return $this === self::PARTY_A ? self::PARTY_B : self::PARTY_A;
    }
}
