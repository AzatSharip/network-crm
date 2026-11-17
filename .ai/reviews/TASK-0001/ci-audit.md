# TASK-0001 — independent CI audit delta review

**Verdict: CHANGES_REQUIRED.** 2026-11-17. Тот же независимый reviewer/integrator, без субагентов и изменений production code.

- Exact reviewed SHA: `806e89891585edd7ad3b40622307ef266ce08c65` (`codex/mvp`).
- Integration base/current main: `e09f4ebd02432c937130742b0d3ef68d87c1c539`.
- Scope: delta CI workflow, audit script, его тесты, README/docs/handoff. Git подтвердил отсутствие изменений backend/frontend/deploy/compose относительно approved `6de1301af34bc4c6feae7a5a4f6abe060141f26f`, включая frontend dependency manifests/lockfile.
- Review-only output: этот файл. Merge/commit/push/deploy не выполнялись; task done не выставлен. При CHANGES_REQUIRED разрешение интегрировать не применяется.

## C1 — P2: некорректный audit JSON принимается как успешная проверка

**Место:** `scripts/audit-frontend.mjs:75–90`; дополнительный путь `:16–23,51–63`.

`audit()` проверяет только наличие metadata.vulnerabilities, но не структуру findings и числовых counters. Runtime path затем проверяет high/critical через truthiness и вообще не вызывает проверку согласованности summary/findings. Поэтому JSON `{auditReportVersion:2,metadata:{vulnerabilities:{}}}` считается успешным runtime audit: отсутствующие counters дают undefined, условие блокировки ложно. Если следующий full audit чистый или содержит только разрешённую цепочку, main завершается успешно, хотя runtime scan не дал пригодного результата.

В full path `assess()` также допускает некорректный тип `vulnerabilities: []` при high=critical=0: массив truthy, Object.entries пуст, summary check проходит. Таким образом заявленное требование fail-closed для malformed reports не выполнено. Это дефект проверки error path, а не утверждение, что сегодняшний npm действительно вернул испорченный отчёт или что CRM runtime эксплуатируем.

**Независимо воспроизведено на точном исходнике**, без записи файлов: в отдельном Node-процессе временно подменён только `node:child_process.spawnSync`, затем `syncBuiltinESMExports()` и импорт реального `main()`. Для двух последовательных npm-вызовов возвращались контролируемые status/stdout; чтение lockfile и production audit logic оставлены настоящими. Результаты:

| runtime report | full report | Фактический результат main |
|---|---|---|
| version2, metadata.vulnerabilities={}, findings отсутствуют | корректный clean report | **ACCEPTED**, без throw |
| summary high=critical=0, но findings содержит critical | корректный clean report | **ACCEPTED**, inconsistency проигнорирована |
| корректный clean report | summary high=critical=0, vulnerabilities=[] | **ACCEPTED**, без throw |

Минимальная форма clean report для повторения: `{auditReportVersion:2,metadata:{vulnerabilities:{info:0,low:0,moderate:0,high:0,critical:0,total:0}},vulnerabilities:{}}`. Для mocked spawn response использовать `{status:0,stdout:JSON.stringify(report)}`. Каждый из трёх случаев должен завершать entrypoint с ошибкой, а не выводить успешный результат.

**Требуемое исправление:** валидировать оба отчёта общей проверкой до применения policy: findings — непустотный по типу object-map (пустой map допустим, массив/null нет), необходимые severity counters — конечные неотрицательные целые числа, значения severity и структура записей валидны, summary согласован с findings. Runtime после успешной валидации должен отвергать любые high/critical без исключений. Добавить tests реального main/audit entrypoint с подменой subprocess result: нынешние шесть tests вызывают только assess и не проверяют обход runtime path.

## Собственное evidence

Preflight: checkout clean на exact SHA; Node22.12.0; сетевой доступ подтверждён успешными настоящими npm audit и чтением GitHub advisory. Тесты не требуют DB, credentials, браузера или Atlas. Стандартные API/UI suites не запускались согласно ограниченному scope. Инъекции выполнены только в памяти отдельного процесса, файлы приложения/lockfile не менялись.

| Проверка | Результат |
|---|---|
| `node --test scripts/tests/audit-frontend.test.mjs` | **PASSED:** 6/6, 46.5 ms; это смесь positive/negative случаев |
| `node scripts/audit-frontend.mjs` — настоящий registry | **PASSED текущий happy path:** runtime total0, full high5; exceptions plugin-react/fdir/picomatch/tinyglobby/vite, blocked=[]; явное NOT FIXED warning |
| Независимые main probes malformed runtime/full | **FAILED:** три случая C1 ошибочно приняты |
| Независимые subprocess/error probes | **PASSED:** process error, status2, invalid JSON, report.error/ENETWORK отвергнуты |
| Независимый parent runtime promotion | **PASSED:** dev=false у vite блокирует исключение vite |
| Независимый mixed-node promotion | **PASSED:** дополнительный runtime picomatch node4.0.7 блокирует picomatch chain |
| Независимый unknown critical advisory на parent | **PASSED:** не скрывается разрешённым downstream GHSA |
| Независимая граница срока | **PASSED:** 2026-12-16 допускает exact chain, 2026-12-17 блокирует |
| Static policy review | Exact GHSA URL/name, picomatch4.0.7, dev=true каждого указанного node, recursive all-via и cycle guard; неизвестные причины/версии не допускаются |
| `git diff --check main HEAD` | **PASSED** |
| Runtime tree identity | **PASSED:** backend/frontend/deploy/compose не отличаются от approved6de1301 |

GitHub указывает high ReDoS для picomatch<=4.0.7, обновление 2026-11-17 и patched versions None: [GHSA-fc5q-39xc-vjpf](https://github.com/advisories/GHSA-fc5q-39xc-vjpf). Это поддерживает честное обозначение временного принятия build-risk, а не исправления upstream. Независимый npm view latest в этом review не запускался.

Статически final frontend Docker stage — Nginx с копированием только static dist из build stage. Отсутствие Node/npm/node_modules на реальном Atlas frontend и предыдущий CI API34/ruff/pip/build PASS сообщены основным агентом; **reviewer NOT TESTED**, не повторялись. Развёрнутый Vite dev server и пользовательские globs не добавлены этой delta.

Non-blocking documentation observation: SECURITY обещает полный отчёт в CI output, но script печатает metadata, имена exceptions/blocked и один advisory URL; raw npm findings/via/nodes не выводятся. Лучше уточнить формулировку или сохранять полный отчёт как evidence. Это отдельно от C1.

## Продолжение

Исправить C1 на task branch, добавить entrypoint regressions и предъявить новый exact SHA тому же reviewer. До повторного APPROVED не интегрировать. Main остаётся `e09f4ebd02432c937130742b0d3ef68d87c1c539`. Само временное исключение для известного build-only риска не является finding; блокирует неполная проверка входных отчётов.
