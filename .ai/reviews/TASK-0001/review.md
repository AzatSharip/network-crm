# TASK-0001 — independent security/correctness/ops review

**Verdict: CHANGES_REQUIRED.** 2026-11-17. Один независимый Codex reviewer, без субагентов; production changes не вносил, integration не выполнял.

- Integration base: `a601f921f1f1eea29b7c75caac17664f0ac0a625` (`main`).
- Exact implementation: `750f7f1a2c4920678ce851e57e520dabbda65c8a` (`codex/mvp`).
- Final tree: `9e80b205417ea026c58cb0523dc3ac9c7feeed0c`. Дополнительно просмотрен docs/LICENSE diff; Git подтвердил отсутствие изменений backend/frontend/scripts/deploy/compose относительно implementation SHA. Оба findings и verdict применимы к этому final tree.
- Scope: весь MVP относительно base, с приоритетом auth, workspace/RLS, transactions/idempotency, AI approval, invitations, backup/deployment; выборочная проверка UI. Решение относится только к указанному SHA.
- По прямому указанию пользователя reviewer пишет только этот файл; task/handoff не обновляет и не интегрирует. MIT/LICENSE/docs fast-path commit внесён основным агентом; runtime-проверки выполнены на implementation SHA, повторный прогон для неизменного runtime не требовался. Gitleaks/history scan выполнен до docs-коммита.

## Findings

### R1 — P1: вход со старым паролем переживает смену пароля и отзыв сессий

**Место:** `backend/app/main.py:162–179`, взаимодействие с `change_password`, строки 843–849.

Login читает пользователя и проверяет пароль без блокировки/повторной проверки актуального hash перед созданием сессии. Смена пароля блокирует пользователя и удаляет существующие сессии, но login не участвует в той же синхронизации. Если login уже проверил старый пароль, затем смена пароля закоммитилась, login может создать новую действующую 12-часовую сессию на основании старого пароля. Это нарушает гарантию отзыва доступа после смены скомпрометированного пароля.

**Воспроизведено** на отдельной синтетической PostgreSQL БД, через реальные FastAPI endpoints. Только в памяти тестового процесса обёрнут `app.main.verify`: после успешного Argon2 verify первого login выставлялся `threading.Event`, поток ожидал второго события; последующие verify работали без паузы. Далее:

1. Клиент A запускает login с текущим паролем; остановить после его успешной проверки, до вставки session.
2. Уже авторизованный клиент B выполняет `/auth/password` с новым паролем; дождаться ответа и commit.
3. Разрешить клиенту A закончить login.
4. Проверить `/me` с полученной A cookie и отдельный новый login со старым паролем.

Фактические HTTP-статусы: **password change 200 → задержанный login 200 → его `/me` 200; новый login со старым паролем 401**. Production-файлы не патчились. Искусственная пауза фиксирует допустимое межпоточное расписание, не меняет результат проверки пароля или SQL.

**Нужно:** согласовать login/session issuance и password change/revocation через общую транзакционную синхронизацию либо credential/session generation с проверкой актуальности. Добавить regression на это расписание и обратный порядок: сессия, созданная до смены пароля, должна отзываться; вход со старым hash после неё не должен оставлять действующую сессию.

### R2 — P2: AI approval скрывает изменение происхождения и верификации контакта

**Место:** `frontend/src/Inbox.tsx:102–103`; применение payload: `backend/app/main.py:735–742` и `backend/app/services.py`.

Для `contacts` renderer показывает platform/kind/value/label/is_primary, но пропускает сохраняемые `source` и `verification`. Предложение, меняющее только эти поля, проходит сравнение JSON, однако колонки «Сейчас» и «Предложено» выглядят одинаково. Пользователь не видит, что подтверждает замену происхождения контакта и перевод `unverified` → `verified`.

**Воспроизведено двумя независимыми частями:**

- Выполнена извлечённая из точного исходника функция `render` в Node VM (без изменения файла). Для синтетического email с `source: "Synthetic original", verification: "unverified"` и того же email с `source: "Synthetic replaced", verification: "verified"` оба результата: `email · email: synthetic@example.com`.
- В отдельной синтетической БД создана карточка, затем update_person suggestion с изменением только этих contact-полей. Approve вернул `applied`; повторное GET подтвердило сохранённые `source="Synthetic replaced"`, `verification="verified"`.

**Нужно:** отображать все сохраняемые поля контакта в before/after, включая source и verification, с понятными подписями. Проверить отдельные изменения/очистку каждого поля и создание контакта с заданной verification. Это проверка функции отображения + API, не новый browser E2E.

## Capability preflight и границы

- Checkout при начале и перед записью отчёта был clean, HEAD совпадал с exact SHA; main совпадал с base. Активна одна TASK-0001 с required/pending review.
- TCP localhost:18432 и localhost:8081 доступны; outbound TCP pypi.org:443 доступен. Это проверка сетевой возможности, не повторный dependency audit.
- `.venv`, локальные UI/test dependencies доступны. DB credentials только загружались разрешённым `scripts/local-env.py` в окружение дочерних процессов; приватные env/credentials не открывались вручную и не выводились.
- Прочитаны runner/fixtures до запуска: случайная отдельная `crm_test_*` БД, миграции и TRUNCATE только в ней, удаление в finally. Дополнительные probes использовали тот же принцип. Все созданные ими БД удалены; не использовались рабочие карточки, реальные аккаунты или Atlas.
- Browser E2E не повторялись; выбран точечный renderer/API review. Попытка полного in-memory TSX render остановилась на отсутствии импортируемого TypeScript JS API в установленном пакете; вместо неё успешно выполнена фактическая функция render. Это ограничение тестового метода, не дефект продукта.
- Разрешённые приватные `gateway.diff` и `gateway.sha256.json` прочитаны read-only. Адреса и приватные пути сюда не копируются. Полные current/candidate configs и live Atlas не читались; собственный nginx -t и проверка соответствия полных файлов хешам не выполнялись.

## Собственное evidence

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

Implementer исправляет R1 и R2 и добавляет целевые regressions на task branch. После этого нужен независимый review нового exact implementation SHA. До него **approval отсутствует**. Интеграция и включение shared ingress этим отчётом не разрешены; task/handoff оставлены без изменений по заданию.
