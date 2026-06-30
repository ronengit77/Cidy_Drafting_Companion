import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useToast } from "../lib/toast";
import { Brand } from "../components/ui";

export function LoginPage() {
  const { user, login } = useAuth();
  const nav = useNavigate();
  const toast = useToast();
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);
  const [devLink, setDevLink] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (user) return <Navigate to="/" replace />;

  async function requestLink(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim()) return;
    setBusy(true);
    try {
      const r = await api.requestMagicLink(email.trim());
      setSent(true);
      setDevLink(r.dev_link);
    } catch (err) {
      toast((err as ApiError).message, "err");
    } finally {
      setBusy(false);
    }
  }

  async function enterDev() {
    if (!devLink) return;
    const token = devLink.split("token=")[1];
    setBusy(true);
    try {
      const { access_token } = await api.verify(token);
      await login(access_token);
      nav("/");
    } catch (err) {
      toast((err as ApiError).message, "err");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", display: "grid", gridTemplateColumns: "1fr 1fr" }}>
      {/* Left — institutional panel */}
      <aside
        style={{
          background:
            "linear-gradient(155deg, #1a2b4a 0%, #16243d 55%, #101b2e 100%)",
          color: "#eef1f6",
          padding: "56px 56px 44px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <div
          aria-hidden
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage:
              "radial-gradient(circle at 80% 12%, rgba(196,145,47,0.18), transparent 40%)",
          }}
        />
        <div style={{ position: "relative" }}>
          <span style={{ display: "inline-flex", filter: "brightness(1.6)" }}>
            <Brand size={30} />
          </span>
        </div>
        <div style={{ position: "relative", maxWidth: 440 }} className="rise">
          <p className="eyebrow" style={{ color: "var(--brass-2)" }}>
            UN funding artifacts · RPTC · Development Account
          </p>
          <h1
            style={{
              fontSize: 40,
              lineHeight: 1.08,
              color: "#fbfaf7",
              margin: "18px 0 0",
            }}
          >
            Draft with clarity, coherence, and confidence.
          </h1>
          <p style={{ color: "#aeb8cb", marginTop: 18, fontSize: 15.5, lineHeight: 1.6 }}>
            CIdy guides you through concept notes and activity proposals — shaping your
            language, checking coherence, and aligning to SDG targets as you write.
          </p>
        </div>
        <p className="mono" style={{ position: "relative", color: "#6f7c95", fontSize: 11.5 }}>
          Passwordless sign-in · your work, saved as you go
        </p>
      </aside>

      {/* Right — sign in */}
      <main style={{ display: "grid", placeItems: "center", padding: 32 }}>
        <div style={{ width: "100%", maxWidth: 380 }} className="rise">
          <h2 style={{ fontSize: 27 }}>Sign in</h2>
          <p className="muted" style={{ marginTop: 8, marginBottom: 28 }}>
            We'll send a one-time link to your email — no password needed.
          </p>

          {!sent ? (
            <form onSubmit={requestLink}>
              <label className="field-label" htmlFor="email">
                Email address
              </label>
              <input
                id="email"
                className="input"
                type="email"
                autoFocus
                placeholder="you@un.org"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
              <button className="btn btn--block" style={{ marginTop: 16 }} disabled={busy}>
                {busy ? <span className="spinner" /> : "Send sign-in link"}
              </button>
            </form>
          ) : (
            <div className="card" style={{ padding: 20 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
                <span className="dot dot--ok" />
                <strong style={{ fontSize: 14 }}>Link sent to {email}</strong>
              </div>
              <p className="muted" style={{ fontSize: 13.5, marginTop: 10 }}>
                Check your inbox for the sign-in link.
              </p>
              {devLink && (
                <div
                  style={{
                    marginTop: 16,
                    paddingTop: 16,
                    borderTop: "1px dashed var(--line-strong)",
                  }}
                >
                  <p className="eyebrow" style={{ marginBottom: 10 }}>
                    Dev mode — link returned directly
                  </p>
                  <button className="btn btn--brass btn--block" onClick={enterDev} disabled={busy}>
                    {busy ? <span className="spinner" /> : "Enter →"}
                  </button>
                </div>
              )}
              <button
                className="btn btn--ghost btn--sm"
                style={{ marginTop: 14 }}
                onClick={() => {
                  setSent(false);
                  setDevLink(null);
                }}
              >
                Use a different email
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
