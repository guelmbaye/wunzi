<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('issues', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('case_id')->constrained('mediation_cases')->cascadeOnDelete();
            $table->string('canonical_type')->index();
            $table->string('status');                     // AGREED | DISPUTED | MISSING | UNVERIFIED
            $table->string('criticality')->default('HIGH');
            $table->text('summary')->nullable();          // neutral prose only
            $table->string('classification_reason')->nullable(); // "normalized values differ"
            $table->json('party_a_value')->nullable();
            $table->json('party_b_value')->nullable();
            $table->decimal('comparison_confidence', 5, 4)->nullable();
            $table->boolean('mediator_overridden')->default(false);
            $table->timestamps();

            $table->unique(['case_id', 'canonical_type']);
        });

        Schema::create('issue_claims', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('issue_id')->constrained('issues')->cascadeOnDelete();
            $table->foreignUuid('claim_id')->constrained('claims')->cascadeOnDelete();
            $table->string('relationship');               // SUPPORTS | CONFLICTS | REQUIRES
            $table->timestamps();

            $table->unique(['issue_id', 'claim_id'], 'issue_claims_unique');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('issue_claims');
        Schema::dropIfExists('issues');
    }
};
