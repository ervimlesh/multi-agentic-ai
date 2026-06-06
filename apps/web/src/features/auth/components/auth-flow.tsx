import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError, authApi } from "@/lib/api-client";
import { useAuth } from "@/store/auth-store";
import { AuthShell } from "./auth-shell";
import { OtpInput } from "./otp-input";

type Mode = "login" | "register";
type Step = "email" | "code";

export function AuthFlow({ mode }: { mode: Mode }) {
  const navigate = useNavigate();
  const { setAuth } = useAuth();

  const [step, setStep] = useState<Step>("email");
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [code, setCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resent, setResent] = useState(false);

  const isRegister = mode === "register";

  async function requestCode(e?: FormEvent) {
    e?.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (isRegister) await authApi.register(email, fullName);
      else await authApi.login(email);
      setStep("code");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  async function verify(submitted: string) {
    setError(null);
    setLoading(true);
    try {
      const res = await authApi.verify(email, submitted);
      setAuth(res);
      navigate("/", { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Invalid code");
      setCode("");
    } finally {
      setLoading(false);
    }
  }

  async function resend() {
    setError(null);
    try {
      await authApi.resend(email);
      setResent(true);
      setTimeout(() => setResent(false), 3000);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not resend");
    }
  }

  // ---------- Step 1: email ----------
  if (step === "email") {
    return (
      <AuthShell>
        <h1 className="auth-title">
          {isRegister ? "Create your account" : "Welcome back"}
        </h1>
        <p className="auth-subtitle">
          {isRegister
            ? "Enter your details and we'll email you a verification code."
            : "Enter your email and we'll send you a sign-in code."}
        </p>

        <form onSubmit={requestCode} style={{ width: "100%" }}>
          {error && <div className="error">{error}</div>}

          {isRegister && (
            <div className="field">
              <label className="field__label" htmlFor="name">
                Full name
              </label>
              <input
                id="name"
                className="input"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Ada Lovelace"
                required
              />
            </div>
          )}

          <div className="field">
            <label className="field__label" htmlFor="email">
              Email address
            </label>
            <input
              id="email"
              className="input"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              autoComplete="email"
              required
            />
          </div>

          <button
            className="btn btn--primary"
            type="submit"
            disabled={loading || !email || (isRegister && !fullName)}
          >
            {loading ? "Sending code…" : "Continue with email"}
          </button>
        </form>

        <p className="auth-footer">
          {isRegister ? (
            <>
              Already have an account? <Link to="/login">Sign in</Link>
            </>
          ) : (
            <>
              Don&apos;t have an account? <Link to="/register">Sign up</Link>
            </>
          )}
        </p>
      </AuthShell>
    );
  }

  // ---------- Step 2: code ----------
  return (
    <AuthShell>
      <h1 className="auth-title">Enter verification code</h1>
      <p className="auth-subtitle">
        We sent a 6-digit code to <strong>{email}</strong>
      </p>

      {error && <div className="error">{error}</div>}

      <OtpInput
        value={code}
        onChange={setCode}
        onComplete={verify}
        disabled={loading}
      />

      <button
        className="btn btn--primary"
        disabled={loading || code.length < 6}
        onClick={() => verify(code)}
      >
        {loading ? "Verifying…" : "Verify and continue"}
      </button>

      <div className="auth-footer">
        {resent ? (
          <span className="muted">A new code is on its way ✓</span>
        ) : (
          <button className="link" onClick={resend} disabled={loading}>
            Resend code
          </button>
        )}
      </div>

      <button
        className="btn btn--ghost"
        style={{ marginTop: 8 }}
        onClick={() => {
          setStep("email");
          setCode("");
          setError(null);
        }}
      >
        ← Use a different email
      </button>
    </AuthShell>
  );
}
