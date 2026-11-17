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
