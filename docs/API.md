# API v1

Базовый префикс `/api/v1`. Авторизованная OpenAPI-схема: `GET /api/v1/openapi.json`; публичные Swagger/Redoc отключены. JSON input запрещает неизвестные поля. Максимум тела 256 KiB. Даты UTC ISO 8601. Ошибки: 401 вход, 403 запрет/CSRF, 404 нет доступного объекта, 409 конфликт, 422 неверные данные, 429 лимит.

Браузер: HttpOnly session cookie, отдельный читаемый `crm_csrf`; при изменении `Origin` должен равняться APP_ORIGIN, `X-CSRF-Token` — csrf cookie. При HTTPS cookie `__Host-crm_session`, Secure и SameSite=Strict. GET не изменяет данные. Bearer не требует cookie/CSRF, но допускает только POST sources/suggestions своего workspace.

| Метод и путь | Действие |
|---|---|
| POST /auth/login, /auth/logout, /auth/revoke-all | Вход, выход, отзыв всех своих сессий |
| GET /me | Текущий пользователь |
| GET/POST /workspaces | Доступные пространства / создать Family |
| GET /workspaces/{w}/members | Участники |
| POST /workspaces/{w}/invitations | Admin приглашает, токен возвращается один раз, срок 3 дня |
| POST /invitations/accept | Токен + name + password; существующему аккаунту нужен его пароль |
| GET /workspaces/{w}/people | q, city, country, profession, tag, priority, known_by, page, size (1–100) |
| POST /workspaces/{w}/people | Создать; обязательный Idempotency-Key, 1–100 символов |
| GET/PATCH /workspaces/{w}/people/{id} | Получить / атомарно заменить редактируемые поля; expected_version обязателен |
| GET /workspaces/{w}/tags, /organizations | Справочники (создаются через карточку) |
| GET/POST /workspaces/{w}/relationships | Связи по person_id / создать |
| DELETE /workspaces/{w}/relationships/{id} | Удалить связь |
| GET /workspaces/{w}/graph | root, depth 1–2, limit 1–150; target включает BFS пути до 6 уровней |
| GET/POST /workspaces/{w}/sources | Источники |
| GET/POST /workspaces/{w}/suggestions | status/page / предложение с job_key и record_key |
| POST /workspaces/{w}/suggestions/{id}/approve, /reject | Человек-editor/admin подтверждает/отклоняет; идемпотентно |
| GET/POST /workspaces/{w}/agent-tokens | Свои токены / создать на 1–90 дней |
| DELETE /workspaces/{w}/agent-tokens/{id} | Отозвать свой токен |
| GET /workspaces/{w}/audit | Admin, пагинация по 50 |

Минимальная карточка: `{"display_name":"Синтетический человек"}`. Контакты: `contacts: [{platform:"telegram",kind:"numeric_id",value:"100000001"}]`. В HTTP JSON все ключи в двойных кавычках. Подробный машинный контракт генерируется непосредственно из схем приложения.

PATCH намеренно принимает полное состояние редактируемой карточки, включая contacts/tags/organizations/connections. Отсутствующие необязательные поля получают значения по умолчанию: интегратор обязан сначала прочитать актуальную карточку. По version conflict (409) повторное применение без сверки запрещено.

Дубликаты: 409 `detail.code=duplicates`, `matches` содержит доступные карточки. Только после решения пользователя повторить с `allow_duplicate=true`. Для создания с тем же Idempotency-Key возвращается текущая карточка, а не устаревший снимок ответа. Нельзя использовать тот же ключ с другим телом.

AI операции: create_person, update_person (полная карточка + expected_version), create_relationship. Agent не читает карточки; update payload/version предоставляет уполномоченный интегратор из разрешённого источника. before сервер получает сам; agent не задаёт его. Уверенность 0–100 — метаданные, не гарантия истинности. approved — транзакционная стадия; снаружи после успешного apply виден applied. При ошибке всё откатывается в pending.
