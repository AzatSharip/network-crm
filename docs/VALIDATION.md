# Проверки — 2026-11-17

Проверки поведения — на синтетических данных; на Atlas выполнен вход владельца и чтение его пустых пространств. Ни секреты, ни персональные данные не попали в доказательства в Git.

| Проверка | Результат |
|---|---|
| Python ruff, frontend TypeScript/Prettier/Vite | PASS |
| PostgreSQL API integration | PASS, 34 теста, PostgreSQL18.7, отдельная одноразовая БД |
| Alembic drift / downgrade → upgrade | PASS, только отдельная тестовая БД |
| Chrome desktop через полный Compose/nginx | PASS: несколько способов связи, создание/правка/поиск, связь, граф, выход |
| Chrome mobile390×844 | PASS: без горизонтального переполнения, focus/Escape |
| AI и приглашение через UI | PASS: подтверждение AI → карточка; приглашение → принятие → вход viewer без права добавления |
| Search10k | PASS: измерен на PostgreSQL18.6; метрики и GIN plans в search-benchmark.json; exact email/name дают1 совпадение |
| Local encrypted backup/restore | PASS: 8 persons/2 workspaces/1 suggestion; повреждённый ciphertext отвергнут; временные БД удалены |
| Atlas encrypted backup/restore | PASS: 0 persons/2 workspaces/0 suggestions, migration0001; ежедневный timer enabled |
| Off-host копия | PASS: копия на Mac, совпадение SHA-256 с restore receipt, расшифровка независимым ключом |
| pip-audit | PASS, без известных уязвимостей |
| npm audit | Runtime PASS; full audit: известный build-only GHSA-fc5q-39xc-vjpf, временное точечное исключение до2026-12-17, см. SECURITY.md |
| Gitleaks tree/staged/history | PASS staged/tree/all-history на implementation750f7f1; ручной поиск private identifiers без совпадений |
| Full Docker Compose | PASS: local и Atlas healthy, one-shot migration успешна, web200/unauthenticated API401 |
| Atlas owner smoke | PASS: вход, Personal/Family пустые, выход; реальные карточки не создавались |
| Существующие сервисы Atlas | PASS: 23 контейнера сохранили StartedAt/status/health; после согласованного graceful reload |
| HTTPS candidate | PASS: доверенный отдельный сертификат; nginx -t на конкретном добавочном vhost; публичный маршрут применён по согласию |
| HTTPS staging / renewal | PASS: trusted TLS/308/HSTS, owner login, Secure __Host cookie, CSRF/Origin, logout через отдельный loopback gateway; certbot dry-run PASS, timer enabled/active |
| Public HTTPS | PASS после согласия: trusted TLS/308/HSTS/login/Secure __Host cookie/CSRF/Origin/logout с Mac; old routes200,23existing containers unchanged |
| Порты DB/API/frontend | LAN connection refused, external IP timeout; Docker bindings/internal networks проверены |
| Independent exact-commit review | APPROVED app6de1301 и CI policy897c03e; integrated by reviewer |
| CI audit policy | PASS7 tests и реальный registry report; malformed runtime/full reports rejected |
| GitHub CI | PASS на55083a1:34 API tests, migrations, ruff, pip audit, build,7 audit-policy tests, browser scenarios, Gitleaks full history. [Run](https://github.com/AzatSharip/network-crm/actions/runs/44142099793) |

API-тесты покрывают IDOR/BOLA, FORCE RLS с runtime-ролью, viewer/editor, CSRF/Origin, logout/revoke-all/password change, Secure/__Host cookies в HTTPS-режиме, rate/body limits, небезопасные URL, Telegram ID, cross-platform phone/email duplicate warning, idempotency, optimistic versions, направленный bounded graph, expiring one-use invitations, limited/revoked agent tokens, conflict rollback, preview удаляемых AI-полей. Отдельный regression проверяет, что ошибка commit возвращает ошибку HTTP и откатывает карточку до отправки успешного ответа.

Эти проверки не являются независимым pentest. Локальный HTTPS cookie test не подменяет реальный публичный TLS smoke. Search benchmark и локальный backup снимались до последних UI/transaction изменений; версия и данные явно указаны. Физическое мобильное устройство не проверено.

После независимого review исправлены R1 (общая row lock при login/password change; два порядка реальной конкурентной транзакции проверены) и R2 (полный before/after source/verification и очистки контакта; три renderer regression PASS). 34 API tests и frontend build/lint PASS. Исправленный exact commit6de1301 APPROVED независимым reviewer; runtime повторно проверен через Compose/HTTPS.
