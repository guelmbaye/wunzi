<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

/** Mediator override. Human authority is explicit and always logged. */
class OverrideIssueRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'status' => ['required', Rule::in(['AGREED', 'DISPUTED', 'MISSING', 'UNVERIFIED'])],
            'note' => ['nullable', 'string', 'max:500'],
        ];
    }
}
