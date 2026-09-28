# Logic system — discussion map

**Purpose:** A short list of nodes to discuss and implement in order, not decisions about how to build them.

1. **Source data** — Decide what data to start with and confirm we can get it. Start small: FPL plus one supplementary source for one fixture.
2. **Store data** — Keep what each source returned so later steps can be rerun.
3. **Structure data** — Turn source responses into usable records without losing their original meaning.
4. **Match identities** — Connect each source's players, teams, and fixtures to the same real-world entities.
5. **Agree on facts** — Handle missing or conflicting stats without silently guessing.
6. **Build clean data** — Produce one dependable set of player- and team-fixture records.
7. **Build model inputs** — Turn clean records into information that would have been known before an FPL deadline.
8. **Find and test patterns** — Make predictions and check them against past gameweeks.
9. **Make the app** — Show useful data, patterns, and predictions to the user.

**Target first: node 1, Source data.** Discuss the smallest first input and how to tell whether it was collected successfully. Leave the details of later nodes for their own discussions.
