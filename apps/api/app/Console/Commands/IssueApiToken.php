<?php

namespace App\Console\Commands;

use App\Models\User;
use Illuminate\Console\Command;

/**
 * Mints a Sanctum token for the mediator workspace.
 *
 * The Next.js app reads cases server-side with a bearer token; there is no
 * browser login flow, because a mediation workspace should not ship one before
 * it has a real identity story. Until then the token is issued here, kept on the
 * Next server, and never sent to a browser.
 */
class IssueApiToken extends Command
{
    protected $signature = 'wunzi:token
        {--email=mediator@wunzi.demo : Account the token acts as}
        {--name=web-workspace : Label shown in the token list}
        {--revoke : Revoke existing tokens with this name first}';

    protected $description = 'Issue an API token for the Next.js workspace';

    public function handle(): int
    {
        $email = (string) $this->option('email');
        $name = (string) $this->option('name');

        $user = User::where('email', $email)->first();

        if (! $user) {
            $this->error("No account found for {$email}.");
            $this->line('Run <comment>php artisan db:seed</comment> to create the demo accounts.');

            return self::FAILURE;
        }

        if ($this->option('revoke')) {
            $removed = $user->tokens()->where('name', $name)->delete();
            $this->line("Revoked {$removed} existing token(s) named '{$name}'.");
        }

        $token = $user->createToken($name)->plainTextToken;

        $this->newLine();
        $this->info("Token issued for {$user->email}.");
        $this->newLine();
        $this->line('Add this to <comment>apps/web/.env.local</comment>:');
        $this->newLine();
        $this->line("  LARAVEL_API_URL=http://localhost:8000");
        $this->line("  WUNZI_API_TOKEN={$token}");
        $this->newLine();
        // Sanctum stores only a hash, so this is genuinely the only time the
        // plaintext exists. Saying so prevents a support round trip.
        $this->warn('This is the only time the token is shown. Re-run with --revoke to replace it.');

        return self::SUCCESS;
    }
}
