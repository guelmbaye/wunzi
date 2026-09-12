<?php

namespace App\Providers;

use App\Models\BenchmarkRun;
use App\Models\Claim;
use App\Models\CriticalField;
use App\Models\Issue;
use App\Models\MediationCase;
use App\Models\Party;
use App\Models\AudioRecording;
use App\Services\Intelligence\IntelligenceClient;
use Illuminate\Support\Facades\Route;
use Illuminate\Support\ServiceProvider;

class AppServiceProvider extends ServiceProvider
{
    public function register(): void
    {
        $this->app->singleton(IntelligenceClient::class, fn () => new IntelligenceClient(
            baseUrl: config('wunzi.intelligence.base_url'),
            secret: config('wunzi.intelligence.secret'),
            timeout: (int) config('wunzi.intelligence.timeout'),
        ));
    }

    public function boot(): void
    {
        Route::model('case', MediationCase::class);
        Route::model('party', Party::class);
        Route::model('recording', AudioRecording::class);
        Route::model('claim', Claim::class);
        Route::model('field', CriticalField::class);
        Route::model('issue', Issue::class);
        Route::model('benchmarkRun', BenchmarkRun::class);
    }
}
