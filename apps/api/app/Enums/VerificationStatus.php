<?php

namespace App\Enums;

/**
 * Never TRUE / FALSE. Speaker verification only asserts that WUNZI captured the
 * speaker's intended claim — not that the claim is objectively true.
 */
enum VerificationStatus: string
{
    case UNVERIFIED = 'UNVERIFIED';
    case CONFIRMED_BY_SPEAKER = 'CONFIRMED_BY_SPEAKER';
    case CORRECTED_BY_SPEAKER = 'CORRECTED_BY_SPEAKER';
    case UNRESOLVED = 'UNRESOLVED';
}
