<?php

namespace App\Models;

use App\Enums\IssueRelationship;
use App\Models\Concerns\HasUuid;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class IssueClaim extends Model
{
    use HasUuid;

    protected $fillable = ['issue_id', 'claim_id', 'relationship'];

    protected function casts(): array
    {
        return ['relationship' => IssueRelationship::class];
    }

    public function issue(): BelongsTo
    {
        return $this->belongsTo(Issue::class, 'issue_id');
    }

    public function claim(): BelongsTo
    {
        return $this->belongsTo(Claim::class, 'claim_id');
    }
}
