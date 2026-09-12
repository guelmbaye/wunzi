<?php

use App\Http\Controllers\Api\AuthController;
use App\Http\Controllers\Api\BenchmarkController;
use App\Http\Controllers\Api\CaseController;
use App\Http\Controllers\Api\CasePacketController;
use App\Http\Controllers\Api\ClaimController;
use App\Http\Controllers\Api\IssueController;
use App\Http\Controllers\Api\PartyController;
use App\Http\Controllers\Api\RecordingController;
use App\Http\Controllers\Api\ResponsibleAiController;
use App\Http\Controllers\Api\VerificationController;
use App\Services\Intelligence\IntelligenceClient;
use Illuminate\Support\Facades\Route;

Route::post('/auth/login', [AuthController::class, 'login'])->name('api.auth.login');
Route::get('/responsible-ai', [ResponsibleAiController::class, 'show'])->name('api.responsible-ai');

Route::get('/health', function (IntelligenceClient $client) {
    try {
        $intelligence = $client->health();
        $intelligenceOk = true;
    } catch (\Throwable $e) {
        $intelligence = ['error' => $e->getMessage()];
        $intelligenceOk = false;
    }

    return response()->json([
        'api' => 'ok',
        'mode' => config('wunzi.mode'),
        'pipeline_version' => config('wunzi.pipeline_version'),
        'intelligence' => $intelligence,
    ], $intelligenceOk ? 200 : 503);
})->name('api.health');

Route::middleware('auth:sanctum')->group(function () {
    Route::get('/auth/me', [AuthController::class, 'me'])->name('api.auth.me');
    Route::post('/auth/logout', [AuthController::class, 'logout'])->name('api.auth.logout');

    // ── Cases ────────────────────────────────────────────────────────────
    Route::get('/cases', [CaseController::class, 'index'])->name('api.cases.index');
    Route::post('/cases', [CaseController::class, 'store'])->name('api.cases.store');
    Route::get('/cases/{case}', [CaseController::class, 'show'])->name('api.cases.show');
    Route::get('/cases/{case}/overview', [CaseController::class, 'overview'])->name('api.cases.overview');
    Route::delete('/cases/{case}', [CaseController::class, 'destroy'])->name('api.cases.destroy');

    // ── Parties & capture ────────────────────────────────────────────────
    Route::post('/cases/{case}/parties', [PartyController::class, 'store'])->name('api.parties.store');
    Route::post('/parties/{party}/consent', [PartyController::class, 'consent'])->name('api.parties.consent');
    Route::get('/cases/{case}/recordings', [RecordingController::class, 'index'])->name('api.recordings.index');
    Route::post('/parties/{party}/recordings', [RecordingController::class, 'store'])->name('api.recordings.store');
    Route::get('/recordings/{recording}', [RecordingController::class, 'show'])->name('api.recordings.show');
    Route::get('/recordings/{recording}/stream', [RecordingController::class, 'stream'])->name('api.recordings.stream');

    // ── Claims & provenance ──────────────────────────────────────────────
    Route::get('/cases/{case}/claims', [ClaimController::class, 'index'])->name('api.claims.index');
    Route::get('/claims/{claim}/audio-source', [ClaimController::class, 'audioSource'])->name('api.claims.audio-source');
    Route::patch('/claims/{claim}', [ClaimController::class, 'correct'])->name('api.claims.correct');

    // ── Critical Speech Guard ────────────────────────────────────────────
    Route::get('/cases/{case}/verifications', [VerificationController::class, 'index'])->name('api.verifications.index');
    Route::post('/verifications/{field}/resolve', [VerificationController::class, 'resolve'])->name('api.verifications.resolve');

    // ── Mediation Issue Graph ────────────────────────────────────────────
    Route::get('/cases/{case}/issues', [IssueController::class, 'index'])->name('api.issues.index');
    Route::post('/cases/{case}/build-issues', [IssueController::class, 'build'])->name('api.issues.build');
    Route::patch('/issues/{issue}/override', [IssueController::class, 'override'])->name('api.issues.override');

    // ── Downstream action ────────────────────────────────────────────────
    Route::post('/cases/{case}/create-packet', [CasePacketController::class, 'store'])->name('api.packets.store');
    Route::get('/cases/{case}/packet', [CasePacketController::class, 'show'])->name('api.packets.show');
    Route::get('/cases/{case}/packet/export', [CasePacketController::class, 'export'])->name('api.packets.export');

    // ── Sponsor proof ────────────────────────────────────────────────────
    Route::get('/benchmark-runs', [BenchmarkController::class, 'index'])->name('api.benchmark.index');
    Route::post('/benchmark-runs', [BenchmarkController::class, 'store'])->name('api.benchmark.store');
    Route::get('/benchmark-runs/{benchmarkRun}', [BenchmarkController::class, 'show'])->name('api.benchmark.show');
    Route::get('/benchmark-runs/{benchmarkRun}/dashboard', [BenchmarkController::class, 'dashboard'])->name('api.benchmark.dashboard');
    Route::get('/benchmark-runs/{benchmarkRun}/same-audio', [BenchmarkController::class, 'sameAudio'])->name('api.benchmark.same-audio');
    Route::get('/benchmark-runs/{benchmarkRun}/observations', [BenchmarkController::class, 'observations'])->name('api.benchmark.observations');
});
