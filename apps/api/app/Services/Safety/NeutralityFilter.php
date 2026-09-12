<?php

namespace App\Services\Safety;

use App\Exceptions\NeutralityViolationException;

/**
 * Guard layer, not a comprehensive legal policy. Blocks adjudicative language
 * before any generated prose is persisted (SR-01, SR-02, SR-03).
 */
class NeutralityFilter
{
    /** @return array<int, string> matched forbidden fragments */
    public function scan(string $text): array
    {
        $matches = [];

        foreach (config('wunzi.neutrality.blocked_patterns', []) as $pattern) {
            if (preg_match($pattern, $text, $found)) {
                $matches[] = trim($found[0]);
            }
        }

        return array_values(array_unique($matches));
    }

    public function passes(string $text): bool
    {
        return $this->scan($text) === [];
    }

    /** @throws NeutralityViolationException */
    public function assert(string $text): void
    {
        $matches = $this->scan($text);

        if ($matches !== []) {
            throw new NeutralityViolationException($matches);
        }
    }

    /** Recursively scans every string in a generated packet payload. */
    public function assertPayload(array $payload): void
    {
        $violations = [];

        array_walk_recursive($payload, function ($value) use (&$violations) {
            if (is_string($value)) {
                $violations = array_merge($violations, $this->scan($value));
            }
        });

        $violations = array_values(array_unique($violations));

        if ($violations !== []) {
            throw new NeutralityViolationException($violations);
        }
    }
}
