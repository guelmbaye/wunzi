<?php

namespace App\Services\Safety;

use App\Exceptions\HallucinationViolationException;

/**
 * Every factual statement in a case packet must belong to exactly one of:
 *   SOURCE_CLAIM | DERIVED_RELATION | MISSING_INFORMATION | SYSTEM_METADATA
 * Generated facts with no provenance are forbidden.
 */
class HallucinationValidator
{
    public const ALLOWED_KINDS = [
        'SOURCE_CLAIM',
        'DERIVED_RELATION',
        'MISSING_INFORMATION',
        'SYSTEM_METADATA',
    ];

    /**
     * @param  array<int, array{text:string, kind?:string, claim_id?:string, issue_id?:string}>  $statements
     * @param  array<int, string>  $knownClaimIds
     * @param  array<int, string>  $knownIssueIds
     * @return array<int, string> unbacked statements
     */
    public function validate(array $statements, array $knownClaimIds, array $knownIssueIds): array
    {
        $unbacked = [];

        foreach ($statements as $statement) {
            $kind = $statement['kind'] ?? null;

            if (! in_array($kind, self::ALLOWED_KINDS, true)) {
                $unbacked[] = $statement['text'] ?? '(unnamed statement)';

                continue;
            }

            if ($kind === 'SYSTEM_METADATA' || $kind === 'MISSING_INFORMATION') {
                continue;
            }

            $claimOk = isset($statement['claim_id']) && in_array($statement['claim_id'], $knownClaimIds, true);
            $issueOk = isset($statement['issue_id']) && in_array($statement['issue_id'], $knownIssueIds, true);

            if (! $claimOk && ! $issueOk) {
                $unbacked[] = $statement['text'] ?? '(unnamed statement)';
            }
        }

        return $unbacked;
    }

    /** @throws HallucinationViolationException */
    public function assert(array $statements, array $knownClaimIds, array $knownIssueIds): void
    {
        $unbacked = $this->validate($statements, $knownClaimIds, $knownIssueIds);

        if ($unbacked !== []) {
            throw new HallucinationViolationException($unbacked);
        }
    }
}
