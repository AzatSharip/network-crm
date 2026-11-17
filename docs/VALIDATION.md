# Проверки — 2026-11-17

Проверки поведения — на синтетических данных; на Atlas выполнен вход владельца и чтение его пустых пространств. Ни секреты, ни персональные данные не попали в доказательства в Git.

| Проверка | Результат |
|---|---|
| Python ruff, frontend TypeScript/Prettier/Vite | PASS |
| PostgreSQL API integration | PASS, 32 теста, PostgreSQL18.7, отдельная одноразовая БД |
| Alembic drift / downgrade → upgrade | PASS, только отдельная тестовая БД |
| Chrome desktop через полный Compose/nginx | PASS: несколько способов связи, создание/правка/поиск, связь, граф, выход |
| Chrome mobile390×844 | PASS: без горизонтального переполнения, focus/Escape |
| AI и приглашение через UI | PASS: подтверждение AI → карточка; приглашение → принятие → вход viewer без права добавления |
| Search10k | PASS: измерен на PostgreSQL18.6; метрики и GIN plans в search-benchmark.json; exact email/name дают1 совпадение |
| Local encrypted backup/restore | PASS: 8 persons/2 workspaces/1 suggestion; повреждённый ciphertext отвергнут; временные БД удалены |
| Atlas encrypted backup/restore | PASS: 0 persons/2 workspaces/0 suggestions, migration0001; ежедневный timer enabled |
| Off-host копия | PASS: копия на Mac, совпадение SHA-256 с restore receipt, расшифровка независимым ключом |
| pip-audit / npm audit | PASS: без известных уязвимостей на момент проверки |
| Gitleaks tree/staged/history | PASS staged; history/tree проверяются на финальном commit |
| Full Docker Compose | PASS: local и Atlas healthy, one-shot migration успешна, web200/unauthenticated API401 |
| Atlas owner smoke | PASS: вход, Personal/Family пустые, выход; реальные карточки не создавались |
| Существующие сервисы Atlas | PASS: 23 контейнера сохранили StartedAt/status/health; shared ingress unchanged |
| HTTPS candidate | PASS: доверенный отдельный сертификат; nginx -t на конкретном добавочном vhost; public route ещё не применён |
| Real public HTTPS login / renewal | Публичный маршрут ещё не применён; certbot dry-run выполняется |
| Independent exact-commit review | PENDING |

API-тесты покрывают IDOR/BOLA, FORCE RLS с runtime-ролью, viewer/editor, CSRF/Origin, logout/revoke-all/password change, Secure/__Host cookies в HTTPS-режиме, rate/body limits, небезопасные URL, Telegram ID, cross-platform phone/email duplicate warning, idempotency, optimistic versions, направленный bounded graph, expiring one-use invitations, limited/revoked agent tokens, conflict rollback, preview удаляемых AI-полей. Отдельный regression проверяет, что ошибка commit возвращает ошибку HTTP и откатывает карточку до отправки успешного ответа.

Эти проверки не являются независимым pentest. Локальный HTTPS cookie test не подменяет реальный публичный TLS smoke. Search benchmark и локальный backup снимались до последних UI/transaction изменений; версия и данные явно указаны. Физическое мобильное устройство не проверено.
