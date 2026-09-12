<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('mediation_cases', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->string('public_reference')->unique();   // WZ-024
            $table->string('category')->default('rental_deposit_dispute');
            $table->string('status')->default('DRAFT')->index();
            $table->string('title');
            $table->string('language_configuration')->default('rw-en-fr');
            $table->foreignId('created_by')->nullable()->constrained('users')->nullOnDelete();
            $table->string('pipeline_version')->nullable();
            $table->timestamps();
            $table->softDeletes();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('mediation_cases');
    }
};
