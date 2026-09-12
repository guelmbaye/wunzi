<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class StoreCaseRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'title' => ['required', 'string', 'max:200'],
            'category' => ['sometimes', 'string', Rule::in(['rental_deposit_dispute'])],
            'language_configuration' => ['sometimes', 'string', 'max:32'],
            'parties' => ['sometimes', 'array', 'size:2'],
            'parties.*.role' => ['required_with:parties', Rule::in(['PARTY_A', 'PARTY_B'])],
            'parties.*.display_name' => ['required_with:parties', 'string', 'max:120'],
            'parties.*.contact_reference' => ['nullable', 'string', 'max:120'],
        ];
    }
}
