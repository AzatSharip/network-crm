import { test, expect } from "@playwright/test";
const email = process.env.CRM_E2E_EMAIL || "demo@example.com";
const password = process.env.CRM_E2E_PASSWORD;
if (!password)
  throw new Error("CRM_E2E_PASSWORD required; synthetic local account only");
async function login(page: any) {
  await page.goto("/");
  await page.getByLabel("Email", { exact: true }).fill(email);
  await page.getByLabel("Пароль", { exact: true }).fill(password!);
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await expect(page.getByRole("heading", { name: /Контакты/ })).toBeVisible();
}
test("create dynamic contacts, search, edit, relationship, graph, Inbox and logout", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await login(page);
  await page
    .getByLabel("Рабочее пространство")
    .selectOption({ label: "◎ Семья" });
  await page
    .getByRole("button", { name: "Добавить контакт", exact: true })
    .click();
  const name = "Браузерный Тест " + Date.now();
  await page.getByLabel("Имя / ФИО").fill(name);
  await page.getByLabel("Город", { exact: true }).fill("Уфа");
  await page.getByLabel("Профессия", { exact: true }).fill("Стоматолог");
  await page.getByRole("button", { name: "Добавить способ связи" }).click();
  await page
    .getByLabel("Платформа 1", { exact: true })
    .selectOption("telegram");
  await page
    .getByLabel("Вид идентификатора 1", { exact: true })
    .selectOption("numeric_id");
  await page.getByLabel("Значение 1", { exact: true }).fill(String(Date.now()));
  await page.getByRole("button", { name: "Добавить способ связи" }).click();
  await page.getByLabel("Платформа 2", { exact: true }).selectOption("email");
  await page
    .getByLabel("Значение 2", { exact: true })
    .fill("browser" + Date.now() + "@example.com");
  await page
    .getByRole("button", { name: "Добавить контакт", exact: true })
    .last()
    .click();
  await expect(page.getByRole("heading", { name, exact: true })).toBeVisible();
  await page
    .getByRole("button", { name: "Редактировать", exact: true })
    .click();
  await page.getByLabel("Страна", { exact: true }).fill("Казахстан");
  await page.getByRole("button", { name: "Сохранить изменения" }).click();
  await expect(page.getByText("Уфа, Казахстан", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Все контакты" }).click();
  await page.getByLabel("Поиск контактов").fill(name);
  await expect(
    page.getByRole("button", { name: name + " Стоматолог" }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Открыть " + name, exact: true })
    .click();
  await page
    .getByRole("button", { name: "Добавить связь", exact: true })
    .click();
  await page.getByLabel("Поиск: Связанный человек").fill("Александр");
  await expect(
    page.getByLabel("Связанный человек", { exact: true }).locator("option"),
  ).toHaveCount(2);
  await page
    .getByLabel("Связанный человек", { exact: true })
    .selectOption({ label: "Александр Тестов" });
  await page.getByRole("button", { name: "Сохранить связь" }).click();
  await expect(
    page.getByRole("button", { name: "Александр Тестов", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Открыть граф" }).click();
  await page.getByRole("button", { name: "Показать связи" }).click();
  await expect(page.locator(".graph-canvas canvas").first()).toBeVisible();
  await expect(page.getByText(/людей · нажмите/)).toBeVisible();
  await page.getByRole("button", { name: "AI Inbox", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "AI Inbox", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Выйти", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Рады видеть вас" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
test("mobile layout and keyboard editor", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await login(page);
  await page
    .getByRole("button", { name: "Добавить контакт", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByLabel("Имя / ФИО")).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).not.toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({ path: "../.ai/scratch/mobile.png", fullPage: true });
});

test("AI approval and invitation confirmation work through the UI", async ({
  page,
  browser,
}) => {
  await login(page);
  await page
    .getByLabel("Рабочее пространство")
    .selectOption({ label: "◎ Семья" });
  const wid = await page.getByLabel("Рабочее пространство").inputValue();
  const name = "AI Браузер " + Date.now();
  await page.evaluate(
    async ({ wid, name }) => {
      const csrf = document.cookie
        .split("; ")
        .find((c) => c.startsWith("crm_csrf="))!
        .split("=")[1];
      const headers = {
        "Content-Type": "application/json",
        "X-CSRF-Token": csrf,
      };
      const base = "/api/v1/workspaces/" + wid;
      const source = await fetch(base + "/sources", {
        method: "POST",
        headers,
        body: JSON.stringify({ name: "Синтетический браузерный тест" }),
      }).then((r) => r.json());
      const r = await fetch(base + "/suggestions", {
        method: "POST",
        headers,
        body: JSON.stringify({
          operation: "create_person",
          source_id: source.id,
          payload: { display_name: name, city: "Уфа" },
          confidence: 90,
          job_key: crypto.randomUUID(),
          record_key: "1",
        }),
      });
      if (!r.ok) throw new Error("Cannot create synthetic suggestion");
    },
    { wid, name },
  );
  await page.getByRole("button", { name: "AI Inbox", exact: true }).click();
  const card = page.locator(".suggestion").filter({ hasText: name });
  await card.getByRole("button", { name: "Подтвердить", exact: true }).click();
  await expect(card).toHaveCount(0);
  await page.getByRole("button", { name: "Контакты", exact: true }).click();
  await page.getByLabel("Поиск контактов").fill(name);
  await expect(
    page.getByRole("button", { name: "Открыть " + name, exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Настройки", exact: true }).click();
  const inviteEmail = "invite" + Date.now() + "@example.com";
  await page.getByLabel("Email", { exact: true }).fill(inviteEmail);
  await page.getByLabel("Роль", { exact: true }).selectOption("viewer");
  await page.getByRole("button", { name: "Создать приглашение" }).click();
  const link = await page.getByLabel("Ссылка приглашения").inputValue();
  const invited = await browser.newContext();
  const other = await invited.newPage();
  await other.goto(link);
  await other
    .getByLabel("Ваше имя", { exact: true })
    .fill("Приглашённый тестовый");
  await other
    .getByLabel("Пароль", { exact: true })
    .fill("Synthetic-invited-password-123!");
  await other.getByRole("button", { name: "Принять приглашение" }).click();
  await expect(
    other.getByText("Приглашение принято. Теперь войдите в аккаунт."),
  ).toBeVisible();
  await other.getByRole("button", { name: "Войти", exact: true }).click();
  await other
    .getByLabel("Рабочее пространство")
    .selectOption({ label: "◎ Семья" });
  await expect(
    other.getByRole("button", { name: "Добавить контакт", exact: true }),
  ).toHaveCount(0);
  await expect(other.getByRole("heading", { name: /Контакты/ })).toBeVisible();
  await invited.close();
});
