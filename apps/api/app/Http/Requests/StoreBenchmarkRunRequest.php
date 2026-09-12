<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class StoreBenchmarkRunRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'name' => ['required', 'string', 'max:120'],
            'dataset_version' => ['sometimes', 'string', 'max:60'],
            'split' => ['sometimes', Rule::in(['development', 'holdout'])],
            'providers' => ['sometimes', 'array', 'min:4'],
            'providers.*' => [Rule::in(['sahara', 'whisper', 'model_b', 'model_c'])],
            'guard_enabled' => ['sometimes', 'boolean'],
        ];
    }

    public function messages(): array
    {
        return [
            'providers.min' => 'The challenge requires Sahara benchmarked against at least three other speech models.',
        ];
    }
}
