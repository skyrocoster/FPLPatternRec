# Player birth-date research

Retained research evidence, not an ingestion input or a statement of current
database contents. These records preserve intermediate conclusions, including
unresolved and later superseded candidates.

- `early-*.json` and `later-*.json` — initial candidate batches and follow-ups.
- `reviews/dob-159-review-*.json` — individual review batches, grouped by canonical player ID range.
- `reviews/dob-159-followup-*.json` — subsequent follow-up research.
- `reviews/dob-159-taylor-final.json` — a retained Tom Taylor research note; read
  it alongside the final reviewed reference rather than assuming its filename
  makes it authoritative.

The accepted ingestion input is
[`reviewed_player_birth_dates.json`](../../../src/tools/data_pipeline/reference/reviewed_player_birth_dates.json).
For the final decisions, source limitations, and recorded database-load evidence,
see [`DATA_PIPELINE.md`](../../../docs/DATA_PIPELINE.md).

The `reviews/dob-159-*.json` files previously sat directly under
`experiments/prototypes/`; they were grouped here without changing their records.
