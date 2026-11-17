# TASK-0002 — independent UI review

**CHANGES_REQUIRED** — exact implementation `5cc703bdef2947d5310a39ea20c0338c4925b1bb`, base/main `2b56ab11f2a238448dac38bb547fda2ab1b46345`. Один reviewer; production edits, integration, push/deploy не выполнялись.

Scope: App.tsx, Graph.tsx, styles.css, interface tests/docs; регрессии, keyboard UX, responsive layout и выбранные accessibility checks. Backend/dependencies/auth не изменены и повторно не аудировались.

## U1 — P2: «Показать весь граф» не вмещает допустимый граф на ширине 320

Место: `frontend/src/Graph.tsx:303–308` вместе с `minZoom: 0.3` на строке 207 и текущим layout.

При ширине viewport 320px граф из 80 узлов после fit остаётся шире canvas. Fit упирается в minimum zoom; кнопка уменьшения тоже ограничена 0.3. Крайние подписи обрезаются, пользователь не может получить обещанный полный обзор одним действием. Panning и новый список людей работают, поэтому это ограниченный UX/responsive defect, не потеря данных.

Repro без записей backend: войти synthetic account, открыть карточку → граф; перехватить только GET /graph и вернуть 80 nodes, 79 star edges от root, display_name «Тестовый участник N», connections=[], path=[], truncated=false. Root — реальный выбранный UUID, остальные UUID синтетические. Дождаться загрузки picker options до получения root (иначе тестовый fixture ошибочно содержит пустой ID). Показать связи, установить viewport320, нажать «Показать весь граф».

В текущем Chrome после явного resize+fit измерено: canvas width290 / height420, zoom0.3, rendered bounding box x1=-6.58, x2=296.58, width303.17. Скриншот также показал обрезанные подписи по обоим краям. При 390 и 1440 тот же fixture помещается. CoSE размещение недетерминированно; проверять границы, а не конкретные координаты. Сам minZoom существовал раньше; finding относится к новому full-fit control и новому layout, а не к утверждению, что весь старый граф ранее соответствовал этому обещанию.

Нужно разрешить fit zoom ниже текущего порога либо адаптировать layout/ограничение к размеру контейнера; добавить bounded graph regression на 320px, проверяющий реальные rendered bounds после кнопки fit, а не только наличие canvas.

## U2 — P2: мелкий содержательный текст новой палитры ниже minimum contrast

Место: `frontend/src/styles.css:594–600` и `:640–644`.

В реальном Chrome получены computed styles, затем рассчитана relative-luminance contrast ratio:

| Текст | Foreground / background | Размер | Ratio |
|---|---|---|---|
| Профессия под именем (`.person-cell small`) | #777b70 / #ffffff | 11px | 4.329:1 |
| Заголовки таблицы (`th`) | #73766b / #f9f9f6 | 10px | 4.392:1 |

Это обычный содержательный текст, не disabled/decorative и не large text. Ориентир accessibility acceptance — минимум 4.5:1 для такого текста; округлять значение вверх до проходного нельзя. Источник: [W3C WCAG 2.2 SC1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html). Палитра улучшает некоторые прежние значения, но подтверждение readable contrast для обновлённой системы остаётся неполным. Это acceptance gap редизайна, не заявление об ухудшении всех прежних контрастов.

Нужно затемнить указанные foreground или изменить backgrounds до >=4.5:1 с запасом; проверить default/hover backgrounds. Полный WCAG audit не проводился.

## Проверки и ограничения

- Preflight: clean checkout, exact HEAD/base подтверждены; локальные API8000/Vite8080 доступны; Node22.22.0 и Chrome/Playwright работают. Synthetic credentials загружались штатным launcher/аналогичным дочерним процессом вне Git, не выводились. Production/Atlas не использовались.
- Первый E2E: 3 renderer PASS, 5 browser FAIL на login HTTP429. У demo-account накопилось 17 попыток от предыдущих прогонов. Проверены localhost18432 и synthetic @example.com account; удалена только его hashed account limiter row. IP counters, runtime policy, пароли и код не изменены. Это test-environment contention, не UI finding.
- Повтор `PATH=/Users/macbook/.nvm/versions/node/v22.22.0/bin:$PATH python3 scripts/run-e2e.py`: **PASSED 8/8**, 12.4s (5 Chrome E2E +3 renderer). Покрыты CRUD, AI/invites/viewer, Ctrl+K, hidden filters/reset, widths320/390/768/1024, editor scroll/focus, graph list.
- `npm --prefix frontend run lint` и `run build` с Node22.22.0: **PASSED**.
- Независимые browser checks: **PASSED** Meta+K focus, Tab остаётся в dialog, Escape, footer visible/no document overflow на320×568 и844×390 (editor body345.7px и146.7px), graph list keyboard Enter открывает карточку, no browser JS errors. **FAILED** U1 на320 и U2 computed contrast.
- Выборочно визуально проверены synthetic desktop list, mobile editor, graph и reviewer320 graph screenshot. Остальные экраны проверены E2E, не все screenshots отдельно просмотрены reviewer. Screenshots/one-off probe находятся в ignored scratch; durable repro/числа приведены выше, продолжение не зависит от scratch.
- Initial independent graph probe был исправлен: дождаться async picker options перед чтением root. Его пустой fixture ID не был дефектом приложения; итоговые результаты получены с корректным fixture.
- Physical phone, Safari, screen reader, полный WCAG audit, deployment: **NOT TESTED**. Прежние API/security/audit suites не повторялись.
- `git diff --check main HEAD`: **PASSED**; новые зависимости/backend/auth changes отсутствуют.

## Продолжение

Исправить только U1/U2, затем предъявить новый exact SHA тому же reviewer для bounded delta review. До APPROVED не интегрировать. Main остаётся2b56ab1; TASK-0002 review/changes_required. Проверки остальных сценариев выше не нужно повторять без новой причины.
