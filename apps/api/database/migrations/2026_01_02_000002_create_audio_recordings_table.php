<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('audio_recordings', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('case_id')->constrained('mediation_cases')->cascadeOnDelete();
            $table->foreignUuid('party_id')->constrained('parties')->cascadeOnDelete();
            $table->string('disk')->default('s3');
            $table->string('storage_path');
            $table->unsignedInteger('duration_ms')->nullable();
            $table->string('mime_type');
            $table->unsignedBigInteger('size_bytes')->nullable();
            $table->string('sha256', 64)->index();        // benchmark reproducibility
            $table->boolean('consent_recorded')->default(false);
            $table->string('processing_status')->default('UPLOADED')->index();
            $table->string('failure_reason')->nullable();
            $table->string('fixture_key')->nullable();    // fixture mode only
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('audio_recordings');
    }
};
