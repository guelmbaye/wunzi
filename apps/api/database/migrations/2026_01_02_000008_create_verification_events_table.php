<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('verification_events', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('critical_field_id')->constrained('critical_fields')->cascadeOnDelete();
            $table->text('prompt_text');
            $table->text('response_text')->nullable();
            $table->string('previous_value')->nullable();
            $table->string('resolved_value')->nullable();
            $table->string('resolution_type');            // CONFIRMED | CORRECTED | UNRESOLVED
            $table->string('verified_by')->default('speaker'); // speaker | mediator
            $table->foreignId('actor_user_id')->nullable()->constrained('users')->nullOnDelete();
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('verification_events');
    }
};
