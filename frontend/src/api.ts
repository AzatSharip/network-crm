export type Contact = {
  platform: string;
  kind: string;
  value: string;
  label: string;
  is_primary: boolean;
  source: string;
  verification: string;
  normalized_value?: string;
};
export type Connection = {
  user_id: string;
  knows: boolean;
  priority: "A" | "B" | "C" | null;
  is_primary: boolean;
};
export type Person = {
  id?: string;
  version?: number;
  display_name: string;
  first_name: string;
  last_name: string;
  middle_name: string;
  aliases: string[];
  city: string;
  country: string;
  profession: string;
  competencies: string;
  description: string;
  notes: string;
  contacts: Contact[];
  tags: string[];
  organizations: { name: string; title: string }[];
  connections: Connection[];
};
export type Workspace = {
  id: string;
  name: string;
  kind: string;
  role: string;
};
export type Member = { user_id: string; name: string; role: string };
export type User = { id: string; name: string; email: string };
export type Suggestion = {
  id: string;
  operation: string;
  before: Partial<Person>;
  payload: Partial<Person>;
  confidence: number;
  status: string;
  source_id: string;
};
export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: unknown,
  ) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
}
export async function api<T>(
  path: string,
  method = "GET",
  body?: unknown,
  key?: string,
): Promise<T> {
  const csrf =
    document.cookie
      .split("; ")
      .find((c) => c.startsWith("crm_csrf="))
      ?.split("=")[1] || "";
  const response = await fetch("/api/v1" + path, {
    method,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
      ...(key ? { "Idempotency-Key": key } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok)
    throw new ApiError(
      response.status,
      data.detail || "Не удалось выполнить запрос",
    );
  return data;
}
export function emptyPerson(userId: string): Person {
  return {
    display_name: "",
    first_name: "",
    last_name: "",
    middle_name: "",
    aliases: [],
    city: "",
    country: "",
    profession: "",
    competencies: "",
    description: "",
    notes: "",
    contacts: [],
    tags: [],
    organizations: [],
    connections: [
      { user_id: userId, knows: true, priority: null, is_primary: true },
    ],
  };
}
export function payload(p: Person) {
  const { id, version, ...rest } = p;
  void id;
  void version;
  return Object.fromEntries(
    Object.entries(rest)
      .filter(([k]) => !["updated_at", "workspace_id"].includes(k))
      .map(([k, v]) => [
        k,
        k === "contacts"
          ? (v as Contact[]).map(({ normalized_value, ...c }) => {
              void normalized_value;
              return c;
            })
          : v,
      ]),
  );
}
export function errorMessage(e: unknown) {
  if (e instanceof ApiError && e.status === 409)
    return "Данные изменились или обнаружен дубль. Обновите карточку и проверьте изменения.";
  return e instanceof Error ? e.message : "Не удалось выполнить запрос";
}
