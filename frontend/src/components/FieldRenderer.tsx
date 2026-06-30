import type { SchemaField } from "../lib/types";

interface Props {
  field: SchemaField;
  value: unknown;
  onChange: (v: unknown) => void;
  onShape?: () => void;
  shaping?: boolean;
  highlight?: boolean;
}

const SHAPEABLE = new Set(["text", "rich_text"]);

export function FieldRenderer({ field, value, onChange, onShape, shaping, highlight }: Props) {
  const c = field.constraints || {};
  const wordCount =
    typeof value === "string" && value.trim() ? value.trim().split(/\s+/).length : 0;

  return (
    <div
      style={{
        padding: "16px 0",
        borderBottom: "1px solid var(--line)",
        scrollMarginTop: 80,
        background: highlight ? "rgba(156,55,42,0.04)" : undefined,
        borderRadius: highlight ? 6 : undefined,
        paddingLeft: highlight ? 12 : undefined,
        paddingRight: highlight ? 12 : undefined,
      }}
    >
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", gap: 12 }}>
        <label className="field-label">
          {field.label}
          {c.required && <span style={{ color: "var(--err)" }}> *</span>}
        </label>
        {SHAPEABLE.has(field.type) && onShape && (
          <button
            className="btn btn--ghost btn--sm"
            onClick={onShape}
            disabled={shaping || !(typeof value === "string" && value.trim())}
            title="Rewrite this into formal language with AI"
            style={{ flexShrink: 0 }}
          >
            {shaping ? <span className="spinner" /> : "✦ Shape with AI"}
          </button>
        )}
      </div>
      {field.guidance && <div className="field-guidance">{field.guidance}</div>}

      <FieldInput field={field} value={value} onChange={onChange} />

      {(c.max_words || c.max_chars) && typeof value === "string" && (
        <div
          className="mono"
          style={{
            fontSize: 11,
            marginTop: 6,
            textAlign: "right",
            color:
              c.max_words && wordCount > c.max_words ? "var(--err)" : "var(--ink-faint)",
          }}
        >
          {c.max_words ? `${wordCount}/${c.max_words} words` : `${(value as string).length}/${c.max_chars} chars`}
        </div>
      )}
    </div>
  );
}

function FieldInput({ field, value, onChange }: Pick<Props, "field" | "value" | "onChange">) {
  const c = field.constraints || {};
  const opts = c.options || [];

  switch (field.type) {
    case "text":
    case "date":
    case "quarter_year":
      return (
        <input
          className="input"
          type={field.type === "date" ? "date" : "text"}
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
        />
      );

    case "rich_text":
      return (
        <textarea
          className="textarea"
          rows={4}
          value={(value as string) ?? ""}
          onChange={(e) => onChange(e.target.value)}
        />
      );

    case "number":
    case "currency":
      return (
        <div style={{ position: "relative" }}>
          {field.type === "currency" && (
            <span
              className="mono"
              style={{ position: "absolute", left: 12, top: 10, color: "var(--ink-faint)" }}
            >
              $
            </span>
          )}
          <input
            className="input"
            type="number"
            style={{ paddingLeft: field.type === "currency" ? 26 : 12 }}
            value={value === undefined || value === null ? "" : (value as number)}
            onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
          />
        </div>
      );

    case "boolean":
      return (
        <div style={{ display: "inline-flex", border: "1px solid var(--line-strong)", borderRadius: 6, overflow: "hidden" }}>
          {[
            { v: true, l: "Yes" },
            { v: false, l: "No" },
          ].map((o) => (
            <button
              key={o.l}
              onClick={() => onChange(o.v)}
              style={{
                padding: "7px 18px",
                border: "none",
                cursor: "pointer",
                fontSize: 13.5,
                background: value === o.v ? "var(--navy)" : "#fff",
                color: value === o.v ? "#fff" : "var(--ink-soft)",
              }}
            >
              {o.l}
            </button>
          ))}
        </div>
      );

    case "single_select":
    case "rating_scale":
      return (
        <select className="select" value={(value as string) ?? ""} onChange={(e) => onChange(e.target.value || null)}>
          <option value="">— select —</option>
          {opts.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      );

    case "multi_select":
    case "checkbox_group": {
      const arr = (value as string[]) || [];
      if (opts.length === 0)
        return <span className="faint" style={{ fontSize: 13 }}>No options configured.</span>;
      return (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {opts.map((o) => {
            const on = arr.includes(o);
            return (
              <button
                key={o}
                onClick={() => onChange(on ? arr.filter((x) => x !== o) : [...arr, o])}
                className="chip"
                style={{
                  cursor: "pointer",
                  borderColor: on ? "var(--navy)" : "var(--line-strong)",
                  background: on ? "var(--navy)" : "var(--paper-2)",
                  color: on ? "#fff" : "var(--ink-soft)",
                }}
              >
                {on ? "✓ " : ""}
                {o}
              </button>
            );
          })}
        </div>
      );
    }

    case "sdg_target_list": {
      const arr = (value as string[]) || [];
      return (
        <div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: arr.length ? 8 : 0 }}>
            {arr.map((code) => (
              <span key={code} className="chip chip--fund" style={{ color: "var(--teal)" }}>
                SDG {code}
                <button
                  onClick={() => onChange(arr.filter((x) => x !== code))}
                  style={{ border: "none", background: "none", cursor: "pointer", color: "inherit", padding: 0 }}
                  aria-label={`Remove ${code}`}
                >
                  ×
                </button>
              </span>
            ))}
          </div>
          <input
            className="input"
            placeholder="Add target codes, e.g. 8.5, 8.6 (Enter)"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                const raw = (e.target as HTMLInputElement).value;
                const codes = raw.split(/[\s,]+/).map((s) => s.trim()).filter(Boolean);
                const next = Array.from(new Set([...arr, ...codes]));
                onChange(next);
                (e.target as HTMLInputElement).value = "";
              }
            }}
          />
        </div>
      );
    }

    default:
      return (
        <div
          className="faint"
          style={{ fontSize: 13, fontStyle: "italic", padding: "8px 0" }}
        >
          ({field.type.replace(/_/g, " ")} — structured editing coming soon)
        </div>
      );
  }
}
