<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('benchmark_runs', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->string('name');
            $table->string('dataset_version');
            $table->string('split')->default('holdout');  // development | holdout
            $table->string('pipeline_version');
            $table->string('prompt_version')->nullable();
            $table->string('git_commit')->nullable();
            $table->json('providers');
            $table->string('status')->default('PENDING')->index();
            $table->json('results')->nullable();
            $table->decimal('sponsor_outcome_delta', 6, 2)->nullable(); // percentage points
            $table->string('best_competitor')->nullable();
            $table->boolean('guard_enabled')->default(true);
            $table->text('failure_reason')->nullable();
            $table->timestamp('started_at')->nullable();
            $table->timestamp('completed_at')->nullable();
            $table->timestamps();
        });

        Schema::create('benchmark_metrics', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('benchmark_run_id')->constrained('benchmark_runs')->cascadeOnDelete();
            $table->string('provider')->index();
            $table->string('metric')->index();            // wer | cfa | cmsr | ...
            $table->decimal('value', 8, 5);
            $table->decimal('ci_low', 8, 5)->nullable();  // bootstrap CI
            $table->decimal('ci_high', 8, 5)->nullable();
            $table->string('scope')->default('overall');  // overall | switch:high | audio:phone
            $table->unsignedInteger('sample_count')->nullable();
            $table->timestamps();

            $table->index(['benchmark_run_id', 'provider', 'metric']);
        });

        // One row per (clip, provider): the raw material of the same-audio proof.
        Schema::create('benchmark_observations', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('benchmark_run_id')->constrained('benchmark_runs')->cascadeOnDelete();
            $table->string('clip_id')->index();
            $table->string('scenario_id')->index();
            $table->string('provider')->index();
            $table->longText('transcript')->nullable();
            $table->json('critical_facts')->nullable();
            $table->json('claims')->nullable();
            $table->json('issue_states')->nullable();
            $table->json('expected_issue_states')->nullable();
            $table->boolean('case_state_correct')->nullable();
            $table->json('error_taxonomy')->nullable();   // E01..E10
            $table->unsignedInteger('latency_ms')->nullable();
            $table->boolean('provider_failed')->default(false);
            // A run scored from placeholder fixtures is a smoke test. Recording
            // it per observation means the warning cannot be lost when rows are
            // aggregated into a dashboard.
            $table->boolean('used_placeholder_fixture')->default(false);
            $table->timestamps();
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('benchmark_observations');
        Schema::dropIfExists('benchmark_metrics');
        Schema::dropIfExists('benchmark_runs');
    }
};
