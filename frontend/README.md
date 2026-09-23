# Frontend

React and Vite status client on port `8455`; it checks backend health on
`http://localhost:5677`.

- `src/` — application, features, tests, and Storybook stories
- `.storybook/` — Storybook configuration
- `package.json` — frontend commands and dependencies

Regenerate the health-only API client from `frontend/src/api/generated/openapi.json` by running
`npm run generate:api --workspace frontend` from the repository root.

Service commands are in [`docs/DEVELOPMENT_SERVICES.md`](../docs/DEVELOPMENT_SERVICES.md).
Before browser/E2E checks, run `dev.ps1 status` and reuse healthy Compose
services; do not start a competing host server.
