<?php

return [
    /*
     | Runtime mode.
     |   live    → real provider calls
     |   fixture → replay of previously observed authentic provider outputs.
     | Fixture mode NEVER fabricates results: every replayed payload keeps its
     | `fixture_origin` (run id + capture date) in transcript_runs.raw_payload.
     */
    'mode' => env('WUNZI_MODE', 'fixture'),

    'dataset_version' => env('DATASET_VERSION', 'dataset-v1'),
    'pipeline_version' => env('PIPELINE_VERSION', 'pipeline-v1'),

    'intelligence' => [
        'base_url' => env('INTELLIGENCE_BASE_URL', 'http://intelligence:8001'),
        'secret' => env('INTERNAL_AI_SERVICE_SECRET', 'change-me'),
        // Must exceed FastAPI's own worst case (ASR timeout x its retries),
        // otherwise Laravel abandons work the provider was already paid for.
        'timeout' => (int) env('INTELLIGENCE_TIMEOUT', 300),
        'connect_timeout' => (int) env('INTELLIGENCE_CONNECT_TIMEOUT', 5),
        // Applied ONLY to endpoints with no upstream cost. Transcription is not
        // retried here: FastAPI already retries the provider, and stacking the
        // two turns one recording into nine ASR calls.
        'retries' => 2,
    ],

    'asr' => [
        'primary' => env('DEFAULT_ASR_PROVIDER', 'sahara'),
        'benchmark_providers' => ['sahara', 'whisper', 'model_b', 'model_c'],
    ],

    /*
     * A full run is accepted by FastAPI and polled by the queue worker. The
     * budget sits below RunBenchmark::$timeout so the deadline is reported as a
     * benchmark failure with a reason, rather than as a killed job with none.
     */
    'benchmark' => [
        'max_wait_seconds' => (int) env('BENCHMARK_MAX_WAIT_SECONDS', 3300),
    ],

    'audio' => [
        'disk' => env('FILESYSTEM_DISK', 's3'),
        'path_template' => 'cases/{case}/parties/{party}/{audio}.{ext}',
        'signed_url_ttl_minutes' => 10,
        'max_bytes' => 40 * 1024 * 1024,
        'accepted_mimes' => ['audio/webm', 'audio/ogg', 'audio/wav', 'audio/x-wav', 'audio/mpeg', 'audio/mp4', 'audio/flac'],
    ],

    /*
     | Canonical issue ontology — deliberately tiny (Rental Deposit MVP).
     | Do NOT grow this into a general legal ontology for the challenge.
     */
    'issue_types' => [
        'deposit_exists',
        'deposit_amount',
        'deposit_payment_date',
        'tenancy_end_date',
        'property_return_date',
        'damage_exists',
        'damage_responsibility',
        'repair_cost',
        'repair_evidence',
        'refund_commitment',
        'refund_amount',
        'refund_deadline',
        'requested_outcome',
    ],

    'critical_issue_types' => [
        'deposit_amount',
        'refund_commitment',
        'damage_responsibility',
        'tenancy_end_date',
        'repair_cost',
        'requested_outcome',
    ],

    /*
     | Neutrality guard. Any generated prose containing these patterns is
     | rejected before persistence (SR-01..SR-03).
     */
    'neutrality' => [
        'blocked_patterns' => [
            '/\bis lying\b/i', '/\bliar\b/i', '/\bdishonest\b/i',
            '/\bis correct\b/i', '/\bis right\b/i', '/\bis wrong\b/i',
            '/\bshould pay\b/i', '/\bmust pay\b/i', '/\bowes\b/i',
            '/\bliable\b/i', '/\bguilty\b/i', '/\bat fault\b/i',
            '/\bcredib(le|ility)\b/i', '/\btrustworth/i',
            '/\bdeserves\b/i', '/\bwe recommend (that )?(party|the)/i',
            '/\bthe truth is\b/i', '/\bproven\b/i',
        ],
        'approved_openers' => [
            'Party A states', 'Party B states', 'The accounts differ on',
            'Both accounts align on', 'No information was provided about',
            'This information remains unverified',
        ],
    ],

    'case_readiness' => [
        // A case cannot be marked READY while any critical field is still
        // NEEDS_CONFIRMATION. It MAY be ready with explicit UNRESOLVED items.
        'blocking_field_statuses' => ['NEEDS_CONFIRMATION'],
    ],
];
