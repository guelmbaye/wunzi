<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('parties', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('case_id')->constrained('mediation_cases')->cascadeOnDelete();
            $table->string('role');                       // PARTY_A | PARTY_B
            $table->string('display_name');               // pseudonym only
            $table->string('contact_reference')->nullable();
            $table->string('consent_status')->default('PENDING');
            $table->timestamp('consent_recorded_at')->nullable();
            $table->timestamps();

            $table->unique(['case_id', 'role']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('parties');
    }
};
