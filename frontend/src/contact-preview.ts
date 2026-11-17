import type { Contact } from "./api";

export function contactPreview(contact: Contact): string {
  return [
    `${contact.platform} · ${contact.kind === "numeric_id" ? "ID" : contact.kind}: ${contact.value}`,
    `Метка: ${contact.label || "Не указана"} · Основной: ${contact.is_primary ? "Да" : "Нет"}`,
    `Источник: ${contact.source || "Не указан"}`,
    `Проверка: ${contact.verification === "verified" ? "Подтверждён" : "Не проверен"}`,
  ].join("\n");
}
