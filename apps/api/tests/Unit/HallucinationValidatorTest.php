<?php

namespace Tests\Unit;

use App\Services\Safety\HallucinationValidator;
use PHPUnit\Framework\TestCase;

class HallucinationValidatorTest extends TestCase
{
    public function test_statement_without_provenance_is_rejected(): void
    {
        $validator = new HallucinationValidator;

        $unbacked = $validator->validate(
            [
                ['text' => 'Party A states the deposit was 150,000 RWF.', 'kind' => 'SOURCE_CLAIM', 'claim_id' => 'c1'],
                ['text' => 'The property was damaged before the tenant arrived.', 'kind' => 'SOURCE_CLAIM', 'claim_id' => 'ghost'],
            ],
            ['c1'],
            []
        );

        $this->assertCount(1, $unbacked);
        $this->assertStringContainsString('damaged before', $unbacked[0]);
    }

    public function test_missing_information_needs_no_claim_id(): void
    {
        $validator = new HallucinationValidator;

        $this->assertSame([], $validator->validate(
            [['text' => 'No repair invoice was provided.', 'kind' => 'MISSING_INFORMATION']],
            [],
            []
        ));
    }
}
