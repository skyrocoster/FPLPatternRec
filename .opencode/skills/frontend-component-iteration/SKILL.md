---
name: frontend-component-iteration
description: Use to create or iterate a production-backed Storybook UI candidate after HTML selection and before application integration, or to make one approved adjustment to an existing component.
---

# Frontend component iteration

Support the production-backed part of the design loop. Require a selected HTML artifact or an exact existing
Storybook candidate, the user's current visual or interaction request, bounded frontend paths, and an explicit
integration exclusion.

## First Storybook version

1. Read the selected HTML, existing Storybook configuration, production tokens and global styles, the nearest
   component/story convention, and only the focused test precedent needed.
2. Rebuild the selected idea as the smallest typed React candidate in the normal frontend source tree. Never import
   runtime code or private color values from `experiments/`.
3. Add representative stories under a clearly temporary title such as `Exploration/<Name>`. Include the states and
   narrow-width behavior needed for useful visual review.
4. Use production semantics, keyboard/focus behavior, tokens, styles, and component tools. Add only focused
   interaction proof for behavior the candidate already claims to support.
5. Keep the candidate disconnected from application routes, screens, state, data, and APIs.

## Later rounds

Read only the candidate implementation, styles, stories, focused tests, direct dependencies, and the latest
authoritative user feedback. Make the smallest coherent adjustment and rerun only invalidated focused proof. User
edits are authoritative; inspect and preserve them.

Work in the current checkout. Do not create or switch Git branches, worktrees, stashes, or commits for design
iteration. Preserve unrelated changes.

Report what changed and how to view the exact Storybook story, then stop for user visual review. Do not claim design
approval, promote the story, integrate the component, create workflow records, or write a Plan. Once the user
explicitly approves integration, return control to the coordinator for integration assessment.
