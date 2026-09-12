<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        // Provenance chain: Issue → Claim → TranscriptSegment → Audio.
        Schema::create('claim_sources', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('claim_id')->constrained('claims')->cascadeOnDelete();
            $table->foreignUuid('transcript_segment_id')->constrained('transcript_segments')->cascadeOnDelete();
            $table->unsignedInteger('start_offset_ms')->nullable();
            $table->unsignedInteger('end_offset_ms')->nullable();
            $table->timestamps();

            $table->unique(['claim_id', 'transcript_segment_id'], 'claim_sources_unique');
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('claim_sources');
    }
};
