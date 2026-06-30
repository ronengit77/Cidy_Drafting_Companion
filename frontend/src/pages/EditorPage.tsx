import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { useToast } from "../lib/toast";
import { AppHeader, FullLoader, fundColor } from "../components/ui";
import { FieldRenderer } from "../components/FieldRenderer";
import type {
  ArtifactDetail,
  ArtifactValues,
  SchemaSection,
  SDGSuggestion,
  TemplateSchema,
  ValidationReport,
} from "../lib/types";

type RightTab = "validate" | "coherence" | "sdg" | "preview";

export function EditorPage() {
  const { id = "" } = useParams();
  const toast = useToast();

  const [artifact, setArtifact] = useState<ArtifactDetail | null>(null);
  const [schema, setSchema] = useState<TemplateSchema | null>(null);
  const [content, setContent] = useState<ArtifactValues>({});
  const [title, setTitle] = useState("");
  const [versionNo, setVersionNo] = useState(1);
  const [active, setActive] = useState<string>("");
  const [dirty, setDirty] = useState(false);
  const [saving, setSaving] = useState(false);

  const [tab, setTab] = useState<RightTab>("validate");
  const [validation, setValidation] = useState<ValidationReport | null>(null);
  const [coherence, setCoherence] = useState<string | null>(null);
  const [sdg, setSdg] = useState<SDGSuggestion[] | null>(null);
  const [busyPanel, setBusyPanel] = useState(false);
  const [shapingKey, setShapingKey] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const a = await api.getArtifact(id);
        const s = await api.getSchema(a.schema_id);
        setArtifact(a);
        setSchema(s);
        setContent(a.content || {});
        setTitle(a.title);
        setVersionNo(a.version_no);
        setActive(s.sections[0]?.id ?? "");
      } catch (e) {
        toast((e as ApiError).message, "err");
      }
    })();
  }, [id, toast]);

  const setField = useCallback(
    (sectionId: string, fieldId: string, val: unknown, itemIdx?: number) => {
      setContent((prev) => {
        const next: ArtifactValues = JSON.parse(JSON.stringify(prev));
        if (itemIdx === undefined) {
          next[sectionId] = { ...((next[sectionId] as object) || {}), [fieldId]: val };
        } else {
          const arr = Array.isArray(next[sectionId]) ? [...(next[sectionId] as unknown[])] : [];
          arr[itemIdx] = { ...((arr[itemIdx] as object) || {}), [fieldId]: val };
          next[sectionId] = arr;
        }
        return next;
      });
      setDirty(true);
    },
    [],
  );

  const save = useCallback(async (): Promise<boolean> => {
    setSaving(true);
    try {
      const a = await api.updateArtifact(id, versionNo, title, content);
      setVersionNo(a.version_no);
      setArtifact(a);
      setDirty(false);
      return true;
    } catch (e) {
      const err = e as ApiError;
      if (err.status === 409) {
        toast("This draft changed elsewhere — reloading the latest version.", "err");
        const a = await api.getArtifact(id);
        setArtifact(a);
        setContent(a.content || {});
        setTitle(a.title);
        setVersionNo(a.version_no);
        setDirty(false);
      } else {
        toast(err.message, "err");
      }
      return false;
    } finally {
      setSaving(false);
    }
  }, [id, versionNo, title, content, toast]);

  const ensureSaved = useCallback(async () => (dirty ? save() : true), [dirty, save]);

  async function runPanel(which: RightTab) {
    setTab(which);
    if (which === "preview") return;
    if (!(await ensureSaved())) return;
    setBusyPanel(true);
    try {
      if (which === "validate") setValidation(await api.checkArtifact(id));
      if (which === "coherence") setCoherence((await api.coherence(id)).assessment);
      if (which === "sdg") setSdg((await api.suggestSdg(id)).suggestions);
    } catch (e) {
      toast((e as ApiError).message, "err");
    } finally {
      setBusyPanel(false);
    }
  }

  async function shapeField(sectionId: string, fieldId: string, itemIdx?: number) {
    const cur = readField(content, sectionId, fieldId, itemIdx);
    if (typeof cur !== "string" || !cur.trim()) return;
    const key = `${sectionId}.${fieldId}.${itemIdx ?? ""}`;
    setShapingKey(key);
    try {
      const r = await api.shapeField(id, sectionId, fieldId, cur);
      setField(sectionId, fieldId, r.shaped_text, itemIdx);
      toast("Field rewritten", "ok");
    } catch (e) {
      toast((e as ApiError).message, "err");
    } finally {
      setShapingKey(null);
    }
  }

  function applySdg(codes: string[]) {
    if (!schema) return;
    for (const s of schema.sections) {
      const f = s.fields.find((x) => x.type === "sdg_target_list");
      if (f && !s.repeating) {
        const existing = (readField(content, s.id, f.id) as string[]) || [];
        setField(s.id, f.id, Array.from(new Set([...existing, ...codes])));
        setActive(s.id);
        toast(`Added ${codes.length} target(s) to "${f.label}"`, "ok");
        return;
      }
    }
    toast("No SDG target field in this template.", "err");
  }

  const missingBySection = useMemo(() => {
    const map: Record<string, number> = {};
    for (const p of validation?.missing ?? []) {
      const sec = p.split(/[.[]/)[0];
      map[sec] = (map[sec] || 0) + 1;
    }
    return map;
  }, [validation]);

  if (!artifact || !schema) return <FullLoader label="Opening draft" />;
  const section = schema.sections.find((s) => s.id === active) ?? schema.sections[0];
  const fund = schema.fund;
  const missingHere = new Set(
    (validation?.missing ?? [])
      .filter((p) => p.startsWith(`${section.id}.`) || p.startsWith(`${section.id}[`))
      .map((p) => p.split(".").pop()),
  );

  return (
    <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column" }}>
      <AppHeader />

      {/* sub-bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 16,
          padding: "12px 28px",
          borderBottom: "1px solid var(--line)",
          background: "var(--paper)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12, minWidth: 0 }}>
          <span className="chip chip--fund" style={{ color: fundColor(fund) }}>
            {fund}
          </span>
          <input
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              setDirty(true);
            }}
            placeholder="Untitled draft"
            style={{
              border: "none",
              background: "transparent",
              fontFamily: "var(--font-serif)",
              fontSize: 19,
              fontWeight: 500,
              width: "min(46vw, 520px)",
              outline: "none",
            }}
          />
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span className="mono faint" style={{ fontSize: 11.5 }}>
            v{versionNo} {dirty ? "· unsaved" : "· saved"}
          </span>
          <button className="btn" onClick={save} disabled={saving || !dirty}>
            {saving ? <span className="spinner" /> : "Save"}
          </button>
        </div>
      </div>

      {/* body */}
      <div style={{ display: "grid", gridTemplateColumns: "232px minmax(0,1fr) 360px", flex: 1, minHeight: 0 }}>
        {/* nav */}
        <nav style={{ borderRight: "1px solid var(--line)", padding: "18px 12px", overflowY: "auto" }}>
          <p className="eyebrow" style={{ padding: "0 10px 10px" }}>
            Sections
          </p>
          {schema.sections.map((s) => {
            const miss = missingBySection[s.id];
            return (
              <button
                key={s.id}
                onClick={() => setActive(s.id)}
                style={{
                  display: "flex",
                  width: "100%",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 8,
                  textAlign: "left",
                  padding: "9px 10px",
                  border: "none",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontSize: 13.5,
                  marginBottom: 2,
                  background: s.id === active ? "var(--paper-3)" : "transparent",
                  color: s.id === active ? "var(--ink)" : "var(--ink-soft)",
                  fontWeight: s.id === active ? 600 : 400,
                }}
              >
                <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  {s.title}
                </span>
                {miss ? <span className="dot dot--err" title={`${miss} required missing`} /> : null}
              </button>
            );
          })}
        </nav>

        {/* form */}
        <section style={{ overflowY: "auto", padding: "26px 34px 80px" }}>
          <div className="rise" key={section.id}>
            <h2 style={{ fontSize: 23 }}>{section.title}</h2>
            {section.guidance && (
              <p className="muted" style={{ marginTop: 6, fontSize: 13.5, maxWidth: 640 }}>
                {section.guidance}
              </p>
            )}
            <div style={{ marginTop: 14, maxWidth: 720 }}>
              {section.repeating ? (
                <RepeatingSection
                  section={section}
                  items={(content[section.id] as ArtifactValues[]) || []}
                  setField={(fid, v, idx) => setField(section.id, fid, v, idx)}
                  onAdd={() => {
                    setContent((prev) => {
                      const next: ArtifactValues = JSON.parse(JSON.stringify(prev));
                      const arr = Array.isArray(next[section.id]) ? [...(next[section.id] as unknown[])] : [];
                      arr.push({});
                      next[section.id] = arr;
                      return next;
                    });
                    setDirty(true);
                  }}
                  onRemove={(idx) => {
                    setContent((prev) => {
                      const next: ArtifactValues = JSON.parse(JSON.stringify(prev));
                      const arr = ((next[section.id] as unknown[]) || []).filter((_, i) => i !== idx);
                      next[section.id] = arr;
                      return next;
                    });
                    setDirty(true);
                  }}
                  shapingKey={shapingKey}
                  onShape={(fid, idx) => shapeField(section.id, fid, idx)}
                />
              ) : (
                section.fields.map((f) => (
                  <FieldRenderer
                    key={f.id}
                    field={f}
                    value={readField(content, section.id, f.id)}
                    onChange={(v) => setField(section.id, f.id, v)}
                    onShape={() => shapeField(section.id, f.id)}
                    shaping={shapingKey === `${section.id}.${f.id}.`}
                    highlight={missingHere.has(f.id)}
                  />
                ))
              )}
            </div>
          </div>
        </section>

        {/* right panel */}
        <aside style={{ borderLeft: "1px solid var(--line)", display: "flex", flexDirection: "column", background: "var(--paper)" }}>
          <div style={{ display: "flex", borderBottom: "1px solid var(--line)" }}>
            {([
              ["validate", "Check"],
              ["coherence", "Coherence"],
              ["sdg", "SDGs"],
              ["preview", "Preview"],
            ] as [RightTab, string][]).map(([k, label]) => (
              <button
                key={k}
                onClick={() => runPanel(k)}
                style={{
                  flex: 1,
                  padding: "11px 4px",
                  border: "none",
                  borderBottom: tab === k ? "2px solid var(--brass)" : "2px solid transparent",
                  background: "transparent",
                  cursor: "pointer",
                  fontSize: 12.5,
                  fontWeight: tab === k ? 600 : 400,
                  color: tab === k ? "var(--ink)" : "var(--ink-soft)",
                }}
              >
                {label}
              </button>
            ))}
          </div>
          <div style={{ overflowY: "auto", padding: 18, flex: 1 }}>
            {busyPanel ? (
              <div style={{ display: "grid", placeItems: "center", paddingTop: 40, gap: 12 }}>
                <span className="spinner" style={{ color: "var(--brass)", width: 20, height: 20 }} />
                <span className="eyebrow">Working…</span>
              </div>
            ) : tab === "validate" ? (
              <ValidatePanel report={validation} onRun={() => runPanel("validate")} />
            ) : tab === "coherence" ? (
              <CoherencePanel text={coherence} onRun={() => runPanel("coherence")} />
            ) : tab === "sdg" ? (
              <SdgPanel suggestions={sdg} onRun={() => runPanel("sdg")} onApply={applySdg} />
            ) : (
              <PreviewPanel schema={schema} content={content} />
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

function readField(content: ArtifactValues, sectionId: string, fieldId: string, itemIdx?: number): unknown {
  const sec = content[sectionId];
  if (itemIdx !== undefined) {
    const item = Array.isArray(sec) ? (sec[itemIdx] as ArtifactValues) : undefined;
    return item?.[fieldId];
  }
  return sec && typeof sec === "object" && !Array.isArray(sec) ? (sec as ArtifactValues)[fieldId] : undefined;
}

function RepeatingSection({
  section,
  items,
  setField,
  onAdd,
  onRemove,
  shapingKey,
  onShape,
}: {
  section: SchemaSection;
  items: ArtifactValues[];
  setField: (fieldId: string, v: unknown, idx: number) => void;
  onAdd: () => void;
  onRemove: (idx: number) => void;
  shapingKey: string | null;
  onShape: (fieldId: string, idx: number) => void;
}) {
  return (
    <div>
      {items.map((item, idx) => (
        <div key={idx} className="card" style={{ padding: "8px 18px 16px", marginBottom: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: 10 }}>
            <span className="eyebrow">
              {section.title} · {idx + 1}
            </span>
            <button className="btn btn--ghost btn--sm" onClick={() => onRemove(idx)}>
              Remove
            </button>
          </div>
          {section.fields.map((f) => (
            <FieldRenderer
              key={f.id}
              field={f}
              value={item?.[f.id]}
              onChange={(v) => setField(f.id, v, idx)}
              onShape={() => onShape(f.id, idx)}
              shaping={shapingKey === `${section.id}.${f.id}.${idx}`}
            />
          ))}
        </div>
      ))}
      <button className="btn btn--ghost" onClick={onAdd}>
        + Add {section.title.toLowerCase()}
      </button>
    </div>
  );
}

function ValidatePanel({ report, onRun }: { report: ValidationReport | null; onRun: () => void }) {
  if (!report)
    return <RunPrompt label="Check completeness and constraints across the whole draft." onRun={onRun} cta="Run check" />;
  const pct = report.required_total ? Math.round((report.required_filled / report.required_total) * 100) : 100;
  return (
    <div className="rise">
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
        <span className={`dot ${report.is_valid ? "dot--ok" : "dot--err"}`} />
        <strong>{report.is_valid ? "No blocking issues" : `${report.issues.filter((i) => i.severity === "error").length} issue(s)`}</strong>
      </div>
      <div className="mono faint" style={{ fontSize: 11.5, marginBottom: 14 }}>
        {report.required_filled}/{report.required_total} required fields · {pct}%
      </div>
      <div style={{ height: 6, background: "var(--paper-3)", borderRadius: 99, overflow: "hidden", marginBottom: 18 }}>
        <div style={{ width: `${pct}%`, height: "100%", background: pct === 100 ? "var(--ok)" : "var(--brass)" }} />
      </div>
      {report.issues.length === 0 ? (
        <p className="muted" style={{ fontSize: 13 }}>Everything required is filled in. Nice work.</p>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {report.issues.map((iss, i) => (
            <div key={i} className="card" style={{ padding: "9px 11px" }}>
              <div className="mono" style={{ fontSize: 10.5, color: "var(--brass)", marginBottom: 3 }}>
                {iss.path}
              </div>
              <div style={{ fontSize: 12.5 }}>{iss.message}</div>
            </div>
          ))}
        </div>
      )}
      <button className="btn btn--ghost btn--sm" style={{ marginTop: 16 }} onClick={onRun}>
        Re-run check
      </button>
    </div>
  );
}

function CoherencePanel({ text, onRun }: { text: string | null; onRun: () => void }) {
  if (text === null)
    return <RunPrompt label="Ask AI to review the draft for clarity, consistency, and gaps across sections." onRun={onRun} cta="✦ Review coherence" />;
  return (
    <div className="rise">
      <p className="eyebrow" style={{ marginBottom: 10 }}>
        AI coherence review
      </p>
      <div style={{ fontSize: 13.5, lineHeight: 1.6, whiteSpace: "pre-wrap" }}>{text}</div>
      <button className="btn btn--ghost btn--sm" style={{ marginTop: 16 }} onClick={onRun}>
        Re-run review
      </button>
    </div>
  );
}

function SdgPanel({
  suggestions,
  onRun,
  onApply,
}: {
  suggestions: SDGSuggestion[] | null;
  onRun: () => void;
  onApply: (codes: string[]) => void;
}) {
  if (suggestions === null)
    return <RunPrompt label="Suggest relevant SDG targets from your draft, validated against the official framework." onRun={onRun} cta="✦ Suggest SDG targets" />;
  return (
    <div className="rise">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <p className="eyebrow">{suggestions.length} suggested target(s)</p>
        {suggestions.length > 0 && (
          <button className="btn btn--brass btn--sm" onClick={() => onApply(suggestions.map((s) => s.target))}>
            Apply all
          </button>
        )}
      </div>
      <div style={{ display: "grid", gap: 9 }}>
        {suggestions.map((s) => (
          <div key={s.target} className="card" style={{ padding: "11px 13px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
              <span className="chip chip--fund" style={{ color: "var(--teal)" }}>
                SDG {s.target}
              </span>
              <button className="btn btn--ghost btn--sm" onClick={() => onApply([s.target])}>
                Add
              </button>
            </div>
            <div style={{ fontSize: 12.5, fontWeight: 600, marginTop: 7 }}>{s.title}</div>
            <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>{s.rationale}</div>
          </div>
        ))}
      </div>
      <button className="btn btn--ghost btn--sm" style={{ marginTop: 16 }} onClick={onRun}>
        Re-run
      </button>
    </div>
  );
}

function PreviewPanel({ schema, content }: { schema: TemplateSchema; content: ArtifactValues }) {
  return (
    <div className="rise">
      <p className="eyebrow" style={{ marginBottom: 12 }}>
        Document preview
      </p>
      {schema.sections.map((s) => {
        const lines: { label: string; value: string }[] = [];
        const sv = content[s.id];
        const push = (label: string, v: unknown) => {
          if (v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0)) return;
          lines.push({ label, value: Array.isArray(v) ? v.join(", ") : String(v) });
        };
        if (s.repeating && Array.isArray(sv)) {
          (sv as ArtifactValues[]).forEach((item, i) =>
            s.fields.forEach((f) => push(`${f.label} [${i + 1}]`, item?.[f.id])),
          );
        } else if (sv && typeof sv === "object") {
          s.fields.forEach((f) => push(f.label, (sv as ArtifactValues)[f.id]));
        }
        if (lines.length === 0) return null;
        return (
          <div key={s.id} style={{ marginBottom: 18 }}>
            <h4 style={{ fontSize: 14, borderBottom: "1px solid var(--line)", paddingBottom: 5 }}>{s.title}</h4>
            {lines.map((l, i) => (
              <div key={i} style={{ marginTop: 8 }}>
                <div className="mono faint" style={{ fontSize: 10.5 }}>{l.label}</div>
                <div style={{ fontSize: 12.5, lineHeight: 1.5 }}>{l.value}</div>
              </div>
            ))}
          </div>
        );
      })}
    </div>
  );
}

function RunPrompt({ label, onRun, cta }: { label: string; onRun: () => void; cta: string }) {
  return (
    <div style={{ paddingTop: 14 }}>
      <p className="muted" style={{ fontSize: 13, lineHeight: 1.55, marginBottom: 16 }}>
        {label}
      </p>
      <button className="btn btn--block" onClick={onRun}>
        {cta}
      </button>
    </div>
  );
}
