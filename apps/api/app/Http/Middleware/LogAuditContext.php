<?php

namespace App\Http\Middleware;

use Closure;
use Illuminate\Http\Request;
use Illuminate\Support\Str;

class LogAuditContext
{
    public function handle(Request $request, Closure $next)
    {
        if (! $request->headers->has('X-Request-Id')) {
            $request->headers->set('X-Request-Id', (string) Str::uuid());
        }

        $response = $next($request);
        $response->headers->set('X-Request-Id', $request->header('X-Request-Id'));

        return $response;
    }
}
