<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // MVP: evidence is referenced, never analysed. No OCR, no document intelligence.
        Schema::create('evidence_references', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('case_id')->constrained('mediation_cases')->cascadeOnDelete();
            $table->foreignUuid('issue_id')->nullable()->constrained('issues')->nullOnDelete();
            $table->foreignUuid('party_id')->nullable()->constrained('parties')->nullOnDelete();
            $table->string('type');                       // repair_invoice | rental_agreement | ...
            $table->text('description')->nullable();
            $table->string('availability')->default('MISSING');
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('evidence_references');
    }
};
