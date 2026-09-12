<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class ResolveVerificationRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'resolution' => ['required', Rule::in(['CONFIRMED', 'CORRECTED', 'UNRESOLVED'])],
            'value' => ['required_if:resolution,CORRECTED', 'nullable', 'string', 'max:200'],
            'response_text' => ['nullable', 'string', 'max:500'],
            'verified_by' => ['sometimes', Rule::in(['speaker', 'mediator'])],
        ];
    }
}
