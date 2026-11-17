# Multi-Agent Software Project Protocol

Protocol version: `1.4`

> Canonical operating instructions for Codex, Claude Code (via `CLAUDE.md`), Antigravity/Gemini, and other coding agents working in this repository.

## 1. Source of truth

- Do not rely on previous chat history or model memory. The repository must contain the durable state needed for continuation.
- `PROJECT.md` is the concise project map and current project-level state.
- `.ai/tasks/` defines substantial user objectives, scope, acceptance criteria, and status.
- `.ai/handoffs/` contains the exact current resume state for active tasks.
- `.ai/reviews/` contains durable QA/code-review/security/UI-review evidence, including capability limits and exact reviewed commits.
- Canonical technical documentation lives in the repository's established docs structure (normally `docs/`).
- Code, tests, configuration, and Git history are implementation evidence. If they disagree with documentation, investigate and reconcile the discrepancy; do not blindly trust either side.
- `.ai/scratch/` is disposable. No future agent may depend on it.

## 2. Start every session by reconstructing context

Before substantive edits:

1. Read `PROJECT.md`.
2. Map the user's request to an existing active task. If the objective is materially new, create a new task; do not create a task merely because a different agent is working. Classify it as `implementation`, `review`, `maintenance`, or `research`.
3. Read the relevant `.ai/tasks/TASK-XXXX-*.md`.
4. Read `.ai/handoffs/TASK-XXXX.md` if present.
5. Read canonical docs and open review findings referenced by the task/handoff.
6. Inspect the relevant code/tests/config.
7. Inspect Git branch/worktree status and recent relevant history. Preserve unknown local changes.
8. Before starting new substantive implementation, scan active tasks for mandatory reviews that are ready for pickup. Apply the automatic review-pickup rules in section 7.
9. Only then plan and execute the requested work.

Do not make the user repeat what a previous agent already persisted in the repository, and do not make the user act as the team's reminder system for routine pending reviews.

## 3. Task policy

A task represents a substantial user outcome and may span multiple agents and sessions.

Examples of one task spanning agents:

- Codex implements backend behavior.
- Claude adds UI for the same feature.
- Gemini/Antigravity performs QA.
- Codex fixes confirmed QA findings.

Keep this as one task when all work serves the same acceptance outcome.

Allowed task statuses: `todo`, `in_progress`, `blocked`, `review`, `done`.

Task types: `implementation`, `review`, `maintenance`, `research`. A standalone audit of already-existing canonical code normally uses `Type: review` and `Review gate: n/a`; do not create a recursive review requirement for the review report itself. QA that fulfills an existing implementation task's merge gate stays attached to that implementation task.

For code-bearing implementation tasks also track:

- canonical integration branch;
- task branch/worktree when used;
- review gate: `required`, `fast_path`, or `waived`;
- review status: `pending`, `approved`, `changes_required`, `inconclusive`, `not_required`, `waived`, or `n/a`;
- exact reviewed implementation commit when a review exists.

If risk/scope increases, escalate `fast_path` to `required`. If uncertain, require review.

Task files are concise scope/state documents, not chronological diaries.

## 4. Handoff policy

Maintain one rolling current handoff per active task at `.ai/handoffs/TASK-XXXX.md`.

Update it automatically before ending any work session, especially when work is incomplete or interrupted. The user should never need to remind you.

A handoff must state:

- what is complete;
- what is partially complete;
- exact remaining work;
- relevant files/areas;
- validation commands and results;
- current branch/commit/worktree state when relevant;
- blockers/open review findings;
- important decisions/assumptions;
- the best concrete next action.

If the task is complete, leave a short completion handoff with validation status and likely next action. Git history preserves previous handoff versions; do not grow the file into a session log.

## 5. Documentation is part of the work

When implementation materially changes behavior, update the relevant canonical docs in the same iteration. This includes, when applicable:

- API contracts;
- schemas/data model;
- architecture/component boundaries;
- configuration/environment behavior;
- build/test/run procedures;
- deployment/operations;
- authentication/security behavior;
- user-visible UI behavior when the project maintains UI specifications.

Prefer existing documentation conventions. Do not create duplicate `api-v2-final.md`-style documents when a canonical document already exists.

Canonical docs describe current truth, not agent conversations or abandoned alternatives.

## 6. `PROJECT.md` maintenance

Keep `PROJECT.md` concise. Update it only when project-level reality changes, such as:

- major implementation state;
- active task list/priorities;
- stack/boundaries;
- canonical docs map;
- known blockers/material risks;
- run/test commands if they become known or change.

Do not use `PROJECT.md` as a changelog or detailed handoff.

## 7. Reviews, automatic review pickup, review gate, and integration

Store independent review evidence under `.ai/reviews/TASK-XXXX/`.

### Automatic pending-review pickup

At every new agent session, after context reconstruction and before new substantive implementation, inspect all active tasks for review-ready work. The user should not need to say "review the previous agent first."

A pending review is eligible for automatic pickup when:

- `Review gate: required`;
- task status is `review`;
- review status is `pending`;
- the intended implementation state is stably identifiable (preferably committed);
- the current agent/harness did not contribute production changes to the exact state being reviewed;
- no explicit user instruction or repository policy tells you to defer it.

Priority:

1. Reviews that block or are dependencies of the user's newly requested work.
2. Other eligible required reviews by project priority.
3. Oldest-ready review when priority is otherwise equal.

For each eligible review picked up:

- run the QA/review capability preflight from `.ai` protocol / `references/qa-evidence.md` semantics before promising review depth;
- review independently against the recorded integration base and exact implementation commit;
- record `APPROVED`, `CHANGES_REQUIRED`, or `INCONCLUSIVE`;
- on `APPROVED`, locally integrate when repository policy permits and validate the integrated state before marking the task done;
- on `CHANGES_REQUIRED`, do not integrate; update task/handoff with findings. Independent new work may continue on its own branch, but dependent work must not treat the blocked implementation as canonical.
- on `INCONCLUSIVE`, do not integrate a `required` task; record the missing evidence/capability and keep the review blocked until sufficient evidence is produced or the user explicitly accepts/waives the missing review scope.

If the user explicitly says to skip/defer the previous review or work only on another task, follow that instruction and keep the review pending. Deferral is not a waiver. Only an explicit waiver changes the gate to `waived`.

If you are not independent of the implementation, you may not approve it. Leave the review pending for another eligible agent.

### Risk-based gate

Independent review is **required** before integration when the change materially affects production/user-visible behavior or carries meaningful correctness/security/data/operational risk. Treat review as required for changes such as:

- API/contracts/protocols;
- authentication, authorization, permissions, secrets, security controls;
- money/financial/business-critical calculations;
- persistence, schemas, migrations, destructive data operations;
- concurrency, idempotency, consistency, transaction boundaries;
- architecture/cross-cutting refactors;
- deployment, infrastructure, production configuration;
- dependency additions/upgrades with runtime/security impact;
- material user-visible UI behavior;
- substantial bug fixes or broad changes where regressions are plausible;
- anything the user explicitly marks for review.

`fast_path` is allowed only for demonstrably low-risk work such as docs/comments/typos/formatting-only changes, non-behavioral metadata, test-only additions that do not alter production behavior, or very small reversible non-behavioral cleanup with adequate validation. If unsure, use `required`.

The user may explicitly waive a required review. Record `Review gate: waived` and the reason; never label a waiver as an approval.

### Required-review lifecycle

1. Work on the task branch, not the canonical integration branch.
2. Implementer runs validation, updates docs/task/handoff, commits coherent changes, and sets task status `review` / review status `pending`.
3. A different agent/harness independently reviews the exact implementation commit against the integration base and records `APPROVED`, `CHANGES_REQUIRED`, or `INCONCLUSIVE`.
4. `CHANGES_REQUIRED` blocks integration. `INCONCLUSIVE` also blocks integration when the gate is `required`. Fixes remain on the task branch and the changed state must be reviewed again.
5. The implementer must not approve or merge its own substantive review-required work.
6. If a reviewer modifies production code, it becomes an implementer for those changes; its approval no longer covers the modified state. Require another independent review unless the user explicitly waives it.
7. `APPROVED` is bound to the exact reviewed implementation commit. Any subsequent production-code change makes that approval stale and returns the changed state to pending review unless a separately justified fast-path policy applies. After a still-valid `APPROVED`, the reviewer or another integration agent may locally integrate according to repository policy. Validate the would-be merged state before finalizing when practical. If integration validation fails, abort/cancel the integration and record the failure instead of knowingly committing a broken canonical branch.
8. Mark the task `done` only after successful integration and required merged-state validation.

### Fast path

For `fast_path`, independent review is optional. The implementing agent may self-validate and integrate according to repository policy. Record the fast-path rationale in the task/handoff when a task exists.

Unless the user asked for both review and fixes, reviewers should report findings rather than silently rewrite production code. Confirmed blocking findings must be reflected into the task and current handoff.

### QA/review evidence discipline

Before any QA/review run, establish runtime capabilities first: outbound network, target reachability, safe credentials/test tenant, local integration dependencies, destructive-test isolation, and browser/tool availability when relevant. Only then claim a review scope.

For material QA, explicitly distinguish `PASSED`, `FAILED`, and `NOT TESTED` across relevant layers such as existing automated tests, static audit, contract/schema checks, independent edge cases, local integration, and live E2E. Separate evidence reproduced in the current review from prior evidence merely consulted. Agent sandbox limitations must never be described as target-system defects.

If evidence is insufficient for a required gate but no defect is confirmed, use `INCONCLUSIVE`, not `APPROVED`.

One-off QA scripts and probes belong in `.ai/scratch/` first; promote them to canonical tests/scripts only when intentionally reusable.

## 8. Git and conflict prevention

### Canonical integration branch

Detect and preserve the repository's actual integration branch/policy (`main`, `master`, `develop`, trunk, etc.). Do not rename branches to fit this protocol. `main` is only an example, not a hard-coded requirement.

### Task branches

For substantial code-bearing tasks, create or reuse a dedicated task branch when repository policy permits, preferably following the repo's own naming convention; otherwise use a clear form such as `task/TASK-XXXX-short-name`. The same branch may pass through Codex, Claude, and Antigravity across multiple sessions.

### Sequential work (default)

Use the same repository checkout with one writing agent at a time. Agents may switch between the canonical integration branch and task branches as required by the task lifecycle. Do not let unreviewed review-required work land on the integration branch.

### Parallel work

Use separate branches/worktrees from a known base. Never allow two agents to write concurrently into the same checkout.

When parallel lanes integrate:

- reconcile conflicts through one integration lane/agent;
- enforce each task's review gate;
- run validation against integrated reality;
- update canonical docs/task/handoff/`PROJECT.md` to match the merged state.

### Existing local changes

- Never reset, discard, overwrite, or mass-format unknown changes.
- Do not revert another agent's work merely because you would implement it differently.
- If an existing decision must change, understand its purpose and document the replacement when consequential.
- Never push, deploy, rotate secrets, rewrite history, force-push, or bypass protected-branch controls unless explicitly authorized.
- Local integration into the canonical branch is allowed only when the task gate and repository policy permit it.

## 9. Git-ignore and checkpoint hygiene

- Preserve the repository's existing `.gitignore` and extend it only when justified by the actual stack/tooling.
- Keep local secrets, local environments, dependency caches, build/test outputs, and editor/OS noise out of Git when appropriate.
- Do not accidentally ignore intentionally versioned generated artifacts or example configuration files.
- Never ignore `AGENTS.md`, `CLAUDE.md`, `PROJECT.md`, canonical docs, `.ai/tasks/`, `.ai/handoffs/`, or `.ai/reviews/`.
- `.ai/scratch/` must remain ignored.
- Prefer a coherent local Git checkpoint at a safe handoff boundary when the current changes can be isolated cleanly and repository policy allows agent commits.
- Never stage or commit unrelated pre-existing changes just to create a checkpoint. If a safe commit is not possible, preserve the working tree and record exact Git state in the handoff.
- Never push, create remotes, rewrite history, force-push, deploy, or bypass remote protected-branch controls unless explicitly authorized. Local integration into the canonical branch is allowed only when the task review gate and repository policy permit it.

## 10. Scratch work

Use `.ai/scratch/` for disposable experiments, temporary scripts, generated diagnostics, or alternate drafts that are not part of the product.

Promote anything required for future work into code/tests/docs/task/handoff/reviews. Never leave the next agent dependent on scratch files.

## 11. Definition of done for an agent iteration

Before stopping, perform the following automatically:

1. Validate the changed surface with the best available tests/lint/typecheck/build/manual check. Record what was and was not run.
2. Synchronize canonical docs with material implementation changes.
3. Update the task's status/progress/acceptance/review state.
4. Update `PROJECT.md` if project-level state changed.
5. Update the rolling handoff, including exact branch/review/resume state.
6. Record review/QA evidence when applicable.
7. If this iteration is the approved integration step, validate integrated reality and only then mark the task `done`.
8. Leave the working tree understandable and do not hide important state only in your final chat response.

Do not mark a task `done` when acceptance criteria are unmet, validation is materially failing, a blocking finding remains unresolved, or a required review/integration has not completed unless the user explicitly accepts/waives that condition.

## 12. Interruption rule

If the user asks you to stop, switch tasks, or end the session while work is incomplete, first make the repository handoff-ready when possible: synchronize the task/handoff/docs with the actual current state, then stop.

## Network CRM contract
Read docs/PROGRESS.md first after this file. Russian UI; FastAPI/SQLAlchemy/PostgreSQL and React/Vite. All entity reads/writes require workspace membership; composite foreign keys enforce same-workspace relations. No real personal data, credentials, dumps or deployment addresses in Git. Use synthetic fixtures only. Runtime data/secrets/backups live outside checkout. Migrations require upgrade and isolated restore tests. Update README and canonical docs with implementation. Public registration is disabled; AI may propose only, humans approve. No external AI APIs. Never expose database/backend ports publicly. Atlas: read its current instructions and audit before changes; no unrelated services, volumes, firewall or media changes. First public GitHub push and license choice require owner confirmation. Work sequentially to conserve tokens; one independent review at end, no overlapping writers. Never self-approve required review. Local integration by independent reviewer is allowed after exact-commit approval and verification. No remote publication implied.
