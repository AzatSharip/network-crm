# Network CRM

Персональная и семейная CRM на русском: быстрый поиск людей, универсальные способы связи, граф знакомств и AI Inbox с подтверждением изменений. React/TypeScript/Vite + FastAPI/SQLAlchemy/Alembic + PostgreSQL. Без внешних AI API и лишних инфраструктурных сервисов.

Текущее проверенное состояние и ограничения: [PROGRESS](docs/PROGRESS.md). Лицензия [MIT](LICENSE), выбрана владельцем; первая публичная публикация требует отдельного подтверждения.

## Запуск через Compose

Нужны Docker с Compose и свободный loopback-порт 8080. Создайте приватный env-файл **вне каталога исходников**, используя имена переменных из [.env.example](.env.example), с двумя разными случайными URL-safe паролями и `APP_ORIGIN=http://localhost:8080`. Установите mode 600.

```sh
docker compose --env-file /защищённый/путь/crm.env up -d --build
docker compose --env-file /защищённый/путь/crm.env exec api \
  python -m app.cli bootstrap --email you@example.com --name 'Ваше имя'
```

Введите новый пароль интерактивно. Откройте `http://localhost:8080`. Первый пользователь получает Personal и Family. Bootstrap после этого закрыт; другие участники присоединяются по приглашению из «Настроек». Personal не копируется в Family. PostgreSQL и API не публикуют порты наружу.

В форме достаточно имени. Можно добавить несколько телефонов, email, Telegram username/ID/URL и других способов связи, организации, теги и знакомых участников. Совпадение идентификатора вызывает предупреждение, а не автоматическое слияние. Поиск работает по всем этим сведениям; граф ограничивает глубину и размер.

## Разработка и проверки

Python 3.12+, Node 22.12+ (CI закреплён на 22.23.5), PostgreSQL 18 с pg_trgm. Создайте `.venv`, установите `backend/requirements.txt`; в frontend выполните `npm ci`. Runtime-зависимости отдельно закреплены в `requirements-runtime.txt`.

Задайте DATABASE_URL (роль crm_app без superuser/BYPASSRLS), MIGRATION_DATABASE_URL (отдельная административная роль), APP_ORIGIN и PYTHONPATH=backend. Роль crm_app создаётся в init-db.sh. Тесты сами создают/удаляют уникальную `crm_test_*` БД; никогда не запускают TRUNCATE в боевой БД.

```sh
python -m alembic -c backend/alembic.ini upgrade head
python scripts/test.py
ruff check backend scripts deploy/*.py
ruff format --check backend scripts deploy/*.py
pip-audit -r backend/requirements.txt
cd frontend
npm run build
cd ..
node --test scripts/tests/audit-frontend.test.mjs
node scripts/audit-frontend.mjs
```

Для браузерных тестов укажите CRM_E2E_URL, CRM_E2E_EMAIL и CRM_E2E_PASSWORD **синтетического** аккаунта и выполните `npm test` в frontend. Используется установленный Chrome. `scripts/seed-demo.py` создаёт вымышленные контакты только в пустой БД и только с CRM_SEED_SYNTHETIC=yes; случайный пароль записывается вне Git. `scripts/benchmark.py` создаёт отдельную БД с 10k вымышленных карточек, снимает метрики и удаляет её.

`deploy/compose.test.yaml` — исключительно локальный override: порт PostgreSQL на loopback, PostgreSQL18.7 и локальные параметры образов. Production-конфигурация также использует18.7. `scripts/local-env.py` — вспомогательный загрузчик приватного env текущего Mac; для других машин используйте явные переменные окружения.

## Документация

- [Архитектура](docs/ARCHITECTURE.md), [модель данных](docs/DATA_MODEL.md), [ADR](docs/adr/0001-architecture.md).
- [API](docs/API.md), [поиск](docs/SEARCH.md), [результаты benchmark](docs/search-benchmark.json).
- [Безопасность](docs/SECURITY.md), [развёртывание и HTTPS](docs/DEPLOYMENT.md), [backup/restore](docs/BACKUP_RESTORE.md).
- [Roadmap](docs/ROADMAP.md), [варианты лицензии](docs/LICENSE_OPTIONS.md), [правила агентов](AGENTS.md).

Перед публичным GitHub push: Gitleaks по всему Git history и текущим файлам, запрет data/secret путей, ручная проверка ПДн и отдельное подтверждение владельца. Настоящие контакты, переписки, дампы, ключи и runtime-конфигурация никогда не входят в Git.
