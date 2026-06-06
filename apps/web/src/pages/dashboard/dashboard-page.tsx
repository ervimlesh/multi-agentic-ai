import { useNavigate } from "react-router-dom";
import { authApi } from "@/lib/api-client";
import { useAuth } from "@/store/auth-store";

export default function DashboardPage() {
  const { user, tokens, clearAuth } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    try {
      if (tokens?.refresh_token) await authApi.logout(tokens.refresh_token);
    } finally {
      clearAuth();
      navigate("/login", { replace: true });
    }
  }

  return (
    <div className="dash">
      <h1 className="auth-title" style={{ textAlign: "left" }}>
        You&apos;re signed in 🎉
      </h1>
      <p className="auth-subtitle" style={{ textAlign: "left" }}>
        Passwordless OTP authentication is working end-to-end.
      </p>

      <div className="dash__card">
        <div className="dash__row">
          <span className="muted">Name</span>
          <span>{user?.full_name}</span>
        </div>
        <div className="dash__row">
          <span className="muted">Email</span>
          <span>{user?.email}</span>
        </div>
        <div className="dash__row">
          <span className="muted">Verified</span>
          <span>{user?.is_verified ? "Yes" : "No"}</span>
        </div>
        <div className="dash__row">
          <span className="muted">User ID</span>
          <span style={{ fontFamily: "monospace", fontSize: 12 }}>{user?.id}</span>
        </div>
      </div>

      <button
        className="btn btn--primary"
        style={{ marginTop: 20, maxWidth: 200 }}
        onClick={handleLogout}
      >
        Sign out
      </button>
    </div>
  );
}
