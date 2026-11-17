import { test, expect } from "@playwright/test";

const password = process.env.CRM_E2E_PASSWORD;
if (!password) throw new Error("Synthetic CRM_E2E_PASSWORD required");

async function login(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page
    .getByLabel("Email", { exact: true })
    .fill(process.env.CRM_E2E_EMAIL || "demo@example.com");
  await page.getByLabel("Пароль", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Контакты/ })).toBeVisible();
}

test("search shortcut, active filters and empty-result recovery", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await expect(page.getByLabel("Email", { exact: true })).toBeVisible();
  await page.screenshot({
    animations: "disabled",
    path: "../.ai/scratch/ui-login.png",
  });
  await login(page);
  await page
    .getByLabel("Рабочее пространство")
    .selectOption({ label: "◎ Семья" });
  await expect(
    page.getByRole("button", { name: "Открыть Александр Тестов", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    animations: "disabled",
    path: "../.ai/scratch/ui-desktop.png",
    fullPage: true,
  });
  await page.keyboard.press("Control+k");
  await expect(page.getByLabel("Поиск контактов")).toBeFocused();
  await page.getByRole("button", { name: "Фильтры", exact: true }).click();
  await page
    .getByLabel("Город", { exact: true })
    .fill("Несуществующий-город-UI");
  await expect(
    page.getByRole("heading", { name: "Ничего не найдено" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /^Фильтры/ }).click();
  await expect(page.getByRole("button", { name: /^Фильтры/ })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  await expect(page.getByRole("button", { name: /^Фильтры/ })).toContainText(
    "1",
  );
  await page.screenshot({
    animations: "disabled",
    path: "../.ai/scratch/ui-no-results.png",
  });
  await page
    .getByRole("button", { name: "Сбросить поиск и фильтры", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Открыть Александр Тестов", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Открыть Александр Тестов", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "Александр Тестов", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    animations: "disabled",
    path: "../.ai/scratch/ui-details.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Редактировать", exact: true })
    .click();
  await page.screenshot({
    animations: "disabled",
    path: "../.ai/scratch/ui-editor.png",
  });
  await page.keyboard.press("Control+k");
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByLabel("Имя / ФИО")).toBeFocused();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: "Открыть граф" }).click();
  await expect(page.getByLabel("От кого", { exact: true })).not.toHaveValue("");
  await page.getByRole("button", { name: "Показать связи" }).click();
  await expect(page.locator(".graph-canvas canvas").first()).toBeVisible();
  await expect(page.getByText(/людей · нажмите/)).toBeVisible();
  await page.screenshot({
    animations: "disabled",
    path: "../.ai/scratch/ui-graph.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Увеличить граф", exact: true })
    .click();
  await page.getByText(/^Люди на графе/).click();
  await expect(
    page
      .locator(".graph-people")
      .getByRole("button", { name: "Александр Тестов", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "AI Inbox", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "AI Inbox", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    animations: "disabled",
    path: "../.ai/scratch/ui-inbox.png",
    fullPage: true,
  });
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  await page.screenshot({
    animations: "disabled",
    path: "../.ai/scratch/ui-settings.png",
    fullPage: true,
  });
});

test("narrow screens preserve contact actions and editor scroll", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await page
    .getByLabel("Рабочее пространство")
    .selectOption({ label: "◎ Семья" });
  await expect(
    page.getByRole("button", { name: "Открыть Александр Тестов", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    animations: "disabled",
    path: "../.ai/scratch/ui-mobile.png",
    fullPage: true,
  });
  for (const width of [320, 390, 768, 1024]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBeTruthy();
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page
    .getByRole("button", { name: "Открыть Александр Тестов", exact: true })
    .click();
  await page.screenshot({
    animations: "disabled",
    path: "../.ai/scratch/ui-mobile-details.png",
    fullPage: true,
  });
  await page
    .getByRole("button", { name: "Редактировать", exact: true })
    .click();
  await expect(page.getByLabel("Имя / ФИО")).toBeFocused();
  await page.getByRole("button", { name: "Добавить способ связи" }).click();
  await page.getByLabel("Значение 2", { exact: true }).scrollIntoViewIfNeeded();
  await page.screenshot({
    animations: "disabled",
    path: "../.ai/scratch/ui-mobile-editor.png",
  });
  await expect(
    page.getByRole("button", { name: "Сохранить изменения" }),
  ).toBeInViewport();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBeTruthy();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

test("80-person graph fits the narrowest viewport and table text stays readable", async ({
  page,
}) => {
  await login(page);
  await page
    .getByLabel("Рабочее пространство")
    .selectOption({ label: "◎ Семья" });
  await expect(
    page.getByRole("button", { name: "Открыть Александр Тестов", exact: true }),
  ).toBeVisible();
  await page.locator(".person-cell").first().hover();
  const contrast = await page.evaluate(() => {
    function luminance(rgb: string) {
      const values = rgb
        .match(/[\d.]+/g)!
        .slice(0, 3)
        .map(Number)
        .map((v) => {
          const c = v / 255;
          return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
        });
      return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2];
    }
    const header = getComputedStyle(document.querySelector("th")!);
    const profession = getComputedStyle(
      document.querySelector(".person-cell small")!,
    );
    const panel = getComputedStyle(document.querySelector(".table-panel")!);
    const hoveredRow = getComputedStyle(document.querySelector("tbody tr")!);
    return [
      (luminance(header.backgroundColor) + 0.05) /
        (luminance(header.color) + 0.05),
      (luminance(panel.backgroundColor) + 0.05) /
        (luminance(profession.color) + 0.05),
      (luminance(hoveredRow.backgroundColor) + 0.05) /
        (luminance(profession.color) + 0.05),
    ];
  });
  for (const ratio of contrast) expect(ratio).toBeGreaterThanOrEqual(4.5);
  await page
    .getByRole("button", { name: "Открыть Александр Тестов", exact: true })
    .click();
  await page.getByRole("button", { name: "Открыть граф", exact: true }).click();
  await expect(page.getByLabel("От кого", { exact: true })).not.toHaveValue("");
  const root = await page.getByLabel("От кого", { exact: true }).inputValue();
  await page.route("**/graph?*", async (route) => {
    const nodes = Array.from({ length: 80 }, (_, i) => ({
      id: i ? `00000000-0000-4000-8000-${String(i).padStart(12, "0")}` : root,
      display_name: `Тестовый участник ${i}`,
      connections: [],
    }));
    const edges = nodes.slice(1).map((p, i) => ({
      id: `edge-${i}`,
      from_person_id: root,
      to_person_id: p.id,
      type: "Знакомые",
      directed: false,
    }));
    await route.fulfill({ json: { nodes, edges, path: [], truncated: false } });
  });
  await page
    .getByRole("button", { name: "Показать связи", exact: true })
    .click();
  await expect(
    page.getByText("Люди на графе · 80", { exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ width: 320, height: 900 });
  await page
    .getByRole("button", { name: "Показать весь граф", exact: true })
    .click();
  await expect
    .poll(() =>
      page.locator(".graph-canvas").evaluate((el) => {
        // Cytoscape's container registration: observe rendered bounds, never alter layout.
        const cy = (
          el as HTMLElement & { _cyreg: { cy: import("cytoscape").Core } }
        )._cyreg.cy;
        const box = cy.elements().renderedBoundingBox();
        return (
          box.x1 >= -1 &&
          box.y1 >= -1 &&
          box.x2 <= cy.width() + 1 &&
          box.y2 <= cy.height() + 1
        );
      }),
    )
    .toBeTruthy();
  await page.locator(".graph-frame").screenshot({
    path: "../.ai/scratch/ui-graph-80-mobile.png",
    animations: "disabled",
  });
});
