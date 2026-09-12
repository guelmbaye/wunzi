<?php

namespace App\Enums;

enum AsrProvider: string
{
    case SAHARA = 'sahara';
    case WHISPER = 'whisper';
    case MODEL_B = 'model_b';
    case MODEL_C = 'model_c';

    public function isSponsor(): bool
    {
        return $this === self::SAHARA;
    }

    /** @return array<int, self> */
    public static function benchmarkSet(): array
    {
        return [self::SAHARA, self::WHISPER, self::MODEL_B, self::MODEL_C];
    }
}
