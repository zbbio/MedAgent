# MedAgent frontend

React + TypeScript + Vite frontend for MedAgent.

```bash
npm ci
npm run build
```

The production build is written to `dist/` and is copied into the final image
by the repository root `Dockerfile`. API requests use same-origin `/api`
endpoints, so no model credential is ever exposed to browser JavaScript.
