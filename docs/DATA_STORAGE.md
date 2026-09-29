# Where data belongs

Keep reviewed inputs, downloaded evidence, research notes, and runtime state
separate. Moving files is not permission to change or reload the database.

| Kind | Location | Version-controlled? |
| --- | --- | --- |
| Reviewed club names, legacy team IDs, reviewed player birth dates | [`src/tools/data_pipeline/reference/`](../src/tools/data_pipeline/reference/README.md) | Yes |
| Canonical schema SQL | `src/tools/data_pipeline/ingestion/base_tables.sql` | Yes |
| Saved core provider responses | Existing `data/raw/<provider>/` tree | No |
| Saved alternative-competition responses | Existing `data/alternative_comps/raw/<provider>/` tree | No |
| Prototype code and retained research notes | `experiments/prototypes/<topic>/` | Code and deliberate research records only |
| Canonical and staging database | `fplpatternrec-sqlite` Docker volume, `/data/fplpatternrec.db` inside containers | Never |
| Test output, caches, logs, build output | Tool-specific ignored output directories | No |

## Rules of thumb

- **Reviewed references are application inputs.** Do not put them in
  `docs/throwaway/` or mix them with refreshed raw responses. Keep provenance and
  review notes with the evidence. Their package includes the JSON/CSV resources
  so ingestion does not depend on documentation files being installed.
- **Provider responses stay as received.** Keep existing provider-relative names
  and season folders. Retrieval replaces individual files atomically; it does
  not turn downloads into reviewed canonical facts.
- **The database is volume-only.** Never create a host database or a
  `data/database/` directory. The existing ignored raw-data trees are not SQLite
  storage. Do not move the database into the checkout for convenience.
- **Research is not ingestion.** Intermediate candidates and follow-up notes
  belong with their prototype, not in the reviewed reference package. Promote
  evidence only after review.
- **Do not copy live row counts into multiple READMEs.** See
  [`DATA_PIPELINE.md`](DATA_PIPELINE.md) for recorded load evidence and limitations;
  use read-only SQL through the data inspector when current state is needed.

Existing downloads, research records, and the named volume were not migrated by
the reference-file reorganization. Historical documents may still cite the former
reference paths; their current locations are listed in the reference README.
