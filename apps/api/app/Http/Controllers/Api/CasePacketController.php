<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Http\Resources\CasePacketResource;
use App\Jobs\GenerateCasePacket;
use App\Models\MediationCase;
use App\Services\Intelligence\CasePacketService;
use Illuminate\Http\JsonResponse;
use Illuminate\Http\Request;

class CasePacketController extends Controller
{
    public function __construct(private readonly CasePacketService $packets)
    {
    }

    /** The downstream action: create and route a structured case for human mediation. */
    public function store(Request $request, MediationCase $case): JsonResponse
    {
        if ($request->boolean('sync', true)) {
            $packet = $this->packets->generate($case);

            return (new CasePacketResource($packet))->response()->setStatusCode(201);
        }

        GenerateCasePacket::dispatch($case->id);

        return response()->json(['status' => 'queued'], 202);
    }

    public function show(MediationCase $case): JsonResponse
    {
        $packet = $case->latestPacket();

        abort_if($packet === null, 404, 'No mediation case packet has been created yet.');

        return (new CasePacketResource($packet))->response();
    }

    /** Optional technical export for judges. */
    public function export(MediationCase $case): JsonResponse
    {
        $packet = $case->latestPacket();

        abort_if($packet === null, 404);

        return response()->json([
            'case' => [
                'public_reference' => $case->public_reference,
                'category' => $case->category,
                'status' => $case->status->value,
            ],
            'packet' => $packet->payload,
            'provenance_index' => $packet->provenance_index,
            'generated_at' => $packet->generated_at,
            'disclaimer' => 'AI-assisted case preparation. WUNZI does not determine truth, credibility or liability.',
        ], 200, [
            'Content-Disposition' => 'attachment; filename="'.$case->public_reference.'.json"',
        ]);
    }
}
