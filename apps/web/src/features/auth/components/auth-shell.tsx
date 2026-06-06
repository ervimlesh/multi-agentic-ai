import type { ReactNode } from "react";

function Sunburst() {
  return (
    <svg className="brand__mark" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <g>
        {Array.from({ length: 12 }).map((_, i) => (
          <rect
            key={i}
            x="11.1"
            y="1"
            width="1.8"
            height="7"
            rx="0.9"
            transform={`rotate(${i * 30} 12 12)`}
          />
        ))}
      </g>
    </svg>
  );
}

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="auth-screen">
      <div className="auth-card">
        <div className="brand">
          <Sunburst />
          <span className="brand__name">Multi-Agent AI</span>
        </div>
        {children}
        <p className="legal">
          By continuing, you agree to our Terms of Service and acknowledge our
          Privacy Policy.
        </p>
      </div>
    </div>
  );
}
