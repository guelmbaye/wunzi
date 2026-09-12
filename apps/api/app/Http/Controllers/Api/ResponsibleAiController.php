<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use Illuminate\Http\JsonResponse;

/** Machine-readable version of the Responsible AI panel. */
class ResponsibleAiController extends Controller
{
    public function show(): JsonResponse
    {
        return response()->json([
            'product' => 'WUNZI — Switch-Aware Mediation Case Intelligence',
            'safety_principle' => 'AI structures. Humans mediate.',
            'wunzi_may' => [
                'transcribe code-switched speech',
                'reconstruct atomic claims',
                'attribute claims to a speaker and a subject',
                'identify contradictions between accounts',
                'identify information gaps',
                'request targeted factual confirmation',
                'create a structured case packet',
                'route a case to a human mediator',
            ],
            'wunzi_must_not' => [
                'determine truth',
                'decide credibility',
                'recommend guilt or liability',
                'predict who will win',
                'choose a settlement amount',
                'issue legal advice',
                'autonomously resolve a dispute',
            ],
            'guarantees' => [
                'verification_semantics' => 'Speaker confirmation means WUNZI captured the intended claim correctly, not that the claim is true.',
                'provenance' => 'Every consequential claim remains linked to its source audio segment.',
                'uncertainty' => 'Material uncertainty on a critical field blocks case readiness until resolved or explicitly marked unresolved.',
                'neutrality' => 'Generated prose is scanned for adjudicative language and regenerated if it fails.',
                'hallucination' => 'Every factual statement in a packet must reference a claim, an issue or system metadata.',
                'data_minimisation' => 'Only information required for case preparation is retained; cases can be deleted with their audio.',
            ],
            'limitations' => [
                'The challenge dataset is small and domain-specific (rental deposit disputes).',
                'WUNZI makes no claim of general legal reliability.',
                'The prototype is independent and is not an official government deployment.',
            ],
        ]);
    }
}
