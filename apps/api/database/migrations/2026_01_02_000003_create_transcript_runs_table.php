<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Every ASR execution is immutable. Sahara output is never overwritten
        // by a comparison-model output.
        Schema::create('transcript_runs', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('audio_id')->constrained('audio_recordings')->cascadeOnDelete();
            $table->string('provider')->index();          // sahara | whisper | model_b | model_c
            $table->string('model')->nullable();
            $table->string('provider_version')->nullable();
            $table->string('status')->default('PENDING');
            $table->json('raw_payload')->nullable();
            $table->longText('normalized_transcript')->nullable();
            $table->unsignedInteger('latency_ms')->nullable();
            $table->string('idempotency_key')->nullable()->index();
            $table->string('source_mode')->default('live'); // live | fixture
            $table->string('fixture_origin')->nullable();   // run id + capture date
            $table->boolean('is_primary')->default(false);
            $table->timestamps();

            $table->unique(['audio_id', 'provider', 'idempotency_key'], 'transcript_runs_idem_unique');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('transcript_runs');
    }
};
