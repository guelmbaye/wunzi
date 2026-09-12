<?php

namespace Tests\Unit;

use App\Exceptions\NeutralityViolationException;
use App\Services\Safety\NeutralityFilter;
use Tests\TestCase;

class NeutralityFilterTest extends TestCase
{
    private NeutralityFilter $filter;

    protected function setUp(): void
    {
        parent::setUp();
        $this->filter = new NeutralityFilter;
    }

    public static function forbiddenPhrases(): array
    {
        return [
            ['Party B is lying about the deposit.'],
            ['The landlord is liable for the repairs.'],
            ['Party A should pay the difference.'],
            ['This claim is credible.'],
            ['Party A is correct.'],
        ];
    }

    /** @dataProvider forbiddenPhrases */
    public function test_adjudicative_language_is_blocked(string $text): void
    {
        $this->assertFalse($this->filter->passes($text));
    }

    public static function approvedPhrases(): array
    {
        return [
            ['Party A states that the deposit was 150,000 RWF.'],
            ['The accounts differ on the deposit amount.'],
            ['No information was provided about the repair invoice.'],
            ['This information remains unverified.'],
        ];
    }

    /** @dataProvider approvedPhrases */
    public function test_neutral_language_passes(string $text): void
    {
        $this->assertTrue($this->filter->passes($text));
    }

    public function test_payload_scan_throws(): void
    {
        $this->expectException(NeutralityViolationException::class);

        $this->filter->assertPayload([
            'disputed' => [
                ['summary' => 'The accounts differ on the amount.'],
                ['summary' => 'Party B is lying.'],
            ],
        ]);
    }
}
