import { useEffect, useRef, useState } from "react";
import type cytoscape from "cytoscape";
import { Search, Network, ZoomIn, ZoomOut, Maximize } from "lucide-react";
import { api, errorMessage, type Person, type Member } from "./api";
import { Button } from "./components/ui/button";
type Edge = {
  id: string;
  from_person_id: string;
  to_person_id: string;
  type: string;
  directed: boolean;
};
export function PersonPicker({
  base,
  value,
  onChange,
  label,
}: {
  base: string;
  value: string;
  onChange: (id: string) => void;
  label: string;
}) {
  const [q, setQ] = useState("");
  const [options, setOptions] = useState<Person[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    const timer = setTimeout(() => {
      api<{ items: Person[] }>(
        base + "/people?q=" + encodeURIComponent(q) + "&size=30",
      )
        .then((r) => {
          if (active) {
            setOptions(r.items);
            setError("");
          }
        })
        .catch((e) => {
          if (active) setError(errorMessage(e));
        });
    }, 250);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [base, q]);
  return (
    <div className="picker">
      <label>
        {label}
        <div className="search-small">
          <Search size={16} />
          <input
            aria-label={`Поиск: ${label}`}
            placeholder="Найти по имени…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>
        <select
          aria-label={label}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="">Выберите человека</option>
          {options.map((p) => (
            <option key={p.id} value={p.id}>
              {p.display_name}
            </option>
          ))}
        </select>
      </label>
      {error && (
        <span role="alert" className="error">
          {error}
        </span>
      )}
    </div>
  );
}
export function Graph({
  base,
  members,
  onOpen,
  initialRoot = "",
}: {
  base: string;
  members: Member[];
  onOpen: (id: string) => void;
  initialRoot?: string;
}) {
  const [root, setRoot] = useState(initialRoot);
  const [target, setTarget] = useState("");
  const [depth, setDepth] = useState(1);
  const [error, setError] = useState("");
  const [info, setInfo] = useState("");
  const [busy, setBusy] = useState(false);
  const [graphPeople, setGraphPeople] = useState<Person[]>([]);
  const mount = useRef<HTMLDivElement>(null);
  const cy = useRef<cytoscape.Core | null>(null);
  useEffect(
    () => () => {
      cy.current?.destroy();
    },
    [],
  );
  async function load() {
    if (!root) return;
    setBusy(true);
    setError("");
    try {
      const result = await api<{
        nodes: Person[];
        edges: Edge[];
        path: string[];
        truncated: boolean;
      }>(
        base +
          `/graph?root=${root}&depth=${depth}` +
          (target ? "&target=" + target : ""),
      );
      const { default: cytoscape } = await import("cytoscape");
      cy.current?.destroy();
      const path = new Set(result.path);
      cy.current = cytoscape({
        container: mount.current,
        elements: [
          ...result.nodes.map((p) => ({
            data: {
              id: p.id,
              label: p.display_name,
              known: p.connections
                .filter((c) => c.knows)
                .map((c) => members.find((m) => m.user_id === c.user_id)?.name)
                .filter(Boolean)
                .join(", "),
            },
            classes: path.has(p.id!) ? "path" : "",
          })),
          ...result.edges.map((e) => ({
            data: {
              id: e.id,
              source: e.from_person_id,
              target: e.to_person_id,
              label: e.type,
            },
            classes: e.directed ? "directed" : "",
          })),
        ],
        style: [
          {
            selector: "node",
            style: {
              "background-color": "#e9e5df",
              "border-color": "#81776d",
              "border-width": 2,
              width: 40,
              height: 40,
              label: "data(label)",
              "font-family": "system-ui",
              "font-size": 11,
              "text-wrap": "wrap",
              "text-max-width": "115px",
              "text-valign": "bottom",
              "text-margin-y": 10,
              color: "#282827",
            },
          },
          {
            selector: "node.path",
            style: {
              "background-color": "#e8b294",
              "border-color": "#9c5236",
              "border-width": 4,
            },
          },
          {
            selector: "edge",
            style: {
              width: 2,
              "line-color": "#c6c0b9",
              "curve-style": "bezier",
              label: "data(label)",
              "font-size": 10,
              "text-background-color": "#fff",
              "text-background-opacity": 0.9,
              "text-background-padding": "3px",
            },
          },
          {
            selector: "edge.directed",
            style: {
              "target-arrow-shape": "triangle",
              "target-arrow-color": "#81776d",
            },
          },
        ],
        layout: {
          name: "cose",
          animate: false,
          nodeDimensionsIncludeLabels: true,
          nodeRepulsion: () => 120000,
          idealEdgeLength: () => 120,
          padding: 50,
        },
        minZoom: 0.01,
        maxZoom: 3,
      });
      if (cy.current.zoom() > 1) {
        cy.current.zoom(1);
        cy.current.center();
      }
      cy.current.on("tap", "node", (e) => onOpen(e.target.id()));
      setGraphPeople(result.nodes);
      setInfo(
        result.truncated
          ? "Достигнут лимит графа. Показана часть связей."
          : target
            ? result.path.length
              ? `Путь знакомства: ${result.path.length - 1} связей`
              : "Путь не найден в пределах 6 уровней и 80 узлов"
            : `${result.nodes.length} людей · нажмите на узел, чтобы открыть карточку`,
      );
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <div className="page-title">
        <div>
          <span className="eyebrow">ВАШ КРУГ ЗНАКОМСТВ</span>
          <h1>Связи между людьми</h1>
          <p>Найдите общих знакомых и путь к нужному человеку.</p>
        </div>
      </div>
      <div className="graph-controls panel">
        <PersonPicker
          base={base}
          label="От кого"
          value={root}
          onChange={setRoot}
        />
        <PersonPicker
          base={base}
          label="К кому (для поиска пути)"
          value={target}
          onChange={setTarget}
        />
        <label>
          Глубина
          <select
            value={depth}
            onChange={(e) => setDepth(Number(e.target.value))}
          >
            <option value={1}>Ближайшие связи</option>
            <option value={2}>Два уровня</option>
          </select>
        </label>
        <Button onClick={() => void load()} disabled={!root || busy}>
          <Network size={17} />
          {busy ? "Загрузка…" : "Показать связи"}
        </Button>
      </div>
      {error && (
        <div role="alert" className="error">
          {error}
        </div>
      )}
      <div className="graph-frame">
        <div className="graph-toolbar" aria-label="Масштаб графа">
          <span className="muted">Карта знакомств</span>
          <div className="inline">
            <Button
              variant="ghost"
              aria-label="Уменьшить граф"
              disabled={!graphPeople.length || busy}
              onClick={() => {
                if (cy.current) {
                  cy.current.zoom(Math.max(0.01, cy.current.zoom() / 1.25));
                  cy.current.center();
                }
              }}
            >
              <ZoomOut size={17} />
            </Button>
            <Button
              variant="ghost"
              aria-label="Увеличить граф"
              disabled={!graphPeople.length || busy}
              onClick={() => {
                if (cy.current) {
                  cy.current.zoom(Math.min(3, cy.current.zoom() * 1.25));
                  cy.current.center();
                }
              }}
            >
              <ZoomIn size={17} />
            </Button>
            <Button
              variant="ghost"
              aria-label="Показать весь граф"
              disabled={!graphPeople.length || busy}
              onClick={() => {
                cy.current?.resize().fit(undefined, 50);
              }}
            >
              <Maximize size={17} />
            </Button>
          </div>
        </div>
        <div className="graph-canvas" ref={mount} />
      </div>
      {graphPeople.length > 0 && (
        <details className="graph-people">
          <summary>Люди на графе · {graphPeople.length}</summary>
          <div className="tags">
            {graphPeople.map((person) => (
              <Button
                key={person.id}
                variant="outline"
                onClick={() => onOpen(person.id!)}
              >
                {person.display_name}
              </Button>
            ))}
          </div>
        </details>
      )}
      <p className="muted">
        {info || "Выберите человека и нажмите «Показать связи»."}
      </p>
    </>
  );
}
