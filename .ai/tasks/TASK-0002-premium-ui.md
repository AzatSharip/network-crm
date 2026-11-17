# TASK-0002 — Premium interface

Type: implementation
Status: review
Integration branch: main
Task branch: codex/premium-ui
Integration base: 2b56ab1
Review gate: required
Review status: pending

Redesign the existing Russian Personal/Family CRM with a coherent, restrained visual system. User requested reference research and implementation, with sequential work and minimal agent overhead.

Scope: app shell/navigation, contact list/search/filters, details, editor, login, graph/Inbox/settings styling, responsive and keyboard behavior. No data model, authorization, network-access or backend changes.

Acceptance: coherent desktop/mobile visual inspection using synthetic fixtures; readable contrast, visible focus and touch targets; existing workflows preserved; frontend lint/build/browser tests pass; one independent exact-commit review before main integration. Frontend-only deployment on existing host after review; preserve other services.

References: Attio official record/table UI (https://attio.com/help/reference/attio-101/attios-data-model/understanding-records); Linear calmer-interface principles (https://linear.app/now/behind-the-latest-design-refresh). Original composition/assets; no third-party brand or screenshots included in product.

Validation: frontend lint/build PASS (Node22.22.0); 8 frontend checks PASS (5 Chrome E2E +3 renderer). Desktop/login/details/editor/graph/Inbox/settings and mobile list/details/editor screenshots visually inspected with synthetic data; animation-disabled snapshots used. No backend/dependency changes. Physical mobile/screen reader not tested.
