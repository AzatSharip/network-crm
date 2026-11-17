import { useEffect, useState } from "react";
import { Check, X, Inbox as InboxIcon } from "lucide-react";
import { api, errorMessage, type Suggestion, type Member } from "./api";
import { Button } from "./components/ui/button";
const labels: Record<string, string> = {
  display_name: "Имя",
  city: "Город",
  country: "Страна",
  profession: "Профессия",
  notes: "Заметки",
  tags: "Теги",
  contacts: "Способы связи",
  organizations: "Организации",
  connections: "Кто знаком",
  competencies: "Компетенции",
  description: "Описание",
  aliases: "Другие имена",
  first_name: "Имя",
  last_name: "Фамилия",
  middle_name: "Отчество",
  from_person_id: "От кого",
  to_person_id: "К кому",
  type: "Тип связи",
  directed: "Направленная",
  comment: "Комментарий",
  source: "Источник",
};
export function Inbox({
  base,
  canEdit,
  members,
}: {
  base: string;
  canEdit: boolean;
  members: Member[];
}) {
  const [names, setNames] = useState<Record<string, string>>({});
  const [items, setItems] = useState<Suggestion[]>([]);
  const [sources, setSources] = useState<Record<string, string>>({});
  const [status, setStatus] = useState("pending");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");
  async function load() {
    try {
      const [ss, src] = await Promise.all([
        api<Suggestion[]>(base + "/suggestions?status=" + status),
        api<{ id: string; name: string }[]>(base + "/sources"),
      ]);
      const ids = [
        ...new Set(
          ss
            .filter((s) => s.operation === "create_relationship")
            .flatMap((s) =>
              Object.entries(s.payload)
                .filter(([k]) => k === "from_person_id" || k === "to_person_id")
                .map(([, v]) => String(v)),
            ),
        ),
      ];
      const people = await Promise.all(
        ids.map((id) =>
          api<{ id: string; display_name: string }>(base + "/people/" + id),
        ),
      );
      setNames(Object.fromEntries(people.map((p) => [p.id, p.display_name])));
      setItems(ss);
      setSources(Object.fromEntries(src.map((s) => [s.id, s.name])));
    } catch (e) {
      setError(errorMessage(e));
    }
  }
  useEffect(() => {
    void load();
  }, [base, status]);
  async function review(id: string, decision: string) {
    setBusy(id);
    setError("");
    try {
      await api(base + "/suggestions/" + id + "/" + decision, "POST");
      await load();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy("");
    }
  }
  const render = (key: string, value: unknown): string => {
    if (
      value === undefined ||
      value === null ||
      value === "" ||
      (Array.isArray(value) && !value.length)
    )
      return "Не указано";
    if (key === "from_person_id" || key === "to_person_id")
      return names[String(value)] || "Контакт";
    if (typeof value === "boolean") return value ? "Да" : "Нет";
    if (Array.isArray(value))
      return value
        .map((item) => {
          if (typeof item === "string") return item;
          if (key === "contacts")
            return `${item.platform} · ${item.kind === "numeric_id" ? "ID" : item.kind}: ${item.value}${item.label ? " (" + item.label + ")" : ""}${item.is_primary ? " · основной" : ""}`;
          if (key === "organizations")
            return `${item.name}${item.title ? " · " + item.title : ""}`;
          if (key === "connections")
            return `${members.find((m) => m.user_id === item.user_id)?.name || "Участник"}: ${item.knows ? "знаком" : "не отмечено"}${item.priority ? " · приоритет " + item.priority : ""}${item.is_primary ? " · основной знакомый" : ""}`;
          return JSON.stringify(item);
        })
        .join("\n");
    return String(value);
  };
  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">ВЫ РЕШАЕТЕ, ЧТО СОХРАНИТЬ</span>
          <h1>AI Inbox</h1>
          <p>
            Предложения из ваших источников. Изменения вступают в силу после
            подтверждения.
          </p>
        </div>
        <select
          aria-label="Статус предложений"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="pending">Ожидают решения</option>
          <option value="applied">Применены</option>
          <option value="rejected">Отклонены</option>
        </select>
      </div>
      {error && (
        <div role="alert" className="error">
          {error}
        </div>
      )}
      {!items.length && (
        <div className="empty panel">
          <InboxIcon size={40} />
          <h2>Здесь всё разобрано</h2>
          <p>Новые предложения появятся после импорта через API.</p>
        </div>
      )}
      {items.map((s) => (
        <section className="panel suggestion" key={s.id}>
          <div className="section-heading">
            <div>
              <span className="eyebrow">
                {s.operation === "create_person"
                  ? "НОВЫЙ КОНТАКТ"
                  : s.operation === "update_person"
                    ? "ИЗМЕНЕНИЕ КАРТОЧКИ"
                    : "НОВАЯ СВЯЗЬ"}
              </span>
              <h2>{s.payload.display_name || "Связь между людьми"}</h2>
              <p className="muted">
                Источник: {sources[s.source_id] || "Источник"} · Уверенность:{" "}
                {s.confidence}%
              </p>
            </div>
            <span className="tag">
              {status === "pending"
                ? "На проверке"
                : status === "applied"
                  ? "Применено"
                  : "Отклонено"}
            </span>
          </div>
          <div className="diff-header">
            <span>Поле</span>
            <span>Сейчас</span>
            <span>Предложено</span>
          </div>
          {Object.entries(s.payload)
            .filter(([key, value]) => {
              const before = (s.before as Record<string, unknown>)[key];
              const empty = (v: unknown) =>
                v === undefined ||
                v === null ||
                v === "" ||
                (Array.isArray(v) && v.length === 0);
              return (
                JSON.stringify(value) !== JSON.stringify(before) &&
                !(empty(value) && empty(before))
              );
            })
            .map(([key, value]) => (
              <div className="diff" key={key}>
                <strong>{labels[key] || key}</strong>
                <pre>
                  {render(key, (s.before as Record<string, unknown>)[key])}
                </pre>
                <pre>{render(key, value)}</pre>
              </div>
            ))}
          {status === "pending" && canEdit && (
            <div className="inline actions">
              <Button
                disabled={busy === s.id}
                onClick={() => void review(s.id, "approve")}
              >
                <Check size={17} />
                Подтвердить
              </Button>
              <Button
                disabled={busy === s.id}
                variant="outline"
                onClick={() => void review(s.id, "reject")}
              >
                <X size={17} />
                Отклонить
              </Button>
            </div>
          )}
        </section>
      ))}
    </>
  );
}
