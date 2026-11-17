import { test, expect } from "@playwright/test";
import { contactPreview } from "../src/contact-preview";
import type { Contact } from "../src/api";

const contact: Contact = {
  platform: "email",
  kind: "email",
  value: "synthetic@example.com",
  label: "Рабочий",
  is_primary: true,
  source: "Исходный источник",
  verification: "unverified",
};

test("AI contact preview exposes source changes and clearing", () => {
  expect(contactPreview(contact)).toContain("Источник: Исходный источник");
  expect(contactPreview({ ...contact, source: "Новый источник" })).toContain(
    "Источник: Новый источник",
  );
  expect(contactPreview({ ...contact, source: "" })).toContain(
    "Источник: Не указан",
  );
});

test("AI contact preview exposes both verification states on create and update", () => {
  expect(contactPreview(contact)).toContain("Проверка: Не проверен");
  const verified = contactPreview({ ...contact, verification: "verified" });
  expect(verified).toContain("Проверка: Подтверждён");
  expect(verified).not.toEqual(contactPreview(contact));
  expect(contactPreview({ ...contact, verification: "unverified" })).toContain(
    "Не проверен",
  );
});

test("AI contact preview preserves every editable contact field", () => {
  const full = contactPreview(contact);
  for (const value of [
    "email · email",
    "synthetic@example.com",
    "Метка: Рабочий",
    "Основной: Да",
    "Исходный источник",
    "Не проверен",
  ])
    expect(full).toContain(value);
  const cleared = contactPreview({ ...contact, label: "", is_primary: false });
  expect(cleared).toContain("Метка: Не указана");
  expect(cleared).toContain("Основной: Нет");
});
