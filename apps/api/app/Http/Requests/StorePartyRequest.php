<?php

namespace App\Http\Requests;

use Illuminate\Foundation\Http\FormRequest;
use Illuminate\Validation\Rule;

class StorePartyRequest extends FormRequest
{
    public function authorize(): bool
    {
        return true;
    }

    public function rules(): array
    {
        return [
            'role' => ['required', Rule::in(['PARTY_A', 'PARTY_B'])],
            'display_name' => ['required', 'string', 'max:120'],
            'contact_reference' => ['nullable', 'string', 'max:120'],
            'consent_status' => ['sometimes', Rule::in(['PENDING', 'GRANTED', 'WITHDRAWN'])],
        ];
    }
}
