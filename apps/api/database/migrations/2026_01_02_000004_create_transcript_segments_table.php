<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('transcript_segments', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('transcript_run_id')->constrained('transcript_runs')->cascadeOnDelete();
            $table->unsignedInteger('sequence');
            $table->unsignedInteger('start_ms');
            $table->unsignedInteger('end_ms');
            $table->text('text');
            // Nullable on purpose: never fabricate provider metadata the ASR
            // does not actually expose.
            $table->string('language_code', 8)->nullable();
            $table->decimal('confidence', 5, 4)->nullable();
            $table->timestamps();

            $table->index(['transcript_run_id', 'sequence']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('transcript_segments');
    }
};
