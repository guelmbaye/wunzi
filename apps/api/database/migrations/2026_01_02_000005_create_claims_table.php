<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('claims', function (Blueprint $table) {
            $table->uuid('id')->primary();
            $table->foreignUuid('case_id')->constrained('mediation_cases')->cascadeOnDelete();
            $table->foreignUuid('party_id')->constrained('parties')->cascadeOnDelete();
            $table->foreignUuid('transcript_run_id')->nullable()->constrained('transcript_runs')->nullOnDelete();

            $table->string('type')->index();              // canonical claim type
            $table->string('subject_ref')->nullable();    // party_b | third_party:xxx
            $table->string('predicate');
            $table->json('canonical_value')->nullable();
            $table->string('polarity')->default('POSITIVE');
            $table->string('certainty')->default('asserted');
            $table->string('criticality')->default('MEDIUM')->index();
            $table->string('verification_status')->default('UNVERIFIED')->index();
            $table->decimal('extraction_confidence', 5, 4)->nullable();
            $table->decimal('attribution_confidence', 5, 4)->nullable();
            $table->boolean('reported_speech')->default(false);

            // Self-correction handling: "the tenth… no, the twelfth of August".
            // The foreign key is added below, not here — see the note in up().
            $table->uuid('superseded_by')->nullable();
            $table->boolean('is_superseded')->default(false);

            $table->string('extraction_version')->nullable();
            $table->boolean('mediator_corrected')->default(false);
            $table->timestamps();
        });

        /*
         * The self-referencing key must be added in a second statement.
         *
         * Laravel appends fluent index commands (here, `uuid('id')->primary()`)
         * to the END of the blueprint's command list, after every foreign key
         * declared inside the closure. On PostgreSQL that produces:
         *
         *     CREATE TABLE claims (...)
         *     ALTER TABLE claims ADD CONSTRAINT ... FOREIGN KEY (superseded_by)
         *                        REFERENCES claims (id)      <- fails here
         *     ALTER TABLE claims ADD PRIMARY KEY (id)        <- too late
         *
         * SQLSTATE 42830: no unique constraint matching the given keys. A key
         * pointing at another table is fine because that table's primary key
         * already exists; only a self-reference lands before its own.
         */
        Schema::table('claims', function (Blueprint $table) {
            // PostgreSQL does not index a foreign key column automatically, and
            // ON DELETE SET NULL scans the referencing table on every delete.
            // Claims cascade when a case is removed, so without this the delete
            // is quadratic in the number of claims.
            $table->index('superseded_by');

            $table->foreign('superseded_by')
                ->references('id')
                ->on('claims')
                ->nullOnDelete();
        });
    }

    public function down(): void
    {
        // Drop the self-reference first: PostgreSQL will not drop a table that
        // still holds a constraint pointing at itself while other objects
        // depend on it.
        if (Schema::hasTable('claims')) {
            Schema::table('claims', function (Blueprint $table) {
                $table->dropForeign(['superseded_by']);
            });
        }

        Schema::dropIfExists('claims');
    }
};
