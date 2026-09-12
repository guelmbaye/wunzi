<?php

use App\Http\Middleware\LogAuditContext;
use Illuminate\Foundation\Application;
use Illuminate\Foundation\Configuration\Exceptions;
use Illuminate\Foundation\Configuration\Middleware;

return Application::configure(basePath: dirname(__DIR__))
    ->withRouting(
        web: __DIR__.'/../routes/web.php',
        api: __DIR__.'/../routes/api.php',
        commands: __DIR__.'/../routes/console.php',
        health: '/up',
    )
    ->withMiddleware(function (Middleware $middleware) {
        $middleware->api(prepend: [

        ]);
        $middleware->api(append: [
            LogAuditContext::class,
        ]);
    })
    ->withExceptions(function (Exceptions $exceptions) {
        $exceptions->render(function (\App\Exceptions\IntelligenceServiceException $e) {
            return response()->json([
                'error' => 'intelligence_service_unavailable',
                'message' => $e->getMessage(),
                'retryable' => true,
            ], 503);
        });
        $exceptions->render(function (\App\Exceptions\InvalidCaseTransitionException $e) {
            return response()->json([
                'error' => 'invalid_case_transition',
                'message' => $e->getMessage(),
            ], 422);
        });
        $exceptions->render(function (\App\Exceptions\NeutralityViolationException $e) {
            return response()->json([
                'error' => 'neutrality_violation',
                'message' => $e->getMessage(),
            ], 422);
        });
    })->create();
