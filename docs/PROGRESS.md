# Состояние MVP — 2026-11-17

Интерфейс обновлён в TASK-0002: approved275a7ea, независимый reviewer интегрировал main, frontend-only обновление доставлено. Новый поиск/фильтры, карточки телефона, граф и общий визуальный стиль: [Интерфейс](INTERFACE.md). [CI5cde415](https://github.com/AzatSharip/network-crm/actions/runs/44150631906) PASS:34 API+9 frontend checks, audits/Gitleaks. Backup/restore и public asset hashes/health/browser PASS; остальные26 containers не изменились.

MVP реализован, независимо проверен, интегрирован в main и опубликован с разрешения владельца. Рабочий Atlas HTTPS включён после отдельного согласования. Реальные данные, URL размещения, ключи и данные владельца хранятся вне публичного Git.

| Критерии исходного задания | Подтверждение |
|---|---|
| 1–16: Compose, вход, пространства, приглашения, карточки/поиск/связи/граф/API/AI | PASS: полный Compose,34 API-теста и6 frontend checks (3 Chrome E2E +3 renderer tests) |
| 17–19: изоляция, основные проверки безопасности, тесты | PASS: отрицательные сценарии и независимое APPROVED6de1301; известное исключение build dependency раскрыто в SECURITY.md |
| 20: документация | Актуальные docs/API/security/deployment/backup/validation и handoff |
| 21–22: безопасный Git/публикация | Gitleaks source/all-history PASS, ручной осмотр, public GitHub создан с согласия; MIT выбрана владельцем |
| 23: HTTPS | PASS: доверенный отдельный сертификат, public TLS/308/HSTS/login/Secure cookie/Origin/logout; certbot dry-run и deploy hook PASS |
| 24: внутренние сервисы закрыты | API/DB без host ports, DB internal network, frontend loopback/Unix socket; LAN refused/external timeout |
| 25: Atlas не пострадал | Все23 прежних containers сохранили StartedAt/status/health, Jellyfin/Clip200 после graceful reload |

Atlas: отдельный стек, безопасный bootstrap владельца, Personal/Family пустые. Ежедневный age backup+restore-check; копии восстановлены в отдельную БД. Независимые копии архива/ключа на Mac: SHA-256 и расшифровка PASS. Автоматический off-host перенос и автоматическое удаление старых копий не включены; retention report read-only.

Независимое review: app6de1301 APPROVED после исправления гонки password/login и неполного AI preview. CI audit policy897c03e APPROVED после исправления проверки malformed reports. Main интегрирован reviewer, implementer не выполнял self-approve/merge. Первый GitHub CI прошёл API/ruff/pip/build, обнаружил обновлённый build-only picomatch advisory; повторный [CI55083a1](https://github.com/AzatSharip/network-crm/actions/runs/44142099793) полностью PASS, включая browser scenarios и скан всей истории. Все25 критериев выполнены в указанном объёме.

Ограничения: MFA, события/напоминания, история взаимодействий, готовые импортёры, управление исключением участников, удаления/экспорт и семантический поиск отложены (ROADMAP.md). Нет внешних AI API. Один известный неисправленный ReDoS advisory в dev/build picomatch4.0.7; в runtime frontend нет Node/npm/node_modules. Исключение только этого advisory и его dev-only цепочки до2026-12-17, все другие high/critical и ошибки аудита блокируются. Это не «ноль уязвимостей».

Локальная проверка: network-crm-local на loopback8081. Colima host mount Documents первоначально блокировался системным разрешением macOS; использована гостевая filesystem и git archive без AppleDouble. Старый собственный Created DB-контейнер из первой попытки не используется; общий Docker/Colima и чужие volumes не перезапускались/не удалялись.
