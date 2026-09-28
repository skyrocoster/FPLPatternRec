# Retrieval rewrite and first ingestion slice — agreed direction

This is directional evidence for one Plan, not implementation authorization or a replacement for repository assessment. The proposed staging shapes in `docs/throwaway/raw-data-staging-schemas.md` are a reference, not existing tables or a mandate to create them all now.

## Agreed outcome

- Rewrite the existing quick-and-dirty retrieval scripts as a coherent, better-organized set of tools. Cover all currently supported retrieval sources in this first milestone, with full command tooling using Typer and PowerShell (`.ps1`) integration. Assess the repository before specifying exact folders, command names, and the relationship to `dev.ps1`.
- Support refreshes: a successful refreshed raw response replaces the saved file. Do not introduce dated capture directories or raw-response history. Do not erase a last good file because a request failed.
- Keep the raw responses fetched from a provider even when only a portion is staged. Do not build a selective bootstrap-only FPL fetch or throw away fixtures, live data, or player data merely because this slice loads teams.
- Create the SQLite database/schema path and prove the end-to-end process with only the official FPL teams staging table. Use season-scoped IDs, as proposed for official FPL staging; repeated loads must not duplicate teams. Additional loaders and staging tables follow after this proof, not in this slice.
- Maintain a checklist of tables expected at the end of the entire ingestion process, distinguishing future tables from ones actually created and proven. The raw staging-schema proposal informs that inventory. Providers with no usable payload yet (ClubElo and SofaScore) must not be misreported as implemented tables.
- Use **one Plan** for this milestone. Luna owns assessment and Plan writing; the coordinator reviews the Plan after it is written. No Plan implementation has been approved by this record.

## Reasons and boundaries

- The priority is a hobby-project-scale, usable retrieval and refresh workflow, not a capture-versioning system or a database full of speculative tables.
- Retrieval breadth and ingestion breadth are deliberately different: migrate the existing source coverage, but prove just one database table first.
- The repository's database currently lives only in the named Docker volume and `dev.ps1 setup` expects a zero-table database. The Plan must reconcile that existing behavior before loading tables; never put a SQLite database in a host `data/` directory.
- Existing raw payloads and unrelated work must be preserved. A new refresh operation may replace the corresponding raw file by design, but planning and assessment must not do so.

## To resolve from repository assessment

- Concrete source-code and raw-data directory layout, Typer command structure and arguments, and PowerShell integration consistent with current project conventions.
- Exact table checklist scope and format, including whether the existing canonical base-table proposal is a future target rather than part of the first database slice.
- Finite direct behavioral proof of retrieval/refresh and the teams ingestion path, without broad maintenance checks.
