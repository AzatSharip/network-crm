import { useRef, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import {
  X,
  Plus,
  Trash2,
  UserRound,
  Phone,
  BriefcaseBusiness,
  Users,
} from "lucide-react";
import {
  api,
  ApiError,
  payload,
  errorMessage,
  type Person,
  type Member,
} from "./api";
import { Button } from "./components/ui/button";
const platforms = [
  ["phone", "Телефон", "phone"],
  ["email", "Email", "email"],
  ["telegram", "Telegram", "username"],
  ["whatsapp", "WhatsApp", "phone"],
  ["signal", "Signal", "phone"],
  ["viber", "Viber", "phone"],
  ["vk", "ВКонтакте", "url"],
  ["ok", "Одноклассники", "url"],
  ["linkedin", "LinkedIn", "url"],
  ["facebook", "Facebook", "url"],
  ["instagram", "Instagram", "username"],
  ["discord", "Discord", "username"],
  ["github", "GitHub", "username"],
  ["website", "Сайт", "url"],
  ["other", "Другой", "other"],
];
export function PersonEditor({
  initial,
  base,
  members,
  userId,
  onClose,
  onSaved,
  onOpen,
}: {
  initial: Person;
  base: string;
  members: Member[];
  userId: string;
  onClose: () => void;
  onSaved: (p: Person) => void;
  onOpen: (id: string) => void;
}) {
  const [p, setP] = useState<Person>(structuredClone(initial));
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [duplicates, setDuplicates] = useState<
    { id: string; display_name: string }[]
  >([]);
  const key = useRef(crypto.randomUUID());
  const field = (name: keyof Person, value: unknown) =>
    setP((old) => ({ ...old, [name]: value }));
  async function save(allow = false) {
    setBusy(true);
    setError("");
    try {
      const body = {
        ...payload(p),
        ...(p.id ? { expected_version: p.version } : {}),
      };
      const saved = await api<Person>(
        base +
          "/people" +
          (p.id ? "/" + p.id : "") +
          (allow ? "?allow_duplicate=true" : ""),
        p.id ? "PATCH" : "POST",
        body,
        key.current,
      );
      onSaved(saved);
    } catch (e) {
      if (
        e instanceof ApiError &&
        typeof e.detail === "object" &&
        e.detail !== null &&
        "code" in e.detail &&
        (e.detail as { code: string }).code === "duplicates"
      ) {
        setDuplicates(
          (
            e.detail as {
              code: string;
              matches: { id: string; display_name: string }[];
            }
          ).matches,
        );
      } else {
        setError(errorMessage(e));
      }
    } finally {
      setBusy(false);
    }
  }
  return (
    <Dialog.Root
      open
      onOpenChange={(open) => {
        if (!open && !busy) onClose();
      }}
    >
      <Dialog.Portal>
        <Dialog.Overlay className="overlay" />
        <Dialog.Content className="editor">
          <div className="editor-header">
            <div>
              <span className="eyebrow">КАРТОЧКА ЧЕЛОВЕКА</span>
              <Dialog.Title>
                {p.id ? "Редактировать контакт" : "Новый контакт"}
              </Dialog.Title>
              <Dialog.Description>
                Достаточно имени. Остальное можно добавить позже.
              </Dialog.Description>
            </div>
            <Dialog.Close asChild>
              <Button variant="ghost" aria-label="Закрыть" disabled={busy}>
                <X size={20} />
              </Button>
            </Dialog.Close>
          </div>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void save();
            }}
          >
            <div className="editor-body">
              <section>
                <h3>
                  <UserRound size={18} />
                  Основное
                </h3>
                <label>
                  Имя / ФИО <span className="required">*</span>
                  <input
                    autoFocus
                    required
                    maxLength={200}
                    value={p.display_name}
                    onChange={(e) => field("display_name", e.target.value)}
                    placeholder="Как зовут человека"
                  />
                </label>
                <div className="form-grid">
                  <label>
                    Город
                    <input
                      value={p.city}
                      onChange={(e) => field("city", e.target.value)}
                      placeholder="Например, Уфа"
                    />
                  </label>
                  <label>
                    Страна
                    <input
                      value={p.country}
                      onChange={(e) => field("country", e.target.value)}
                    />
                  </label>
                </div>
                <label>
                  Профессия
                  <input
                    value={p.profession}
                    onChange={(e) => field("profession", e.target.value)}
                    placeholder="Чем занимается"
                  />
                </label>
                <label>
                  Компетенции
                  <input
                    value={p.competencies}
                    onChange={(e) => field("competencies", e.target.value)}
                    placeholder="В чём разбирается"
                  />
                </label>
                <label>
                  Теги, через запятую
                  <input
                    value={p.tags.join(", ")}
                    onChange={(e) =>
                      field(
                        "tags",
                        e.target.value.split(",").map((v) => v.trim()),
                      )
                    }
                    onBlur={() => field("tags", p.tags.filter(Boolean))}
                    placeholder="Медицина, IT, Инвестиции"
                  />
                </label>
                <details>
                  <summary>Дополнительные имена и описание</summary>
                  <div className="form-grid">
                    {(["last_name", "first_name", "middle_name"] as const).map(
                      (name, i) => (
                        <label key={name}>
                          {["Фамилия", "Имя", "Отчество"][i]}
                          <input
                            value={p[name]}
                            onChange={(e) => field(name, e.target.value)}
                          />
                        </label>
                      ),
                    )}
                  </div>
                  <label>
                    Другие имена, через запятую
                    <input
                      value={p.aliases.join(", ")}
                      onChange={(e) =>
                        field(
                          "aliases",
                          e.target.value.split(",").map((v) => v.trim()),
                        )
                      }
                      onBlur={() => field("aliases", p.aliases.filter(Boolean))}
                    />
                  </label>
                  <label>
                    Краткое описание
                    <textarea
                      value={p.description}
                      onChange={(e) => field("description", e.target.value)}
                    />
                  </label>
                </details>
              </section>
              <section>
                <h3>
                  <Phone size={18} />
                  Контактные данные
                </h3>
                {p.contacts.map((c, i) => (
                  <div className="contact-row" key={i}>
                    <div className="form-grid">
                      <label>
                        Платформа
                        <select
                          aria-label={`Платформа ${i + 1}`}
                          value={
                            platforms.some((x) => x[0] === c.platform)
                              ? c.platform
                              : "other"
                          }
                          onChange={(e) => {
                            const option = platforms.find(
                              (x) => x[0] === e.target.value,
                            )!;
                            field(
                              "contacts",
                              p.contacts.map((v, j) =>
                                j === i
                                  ? {
                                      ...v,
                                      platform: option[0],
                                      kind: option[2],
                                    }
                                  : v,
                              ),
                            );
                          }}
                        >
                          {platforms.map((x) => (
                            <option key={x[0]} value={x[0]}>
                              {x[1]}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Вид идентификатора
                        <select
                          aria-label={`Вид идентификатора ${i + 1}`}
                          value={c.kind}
                          onChange={(e) =>
                            field(
                              "contacts",
                              p.contacts.map((v, j) =>
                                j === i ? { ...v, kind: e.target.value } : v,
                              ),
                            )
                          }
                        >
                          {[
                            ["phone", "Номер телефона"],
                            ["email", "Email"],
                            ["username", "Username"],
                            ["numeric_id", "Числовой ID"],
                            ["url", "Ссылка"],
                            ["other", "Другое"],
                          ].map((x) => (
                            <option key={x[0]} value={x[0]}>
                              {x[1]}
                            </option>
                          ))}
                        </select>
                      </label>
                    </div>
                    {(c.platform === "other" ||
                      !platforms.some((x) => x[0] === c.platform)) && (
                      <label>
                        Название платформы (латиницей)
                        <input
                          value={c.platform}
                          onChange={(e) =>
                            field(
                              "contacts",
                              p.contacts.map((v, j) =>
                                j === i
                                  ? { ...v, platform: e.target.value }
                                  : v,
                              ),
                            )
                          }
                        />
                      </label>
                    )}
                    <div className="inline">
                      <label className="grow">
                        Значение
                        <input
                          required
                          aria-label={`Значение ${i + 1}`}
                          value={c.value}
                          onChange={(e) =>
                            field(
                              "contacts",
                              p.contacts.map((v, j) =>
                                j === i ? { ...v, value: e.target.value } : v,
                              ),
                            )
                          }
                        />
                      </label>
                      <Button
                        type="button"
                        variant="ghost"
                        aria-label={`Удалить способ связи ${i + 1}`}
                        onClick={() =>
                          field(
                            "contacts",
                            p.contacts.filter((_, j) => j !== i),
                          )
                        }
                      >
                        <Trash2 size={17} />
                      </Button>
                    </div>
                    <div className="form-grid">
                      <label>
                        Подпись
                        <input
                          placeholder="Рабочий, личный…"
                          value={c.label}
                          onChange={(e) =>
                            field(
                              "contacts",
                              p.contacts.map((v, j) =>
                                j === i ? { ...v, label: e.target.value } : v,
                              ),
                            )
                          }
                        />
                      </label>
                      <label>
                        Источник
                        <input
                          value={c.source}
                          onChange={(e) =>
                            field(
                              "contacts",
                              p.contacts.map((v, j) =>
                                j === i ? { ...v, source: e.target.value } : v,
                              ),
                            )
                          }
                        />
                      </label>
                    </div>
                    <div className="inline">
                      <label className="check">
                        <input
                          type="checkbox"
                          checked={c.is_primary}
                          onChange={(e) =>
                            field(
                              "contacts",
                              p.contacts.map((v, j) =>
                                j === i
                                  ? { ...v, is_primary: e.target.checked }
                                  : v,
                              ),
                            )
                          }
                        />
                        Основной
                      </label>
                      <label className="check">
                        <input
                          type="checkbox"
                          checked={c.verification === "verified"}
                          onChange={(e) =>
                            field(
                              "contacts",
                              p.contacts.map((v, j) =>
                                j === i
                                  ? {
                                      ...v,
                                      verification: e.target.checked
                                        ? "verified"
                                        : "unverified",
                                    }
                                  : v,
                              ),
                            )
                          }
                        />
                        Проверен
                      </label>
                    </div>
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  onClick={() =>
                    field("contacts", [
                      ...p.contacts,
                      {
                        platform: "phone",
                        kind: "phone",
                        value: "",
                        label: "",
                        source: "",
                        is_primary: false,
                        verification: "unverified",
                      },
                    ])
                  }
                >
                  <Plus size={16} />
                  Добавить способ связи
                </Button>
              </section>
              <section>
                <h3>
                  <BriefcaseBusiness size={18} />
                  Работа и организации
                </h3>
                {p.organizations.map((o, i) => (
                  <div key={i} className="inline">
                    <label>
                      Компания
                      <input
                        required
                        value={o.name}
                        onChange={(e) =>
                          field(
                            "organizations",
                            p.organizations.map((v, j) =>
                              j === i ? { ...v, name: e.target.value } : v,
                            ),
                          )
                        }
                      />
                    </label>
                    <label>
                      Должность
                      <input
                        value={o.title}
                        onChange={(e) =>
                          field(
                            "organizations",
                            p.organizations.map((v, j) =>
                              j === i ? { ...v, title: e.target.value } : v,
                            ),
                          )
                        }
                      />
                    </label>
                    <Button
                      variant="ghost"
                      type="button"
                      aria-label="Удалить организацию"
                      onClick={() =>
                        field(
                          "organizations",
                          p.organizations.filter((_, j) => j !== i),
                        )
                      }
                    >
                      <X size={16} />
                    </Button>
                  </div>
                ))}
                <Button
                  variant="outline"
                  type="button"
                  onClick={() =>
                    field("organizations", [
                      ...p.organizations,
                      { name: "", title: "" },
                    ])
                  }
                >
                  <Plus size={16} />
                  Добавить организацию
                </Button>
              </section>
              <section>
                <h3>
                  <Users size={18} />
                  Кто знаком
                </h3>
                {members.map((m) => {
                  const connection = p.connections.find(
                    (c) => c.user_id === m.user_id,
                  );
                  return (
                    <div key={m.user_id} className="member-row">
                      <label className="check">
                        <input
                          type="checkbox"
                          checked={connection?.knows || false}
                          onChange={(e) =>
                            field(
                              "connections",
                              connection
                                ? p.connections.map((c) =>
                                    c.user_id === m.user_id
                                      ? {
                                          ...c,
                                          knows: e.target.checked,
                                          is_primary:
                                            e.target.checked && c.is_primary,
                                        }
                                      : c,
                                  )
                                : [
                                    ...p.connections,
                                    {
                                      user_id: m.user_id,
                                      knows: e.target.checked,
                                      priority: null,
                                      is_primary: false,
                                    },
                                  ],
                            )
                          }
                        />
                        {m.name}
                      </label>
                      {connection?.knows && (
                        <label className="check">
                          <input
                            type="radio"
                            name="primary"
                            checked={connection.is_primary}
                            onChange={() =>
                              field(
                                "connections",
                                p.connections.map((c) => ({
                                  ...c,
                                  is_primary: c.user_id === m.user_id,
                                })),
                              )
                            }
                          />
                          Основной знакомый
                        </label>
                      )}
                    </div>
                  );
                })}
                <label>
                  Мой приоритет
                  <select
                    value={
                      p.connections.find((c) => c.user_id === userId)
                        ?.priority || ""
                    }
                    onChange={(e) => {
                      const mine = p.connections.find(
                        (c) => c.user_id === userId,
                      );
                      const updated = {
                        ...(mine || {
                          user_id: userId,
                          knows: false,
                          is_primary: false,
                        }),
                        priority: (e.target.value || null) as
                          "A" | "B" | "C" | null,
                      };
                      field("connections", [
                        ...p.connections.filter((c) => c.user_id !== userId),
                        updated,
                      ]);
                    }}
                  >
                    <option value="">Не определён</option>
                    <option value="A">A — ключевой контакт</option>
                    <option value="B">B — ценный контакт</option>
                    <option value="C">C — обычный контакт</option>
                  </select>
                </label>
              </section>
              <section>
                <h3>Заметки</h3>
                <textarea
                  rows={5}
                  value={p.notes}
                  onChange={(e) => field("notes", e.target.value)}
                  placeholder="Где познакомились, о чём говорили, что важно помнить…"
                />
              </section>
              {duplicates.length > 0 && (
                <div className="notice">
                  <strong>Возможно, вы уже знакомы</strong>
                  <p>
                    Совпали контактные идентификаторы. Выберите существующую
                    карточку для просмотра или дополнения.
                  </p>
                  {duplicates.map((d) => (
                    <Button
                      key={d.id}
                      type="button"
                      variant="outline"
                      onClick={() => onOpen(d.id)}
                    >
                      {d.display_name}
                    </Button>
                  ))}
                  <Button
                    type="button"
                    variant="outline"
                    disabled={busy}
                    onClick={() => void save(true)}
                  >
                    {p.id
                      ? "Сохранить раздельные карточки"
                      : "Всё равно создать отдельный контакт"}
                  </Button>
                </div>
              )}
              {error && (
                <div role="alert" className="error">
                  {error}
                </div>
              )}
            </div>
            <footer className="editor-footer">
              <Button
                type="button"
                variant="outline"
                onClick={onClose}
                disabled={busy}
              >
                Отмена
              </Button>
              <Button type="submit" disabled={busy}>
                {busy
                  ? "Сохраняем…"
                  : p.id
                    ? "Сохранить изменения"
                    : "Добавить контакт"}
              </Button>
            </footer>
          </form>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
