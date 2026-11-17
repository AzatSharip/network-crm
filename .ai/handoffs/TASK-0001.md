# Прогресс MVP
Дата: 2026-11-17. Этап B–E: реализация и практическая проверка.

Написаны модели/замороженная Alembic migration, FastAPI API (sessions/CSRF, Personal/Family, invites, контакты, теги, организации, связи, поиск, граф, AI review, agent tokens, audit), русский React UI, Compose, backup/restore scripts, документация и тесты. Это пока реализованный код, не подтверждённая готовность.

Проверено: frontend TypeScript/Vite build PASS; ruff PASS; pip-audit без известных уязвимостей; npm audit после установки без уязвимостей; первоначальная Git history и исходники Gitleaks без находок. Реальная интеграция/браузер/backup/10k benchmark ещё не завершены.

Локальный Colima отвечает, существующие контейнеры не затронуты. Bind mount из macOS Documents блокирует запуск нового DB-контейнера; обход: immutable DB image с COPY init script, отдельный network-crm-local проект, cached PostgreSQL18.6 для тестов. Production target18.7. Runtime env вне репозитория: стандартный приватный каталог приложения, local-env.py задаёт URLs без печати секретов. Стандартный network-crm-db-1 остаётся Created, не работает; удалить лишь собственный объект после снятия блокировки. Не перезапускать Docker/Colima без согласования из-за чужих сервисов.

Остались все практические acceptance-проверки: migrations/integration, браузер, benchmark10k, backup restore, full Compose, Atlas read-only audit, HTTPS/public endpoints, независимое exact-commit review. GitHub remote отсутствует; первый публичный push отдельно подтверждается. Лицензия не выбрана. Следующее действие: запустить отдельный DB без host bind mount и выполнить scripts/test.py.
