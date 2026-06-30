import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";

export function Brand({ size = 28 }: { size?: number }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 10 }}>
      <svg width={size} height={size} viewBox="0 0 32 32" fill="none" aria-hidden>
        <rect width="32" height="32" rx="6" fill="#1A2B4A" />
        <path
          d="M22 11.4C20.9 10.2 19.3 9.5 17.4 9.5C13.6 9.5 10.8 12.4 10.8 16C10.8 19.6 13.6 22.5 17.4 22.5C19.3 22.5 20.9 21.8 22 20.6"
          stroke="#C4912F"
          strokeWidth="2.4"
          strokeLinecap="round"
        />
        <circle cx="22.3" cy="16" r="1.7" fill="#FBFAF7" />
      </svg>
      <span style={{ fontFamily: "var(--font-serif)", fontSize: 19, fontWeight: 500, letterSpacing: "-0.01em" }}>
        CIdy <span style={{ color: "var(--ink-faint)", fontWeight: 400 }}>·</span>{" "}
        <span style={{ fontSize: 14, color: "var(--ink-soft)", fontFamily: "var(--font-sans)" }}>
          Drafting Companion
        </span>
      </span>
    </span>
  );
}

export function FullLoader({ label }: { label?: string }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        gap: 14,
        color: "var(--ink-soft)",
      }}
    >
      <div style={{ display: "grid", justifyItems: "center", gap: 14 }}>
        <span className="spinner" style={{ color: "var(--brass)", width: 22, height: 22 }} />
        {label && <span className="eyebrow">{label}</span>}
      </div>
    </div>
  );
}

export function AppHeader() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  return (
    <header
      style={{
        position: "sticky",
        top: 0,
        zIndex: 20,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "14px 28px",
        borderBottom: "1px solid var(--line)",
        background: "rgba(251,250,247,0.86)",
        backdropFilter: "saturate(140%) blur(8px)",
      }}
    >
      <Link to="/" aria-label="Home">
        <Brand />
      </Link>
      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        {user && (
          <span className="mono" style={{ fontSize: 12.5, color: "var(--ink-soft)" }}>
            {user.email}
          </span>
        )}
        <button
          className="btn btn--ghost btn--sm"
          onClick={() => {
            logout();
            nav("/login");
          }}
        >
          Sign out
        </button>
      </div>
    </header>
  );
}

export function fundColor(fund: string): string {
  return fund === "DA" ? "var(--teal)" : "var(--brass)";
}
