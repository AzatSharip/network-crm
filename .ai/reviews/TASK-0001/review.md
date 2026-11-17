# TASK-0001 — independent security/correctness/ops review

**Verdict: APPROVED.** Exact SHA: `6de1301af34bc4c6feae7a5a4f6abe060141f26f`. 2026-11-17. Один независимый Codex reviewer, без субагентов; production changes не вносил, integration не выполнял.

- Integration base: `a601f921f1f1eea29b7c75caac17664f0ac0a625` (`main`).
- Reviewed implementation/current HEAD: `6de1301af34bc4c6feae7a5a4f6abe060141f26f` (`codex/mvp`).
- First review implementation: `750f7f1a2c4920678ce851e57e520dabbda65c8a`.
- First review final tree / delta base: `9e80b205417ea026c58cb0523dc3ac9c7feeed0c` (docs/LICENSE only относительно первого implementation). Первое решение для него было CHANGES_REQUIRED; ниже сохранено историческое evidence.
- Scope: исходный review всего MVP относительно main + текущий review только delta `9e80b20..6de1301` и исходных repro R1/R2. Неизменённые области повторно не прогонялись. APPROVED относится к текущему exact SHA, а не к последующим runtime changes или live deployment.
- Ограничение reviewer на запись только этого файла и запрет редактировать task/handoff переданы **основным агентом**; прежняя атрибуция «прямое указание пользователя» исправлена. В текущем поручении также запрещён merge. Reviewer не менял production code и не интегрировал. Gitleaks/history scan ниже относится к первому implementation до docs-коммита.

## Повторный delta review — APPROVED

**R1 CLOSED, R2 CLOSED. Новых blocking findings в delta нет.** Production delta ограничена `main.py` (User SELECT FOR UPDATE в login), `Inbox.tsx` (вызов helper) и новым `contact-preview.ts`. Также просмотрены два parametrized API regression, три renderer regression и изменения документации.

R1: login теперь получает блокировку строки User до verify и держит её до function-scoped commit сессии. Password change использует ту же блокировку и refresh после получения lock. При login-first смена пароля ждёт создания сессии, затем удаляет её; при change-first login читает новый hash и отвергает старый пароль. Добавленные tests наблюдают реальный `pg_stat_activity.wait_event_type='Lock'`, а не только задержку потока.

R2: фактический Inbox renderer вызывает `contactPreview`, который показывает все семь сохраняемых полей: platform, kind, value, label, is_primary, source, verification; пустые label/source и оба verification states видны явно. UI сохраняет React text escaping. Изменения backend payload/apply для этого исправления не потребовались.

### Собственное evidence на 6de1301

Preflight: checkout clean, точный HEAD и main проверены; localhost:18432 доступен. Прежний безопасный disposable runner и fixtures не изменены. Секреты загружались только разрешённым launcher, не выводились. Тесты работают с synthetic fixtures в отдельных случайных `crm_test_*`; временные БД удалены. Atlas и перестраиваемые основным агентом local/private сервисы не использовались. Новых внешних зависимостей нет, outbound/browser проверки для delta не требовались.

| Проверка | Результат |
|---|---|
| `python3 scripts/local-env.py .venv/bin/python scripts/test.py -k password_change_serializes_session_issuance` | **PASSED:** 2 passed, 32 deselected; оба порядка; runtime 0.90 s |
| Миграции в том же runner | **PASSED:** fresh upgrade, drift check, downgrade→upgrade; штатные шаги runner, schema delta отсутствует |
| Независимый исходный R1 repro | **PASSED:** login приостановлен после успешного verify; password change наблюдаемо ждёт User lock; после release login200 → change200 → старая session `/me`401; новый login со старым паролем401 |
| `node frontend/node_modules/@playwright/test/cli.js test --config frontend/playwright.config.ts frontend/tests/contact-preview.spec.ts` | **PASSED:** 3 renderer tests, 297 ms; это не browser E2E |
| Независимый исходный R2 renderer repro | **PASSED:** извлечённая из текущего Inbox функция render с фактическим contactPreview показывает original/unverified и replaced/verified различно; отдельная мутация каждого из семи editable fields меняет результат |
| Независимый исходный R2 API repro | **PASSED:** update_person → approve/applied → GET сохраняет source/verification ровно как теперь показано renderer |
| `git diff --check 9e80b20 HEAD` | **PASSED** |

Исходный R1 probe адаптирован только по синхронизации: после исправления нельзя ждать завершения password change, удерживая паузу login; вместо этого отдельно запущен change, подтверждено ожидание lock, затем снята пауза. Реальный Argon2/SQL и endpoints не подменялись. R2 проверен через исходную функцию отображения и API, не через копию её логики.

При первом запуске Playwright из frontend shell выбрал Node16 и tool отказался запускаться; повтор из корня под установленным Node22.12.0 успешно выполнил три теста. Это локальный выбор runtime, не дефект приложения. Starlette/httpx deprecation warning остаётся неблокирующим.

**Reported, не собственный повторный прогон:** полный suite34, frontend lint/build PASS от implementer. Полный старый scope, dependency audit, browser E2E, backup/restore, live TLS/renew/public ingress не повторялись согласно ограничению задачи. Сохраняются их ранее указанные границы evidence; approval кода не означает, что публичный ingress уже включён или проверен reviewer.

## Исторические findings первого review — оба закрыты выше

### R1 — P1 (CLOSED на 6de1301): вход со старым паролем переживает смену пароля и отзыв сессий

**Место:** `backend/app/main.py:162–179`, взаимодействие с `change_password`, строки 843–849.

Login читает пользователя и проверяет пароль без блокировки/повторной проверки актуального hash перед созданием сессии. Смена пароля блокирует пользователя и удаляет существующие сессии, но login не участвует в той же синхронизации. Если login уже проверил старый пароль, затем смена пароля закоммитилась, login может создать новую действующую 12-часовую сессию на основании старого пароля. Это нарушает гарантию отзыва доступа после смены скомпрометированного пароля.

**Воспроизведено** на отдельной синтетической PostgreSQL БД, через реальные FastAPI endpoints. Только в памяти тестового процесса обёрнут `app.main.verify`: после успешного Argon2 verify первого login выставлялся `threading.Event`, поток ожидал второго события; последующие verify работали без паузы. Далее:

1. Клиент A запускает login с текущим паролем; остановить после его успешной проверки, до вставки session.
2. Уже авторизованный клиент B выполняет `/auth/password` с новым паролем; дождаться ответа и commit.
3. Разрешить клиенту A закончить login.
4. Проверить `/me` с полученной A cookie и отдельный новый login со старым паролем.

Фактические HTTP-статусы: **password change 200 → задержанный login 200 → его `/me` 200; новый login со старым паролем 401**. Production-файлы не патчились. Искусственная пауза фиксирует допустимое межпоточное расписание, не меняет результат проверки пароля или SQL.

**Нужно:** согласовать login/session issuance и password change/revocation через общую транзакционную синхронизацию либо credential/session generation с проверкой актуальности. Добавить regression на это расписание и обратный порядок: сессия, созданная до смены пароля, должна отзываться; вход со старым hash после неё не должен оставлять действующую сессию.

### R2 — P2 (CLOSED на 6de1301): AI approval скрывает изменение происхождения и верификации контакта

**Место:** `frontend/src/Inbox.tsx:102–103`; применение payload: `backend/app/main.py:735–742` и `backend/app/services.py`.

Для `contacts` renderer показывает platform/kind/value/label/is_primary, но пропускает сохраняемые `source` и `verification`. Предложение, меняющее только эти поля, проходит сравнение JSON, однако колонки «Сейчас» и «Предложено» выглядят одинаково. Пользователь не видит, что подтверждает замену происхождения контакта и перевод `unverified` → `verified`.

**Воспроизведено двумя независимыми частями:**

- Выполнена извлечённая из точного исходника функция `render` в Node VM (без изменения файла). Для синтетического email с `source: "Synthetic original", verification: "unverified"` и того же email с `source: "Synthetic replaced", verification: "verified"` оба результата: `email · email: synthetic@example.com`.
- В отдельной синтетической БД создана карточка, затем update_person suggestion с изменением только этих contact-полей. Approve вернул `applied`; повторное GET подтвердило сохранённые `source="Synthetic replaced"`, `verification="verified"`.

**Нужно:** отображать все сохраняемые поля контакта в before/after, включая source и verification, с понятными подписями. Проверить отдельные изменения/очистку каждого поля и создание контакта с заданной verification. Это проверка функции отображения + API, не новый browser E2E.

## Capability preflight и границы первого review

- Checkout при начале и перед записью отчёта был clean, HEAD совпадал с exact SHA; main совпадал с base. Активна одна TASK-0001 с required/pending review.
- TCP localhost:18432 и localhost:8081 доступны; outbound TCP pypi.org:443 доступен. Это проверка сетевой возможности, не повторный dependency audit.
- `.venv`, локальные UI/test dependencies доступны. DB credentials только загружались разрешённым `scripts/local-env.py` в окружение дочерних процессов; приватные env/credentials не открывались вручную и не выводились.
- Прочитаны runner/fixtures до запуска: случайная отдельная `crm_test_*` БД, миграции и TRUNCATE только в ней, удаление в finally. Дополнительные probes использовали тот же принцип. Все созданные ими БД удалены; не использовались рабочие карточки, реальные аккаунты или Atlas.
- Browser E2E не повторялись; выбран точечный renderer/API review. Попытка полного in-memory TSX render остановилась на отсутствии импортируемого TypeScript JS API в установленном пакете; вместо неё успешно выполнена фактическая функция render. Это ограничение тестового метода, не дефект продукта.
- Разрешённые приватные `gateway.diff` и `gateway.sha256.json` прочитаны read-only. Адреса и приватные пути сюда не копируются. Полные current/candidate configs и live Atlas не читались; собственный nginx -t и проверка соответствия полных файлов хешам не выполнялись.

## Собственное evidence первого review (750f7f1)

| Слой / проверка | Результат |
|---|---|
| `python3 scripts/local-env.py .venv/bin/python scripts/test.py` | **PASSED:** 32 теста, 11.97 s; warning Starlette/httpx deprecation |
| Upgrade fresh DB, Alembic check, downgrade base → upgrade head | **PASSED**, в disposable DB; drift отсутствует |
| Дополнительный login/password concurrency probe | **FAILED**, R1 воспроизведён |
| Два concurrent POST people с одинаковым Idempotency-Key | **PASSED:** два 201, один person ID |
| Два concurrent approve одного suggestion | **PASSED:** два 200/applied, одна созданная карточка (проверено SQL) |
| RLS catalog/runtime | **PASSED:** 11 таблиц ENABLE+FORCE RLS, runtime не superuser/BYPASSRLS |
| RLS foreign-context INSERT / context reset | **PASSED:** INSERT отвергнут SQLSTATE 42501; после rollback scoped SELECT не видит карточек |
| Audit UPDATE от runtime | **PASSED:** SQLSTATE 42501 |
| Concurrent acceptance одного invitation | **PASSED:** один 200, один 400 |
| Invitation существующего пользователя | **PASSED:** неверный пароль 401, верный 200; существующая editor роль не повышена до admin из нового invitation |
| AI contact source/verification preview + persistence | **FAILED**, R2: одинаковое отображение разных сохраняемых значений |
| Local full Compose read-only smoke | **PASSED:** `/` 200, `/api/v1/me` без сессии 401, nosniff/DENY |
| Ruff check + format check backend/scripts/deploy | **PASSED**, 22 Python-файла отформатированы |
| `python3 scripts/check-repository.py` | **PASSED:** 89 historical/current paths, запрещённых имён нет |
| `gitleaks git . --redact --no-banner` | **PASSED:** 3 commits, no leaks; не доказательство отсутствия всех ПДн |
| `git diff --check a601f92 750f7f1` | **FAILED, non-blocking hygiene:** 177 trailing-whitespace diagnostics в generated schema SQL; runtime finding из этого не выводится |

Статический review проследил проверку membership/roles, ограничения bearer, CSRF/Origin, session cookies, composite FK, FORCE RLS, function-scoped commit до HTTP-response, optimistic versions и rollback AI approval. Подтверждённые дефекты перечислены выше; иных блокирующих дефектов в этих просмотренных участках не установлено.

Ops review: Compose не публикует API/DB в production; test override публикует DB на loopback и отдельно маркирован. Изучены bootstrap, образы, nginx, Unix-socket override, TXT-only hook и certificate validation/rollback. Приватный gateway diff добавляет CRM vhost; live application не выполнялась. Backup использует pipefail и age pipeline без plaintext dump на диске; restore создаёт случайную отдельную БД и проверяет exit codes; retention удаляет только при явном --apply и совпадении verified hash. Структурные restore counts не подменяют disaster-recovery smoke. Автоматический off-host backup в reviewed docs ещё не настроен.

## Prior / reported evidence — не воспроизведено reviewer

Из `docs/VALIDATION.md` exact commit: три Chrome E2E, frontend build/lint, search10k, pip/npm audit, локальный encrypted backup/restore и rejection повреждённого ciphertext, Atlas backup/restore, off-host copy, owner smoke, 23 существующих контейнера без изменений, nginx -t candidate. Для этих пунктов собственный результат: **NOT TESTED**; prior PASS не присвоен reviewer.

В ходе review пользователь передал дополнительное evidence основного агента (runtime source остаётся заморожен): certbot renew dry-run PASS, timer enabled/active; отдельный loopback TLS-check gateway с тем же candidate — trusted TLS, HTTP308, HSTS, owner login, Secure/HttpOnly/__Host/SameSite cookie, пустые Personal/Family, wrong Origin403, logout401 PASS. Actual shared ingress unchanged. Это **reported PASS / reviewer NOT TESTED**, а не проверка действующего публичного маршрута.

Также сообщено: socket mode 0666, parent UID/GID101 mode0750, isolated mount; `/crm-socket` fix уже в exact SHA. Защита от посторонних local users при таком mode опирается на доступ к parent и mount boundary; live permissions reviewer не проверял. Оснований объявлять публичную доступность socket только из mode0666 нет.

Дополнение основного агента: Mac public TCP connect оказался misleading из-за локального сетевого слоя, protocol replies timeout; с Atlas LAN порты 5432/8000/18080 refused, external IP те же порты timeout; Docker API/DB без bindings. Backup restore и off-host SHA/decryption PASS, автоматический off-host перенос пока отсутствует. Это reported evidence, не собственный сетевой/restore test reviewer. В final docs/handoff ещё остаются прежние формулировки «dry-run запущен»/«проверка auto-renew»; при дальнейшей синхронизации отделить уже выполненный staging renew от ещё не включённого public ingress (non-blocking documentation note).

## Следующий шаг

R1/R2 закрыты. Exact implementation `6de1301af34bc4c6feae7a5a4f6abe060141f26f` **APPROVED**; новых blocking findings нет. По отдельному поручению integration agent может обновить task/handoff и выполнить предусмотренную протоколом интеграцию с проверкой integrated state. В этой итерации merge не выполнялся и не разрешён к выполнению reviewer; shared ingress не менялся. Любое последующее production-code изменение требует оценки нового exact SHA.
