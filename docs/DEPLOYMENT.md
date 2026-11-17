# Развёртывание

Compose изолирует проект `network-crm`: PostgreSQL в internal network, API без host ports, nginx только `127.0.0.1:8080`. Реальные данные в named volume вне Git; секреты в отдельном env-файле вне checkout (600). Не запускать общий prune и не менять чужие сети/volumes.

1. Создайте два разных длинных URL-safe пароля, перенесите имена переменных из `.env.example` в защищённый внешний файл. Укажите точный APP_ORIGIN. Для локальной проверки `http://localhost:8080`; для публичного доступа — согласованный `https://...`.
2. `docker compose --env-file /защищённый/путь/network-crm.env up -d --build` (или `docker-compose`, если plugin недоступен). Миграции запускаются отдельным one-shot сервисом перед API.
3. `docker compose --env-file /защищённый/путь/network-crm.env exec api python -m app.cli bootstrap --email you@example.com --name 'Ваше имя'`. Пароль вводится интерактивно, не через аргументы. Bootstrap закрывается после первого пользователя.
4. Откройте локальный адрес, проверьте вход, Personal/Family, создание/поиск/редактирование, приглашение, запрет viewer и чужого Personal.
5. До интернета: согласуйте домен/DNS/маршрут; выпустите доверенный сертификат через существующий механизм с auto-renew; проверьте `nginx -t`, TLS/redirect, Secure cookies, CSRF, отсутствие публичных API/DB ports и конфликта существующих vhosts. Только затем включайте новый vhost. `deploy/https.conf.example` — шаблон, не готовый действующий домен. HSTS включайте после проверки стабильности HTTPS.
6. Настройте и проверьте шифрованные бэкапы (BACKUP_RESTORE.md). Выберите MFA перед публичным запуском или явно примите ограничение password-only.

Тестовый override `deploy/compose.test.yaml` публикует PostgreSQL только на loopback 18432 и использует заранее доступный PostgreSQL 18.6 для локальной разработки. Его нельзя применять к публичному размещению. Production target — PostgreSQL 18.7. Scripts local-env.py предназначен для этой рабочей станции; в CI/других окружениях задавайте DATABASE_URL/MIGRATION_DATABASE_URL явно. Runtime crm_app и migration crm_migrator разделены. Migration role имеет административные права только внутри выделенного PostgreSQL контейнера.

Обновление: backup + restore-check → записать текущий image digest и revision → собрать новый образ → применить миграцию → проверить CRM health и smoke → при ошибке оставить прежние образы/копию для согласованного отката. Не удалять прежний volume. Обновления PostgreSQL major требуют отдельного плана.

Atlas: первоначально только read-only audit ресурсов, портов, проектов, сети/volumes, reverse proxy, TLS и firewall. Конкретные адреса/доступы не должны попадать в публичную документацию. Итог live-аудита и фактическое размещение будут отмечены в PROGRESS/VALIDATION, а чувствительные детали — во внешнем приватном журнале.
