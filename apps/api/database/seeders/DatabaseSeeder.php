<?php

namespace Database\Seeders;

use App\Models\User;
use Illuminate\Database\Seeder;

class DatabaseSeeder extends Seeder
{
    public function run(): void
    {
        User::firstOrCreate(
            ['email' => 'mediator@wunzi.demo'],
            [
                'name' => 'Demo Mediator',
                'password' => bcrypt('wunzi-demo'),
                'role' => 'MEDIATOR',
                'organisation' => 'WUNZI prototype',
            ]
        );

        User::firstOrCreate(
            ['email' => 'admin@wunzi.demo'],
            [
                'name' => 'Demo Admin',
                'password' => bcrypt('wunzi-demo'),
                'role' => 'ADMIN',
                'organisation' => 'WUNZI prototype',
            ]
        );
    }
}
