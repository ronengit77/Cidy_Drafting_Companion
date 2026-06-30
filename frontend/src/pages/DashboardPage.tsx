import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { useToast } from "../lib/toast";
import { AppHeader, fundColor } from "../components/ui";
import type { ArtifactSummary, SchemaInfo } from "../lib/types";

function timeAgo(iso: string): string {
  const d = new Date(iso).getTime();
  const s = Math.floor((Date.now() - d) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function DashboardPage() {
  const nav = useNavigate();
  const toast = useToast();
  const [artifacts, setArtifacts] = useState<ArtifactSummary[] | null>(null);
  const [showNew, setShowNew] = useState(false);

  useEffect(() => {
    api
      .listArtifacts()
      .then(setArtifacts)
      .catch((e) => {
        toast((e as ApiError).message, "err");
        setArtifacts([]);
      });
  }, [toast]);

  return (
    <div style={{ minHeight: "100vh" }}>
      <AppHeader />
      <main style={{ maxWidth: 1040, margin: "0 auto", padding: "40px 28px 80px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            marginBottom: 28,
          }}
        >
          <div className="rise">
            <p className="eyebrow">Your workspace</p>
            <h1 style={{ fontSize: 30, marginTop: 8 }}>Drafts</h1>
          </div>
          <button className="btn" onClick={() => setShowNew(true)}>
            + New draft
          </button>
        </div>

        {artifacts === null ? (
          <div style={{ display: "grid", gap: 12 }}>
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                className="card"
                style={{ height: 76, opacity: 0.5, animation: "fade 0.6s ease both" }}
              />
            ))}
          </div>
        ) : artifacts.length === 0 ? (
          <EmptyState onNew={() => setShowNew(true)} />
        ) : (
          <div style={{ display: "grid", gap: 12 }}>
            {artifacts.map((a, i) => (
              <button
                key={a.id}
                className="card rise"
                onClick={() => nav(`/artifacts/${a.id}`)}
                style={{
                  textAlign: "left",
                  padding: "18px 20px",
                  cursor: "pointer",
                  display: "grid",
                  gridTemplateColumns: "1fr auto",
                  alignItems: "center",
                  gap: 16,
                  animationDelay: `${i * 45}ms`,
                  background: "#fff",
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                    <span
                      className="chip chip--fund"
                      style={{ color: fundColor(a.schema_id.startsWith("da") ? "DA" : "RPTC") }}
                    >
                      {a.schema_id.startsWith("da") ? "DA" : "RPTC"}
                    </span>
                    <span className="chip">v{a.version_no}</span>
                  </div>
                  <div
                    style={{
                      fontFamily: "var(--font-serif)",
                      fontSize: 17,
                      fontWeight: 500,
                      whiteSpace: "nowrap",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {a.title || "Untitled draft"}
                  </div>
                  <div className="mono faint" style={{ fontSize: 11.5, marginTop: 4 }}>
                    {a.schema_id}
                  </div>
                </div>
                <div style={{ textAlign: "right", color: "var(--ink-soft)", fontSize: 12.5 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, justifyContent: "flex-end" }}>
                    <span className="dot dot--warn" /> {a.status}
                  </div>
                  <div className="faint" style={{ marginTop: 5 }}>
                    edited {timeAgo(a.updated_at)}
                  </div>
                </div>
              </button>
            ))}
          </div>
        )}
      </main>
      {showNew && <NewDraftModal onClose={() => setShowNew(false)} />}
    </div>
  );
}

function EmptyState({ onNew }: { onNew: () => void }) {
  return (
    <div
      className="card rise"
      style={{ padding: "56px 32px", textAlign: "center", borderStyle: "dashed" }}
    >
      <h3 style={{ fontSize: 21 }}>No drafts yet</h3>
      <p className="muted" style={{ maxWidth: 380, margin: "10px auto 22px" }}>
        Start a concept note or activity proposal and let CIdy guide you through it.
      </p>
      <button className="btn" onClick={onNew}>
        + Create your first draft
      </button>
    </div>
  );
}

function NewDraftModal({ onClose }: { onClose: () => void }) {
  const nav = useNavigate();
  const toast = useToast();
  const [schemas, setSchemas] = useState<SchemaInfo[] | null>(null);
  const [picked, setPicked] = useState<string>("");
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.listSchemas().then((s) => {
      setSchemas(s);
      if (s.length) setPicked(s[0].schema_id);
    });
  }, []);

  async function create() {
    if (!picked) return;
    setBusy(true);
    try {
      const a = await api.createArtifact(picked, title.trim() || "Untitled draft");
      nav(`/artifacts/${a.id}`);
    } catch (e) {
      toast((e as ApiError).message, "err");
      setBusy(false);
    }
  }

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(20,26,38,0.42)",
        backdropFilter: "blur(2px)",
        display: "grid",
        placeItems: "center",
        zIndex: 50,
        padding: 20,
        animation: "fade 0.18s ease both",
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="card rise"
        style={{ width: "100%", maxWidth: 520, padding: 26, boxShadow: "var(--shadow-lg)" }}
      >
        <p className="eyebrow">New draft</p>
        <h2 style={{ fontSize: 22, marginTop: 8, marginBottom: 18 }}>Choose a template</h2>

        <div style={{ display: "grid", gap: 10, marginBottom: 18 }}>
          {schemas === null ? (
            <span className="muted">Loading templates…</span>
          ) : (
            schemas.map((s) => (
              <label
                key={s.schema_id}
                className="card"
                style={{
                  padding: "13px 15px",
                  display: "flex",
                  gap: 12,
                  alignItems: "center",
                  cursor: "pointer",
                  borderColor: picked === s.schema_id ? "var(--navy)" : "var(--line)",
                  boxShadow: picked === s.schema_id ? "0 0 0 3px rgba(26,43,74,0.1)" : "var(--shadow-sm)",
                }}
              >
                <input
                  type="radio"
                  name="schema"
                  checked={picked === s.schema_id}
                  onChange={() => setPicked(s.schema_id)}
                />
                <span>
                  <span className="chip chip--fund" style={{ color: fundColor(s.fund), marginRight: 8 }}>
                    {s.fund}
                  </span>
                  <strong style={{ fontSize: 14.5 }}>{s.title}</strong>
                  <div className="mono faint" style={{ fontSize: 11, marginTop: 3 }}>
                    {s.schema_id} · {s.version}
                  </div>
                </span>
              </label>
            ))
          )}
        </div>

        <label className="field-label" htmlFor="t">
          Working title
        </label>
        <input
          id="t"
          className="input"
          placeholder="e.g. Strengthening tax cooperation in LDCs"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />

        <div style={{ display: "flex", gap: 10, justifyContent: "flex-end", marginTop: 22 }}>
          <button className="btn btn--ghost" onClick={onClose}>
            Cancel
          </button>
          <button className="btn" onClick={create} disabled={busy || !picked}>
            {busy ? <span className="spinner" /> : "Create draft"}
          </button>
        </div>
      </div>
    </div>
  );
}
