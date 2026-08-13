# AR Collections Command

UiPath coded process app for reviewing active AR dispute-resolution Flow instances.

Run locally with `npm run dev`. The configured OAuth redirect is `http://localhost:5173`; sign in from the app header. The app uses PKCE with the public external application in `uipath.json` and never uses a client secret.

The dashboard loads tenant-scoped entity `bc0fc734-bf94-f111-9b32-000d3ab5d4c4` only when an active Flow instance can be correlated by `caseId`. If the entity, records, or correlation are unavailable, it renders clearly marked fictional, read-only preview data for visual inspection.

Run `npm test -- --run` and `npm run build` before publishing.
