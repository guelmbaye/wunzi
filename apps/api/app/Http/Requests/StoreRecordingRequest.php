<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class StoreRecordingRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'audio' => [
                'required_without:fixture_key',
                'file',
                'max:'.(int) (config('wunzi.audio.max_bytes') / 1024),
                'mimetypes:'.implode(',', config('wunzi.audio.accepted_mimes')),
            ],
            'fixture_key' => ['required_without:audio', 'nullable', 'string', 'max:120'],
            'duration_ms' => ['nullable', 'integer', 'min:0'],
            // Explicit consent is mandatory before any processing.
            'consent_recorded' => ['required', 'accepted'],
            'provider' => ['sometimes', Rule::in(['sahara', 'whisper', 'model_b', 'model_c'])],
        ];
    }

    public function messages(): array
    {
        return [
            'consent_recorded.accepted' => 'Explicit recording and AI-processing consent is required before capture.',
        ];
    }
}
