<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('critical_fields', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('claim_id')->constrained('claims')->cascadeOnDelete();
            $table->string('field_type');                 // AMOUNT | DATE | NEGATION | ...
            $table->string('detected_value')->nullable();
            $table->string('normalized_value')->nullable();
            $table->string('risk_level')->default('HIGH');
            $table->json('guard_reason')->nullable();     // ["critical_amount","low_asr_confidence"]
            $table->string('status')->default('NEEDS_CONFIRMATION')->index();
            $table->text('prompt_text')->nullable();      // neutral, non-leading
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('critical_fields');
    }
};
