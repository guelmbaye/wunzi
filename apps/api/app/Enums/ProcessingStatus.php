<?php

namespace App\Enums;

enum ProcessingStatus: string
{
    case UPLOADED = 'UPLOADED';
    case TRANSCRIBING = 'TRANSCRIBING';
    case TRANSCRIBED = 'TRANSCRIBED';
    case EXTRACTING = 'EXTRACTING';
    case CLAIMS_READY = 'CLAIMS_READY';
    case FAILED = 'FAILED';
}
