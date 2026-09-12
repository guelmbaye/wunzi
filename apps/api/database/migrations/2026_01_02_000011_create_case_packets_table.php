<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('case_packets', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('case_id')->constrained('mediation_cases')->cascadeOnDelete();
            $table->unsignedInteger('version')->default(1);
            $table->json('payload');
            $table->json('provenance_index');             // sentence → claim_id / issue_id
            $table->boolean('neutrality_check_passed')->default(false);
            $table->boolean('hallucination_check_passed')->default(false);
            $table->string('generation_model')->nullable();
            $table->string('prompt_version')->nullable();
            $table->foreignId('generated_by')->nullable()->constrained('users')->nullOnDelete();
            $table->timestamp('generated_at')->nullable();
            $table->timestamps();

            $table->unique(['case_id', 'version']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('case_packets');
    }
};
