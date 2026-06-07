import { useEffect, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "@/lib/api-client";
import { useAuth } from "@/store/auth-store";
import { useAgentChat } from "@/features/chat/hooks/use-chat";
import { Markdown } from "@/components/ui/markdown";

/** Read File objects into data URLs (base64) for the vision API. */
function filesToDataUrls(files: File[]): Promise<string[]> {
  return Promise.all(
    files
      .filter((f) => f.type.startsWith("image/"))
      .map(
        (f) =>
          new Promise<string>((resolve, reject) => {
            const r = new FileReader();
            r.onload = () => resolve(r.result as string);
            r.onerror = reject;
            r.readAsDataURL(f);
          }),
      ),
  );
}

/** Eight-point sparkle — the Claude / Claude Code brand mark. */
function BrandMark({ className, style }: { className?: string; style?: CSSProperties }) {
  return (
    <svg className={className} style={style} viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 1.5c.3 3.4 1.3 5.6 3 7s3.6 2.4 7 3c-3.4.3-5.6 1.3-7 3s-2.4 3.6-3 7c-.3-3.4-1.3-5.6-3-7s-3.6-2.4-7-3c3.4-.3 5.6-1.3 7-3s2.4-3.6 3-7Z" />
    </svg>
  );
}

/** Pixel-art robot mascot shown on the empty home screen. */
function Mascot({ className }: { className?: string }) {
  const c = "#d4866b";
  return (
    <svg className={className} viewBox="0 0 16 16" shapeRendering="crispEdges" aria-hidden>
      <rect x="2" y="3" width="12" height="9" fill={c} />
      <rect x="7" y="1" width="2" height="2" fill={c} />
      <rect x="4" y="6" width="2" height="2" fill="#1f1e1d" />
      <rect x="10" y="6" width="2" height="2" fill="#1f1e1d" />
      <rect x="4" y="12" width="2" height="2" fill={c} />
      <rect x="10" y="12" width="2" height="2" fill={c} />
    </svg>
  );
}

export default function DashboardPage() {
  const { tokens, clearAuth } = useAuth();
  const navigate = useNavigate();
  const [draft, setDraft] = useState("");
  const [pendingImages, setPendingImages] = useState<string[]>([]);
  const { messages, isStreaming, send, approve } = useAgentChat();
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const hasConversation = messages.length > 0;

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [messages]);

  async function handleLogout() {
    try {
      if (tokens?.refresh_token) await authApi.logout(tokens.refresh_token);
    } finally {
      clearAuth();
      navigate("/login", { replace: true });
    }
  }

  async function addFiles(files: File[]) {
    const urls = await filesToDataUrls(files);
    if (urls.length) setPendingImages((prev) => [...prev, ...urls]);
  }

  function handlePaste(e: React.ClipboardEvent) {
    const files = Array.from(e.clipboardData.files);
    if (files.some((f) => f.type.startsWith("image/"))) {
      e.preventDefault();
      void addFiles(files);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const task = draft.trim();
    if ((!task && !pendingImages.length) || isStreaming) return;
    setDraft("");
    const images = pendingImages;
    setPendingImages([]);
    void send(task, images.length ? images : undefined);
  }

  return (
    <div className="cc">
      <header className="cc__topbar">
        <div className="cc__tab">
          <BrandMark className="cc__brand-mark" style={{ width: 13, height: 13 }} />
          <span>Claude Code</span>
        </div>
        <div className="cc__topbar-actions">
          <button className="cc__icon-btn" title="Sign out" onClick={handleLogout}>
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>
          </button>
        </div>
      </header>

      <main className="cc__main">
        {!hasConversation ? (
          <>
            <div className="cc__brand">
              <BrandMark className="cc__brand-mark" />
              <span className="cc__brand-name">Claude Code</span>
            </div>
            <div className="cc__hero">
              <Mascot className="cc__mascot" />
              <p className="cc__hint">
                Ask me anything, paste a URL to analyze, attach a screenshot, or
                tell me to do something on a site.
              </p>
            </div>
          </>
        ) : (
          <div className="cc__messages" ref={scrollRef}>
            {messages.map((m) => (
              <div key={m.id} className={`cc__msg cc__msg--${m.role}`}>
                {m.role === "assistant" && (
                  <BrandMark className="cc__msg-avatar" />
                )}
                <div className="cc__msg-body">
                  {m.images && m.images.length > 0 && (
                    <div className="cc__msg-images">
                      {m.images.map((src, n) => (
                        <img key={n} src={src} alt="attachment" className="cc__msg-img" />
                      ))}
                    </div>
                  )}
                  {m.text &&
                    (m.role === "assistant" && !m.error ? (
                      <div className="cc__msg-text">
                        <Markdown text={m.text} />
                      </div>
                    ) : (
                      <div className={m.error ? "cc__msg-text cc__msg-text--error" : "cc__msg-text"}>
                        {m.text}
                      </div>
                    ))}
                  {!m.text && m.status && (
                    <div className="cc__msg-status">
                      <span className="cc__spinner" /> {m.status}
                    </div>
                  )}
                  {m.approval && (
                    <div className="cc__approval">
                      <div className="cc__approval-risk">⚠ {m.approval.risk_label} — needs your approval</div>
                      <div className="cc__approval-action">{m.approval.action}</div>
                      <div className="cc__approval-reason">{m.approval.reason}</div>
                      <div className="cc__approval-actions">
                        <button
                          className="cc__btn cc__btn--primary"
                          disabled={isStreaming}
                          onClick={() => approve(m.id, "approved")}
                        >
                          Continue
                        </button>
                        <button
                          className="cc__btn cc__btn--ghost"
                          disabled={isStreaming}
                          onClick={() => approve(m.id, "rejected")}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                  {m.decided && (
                    <div className="cc__decided">
                      {m.decided === "approved" ? "✅ You approved this" : "✋ You cancelled this"}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        <form className="cc__composer" onSubmit={handleSubmit}>
          {pendingImages.length > 0 && (
            <div className="cc__attachments">
              {pendingImages.map((src, n) => (
                <div key={n} className="cc__attachment">
                  <img src={src} alt="attachment" />
                  <button
                    type="button"
                    className="cc__attachment-x"
                    title="Remove"
                    onClick={() =>
                      setPendingImages((prev) => prev.filter((_, idx) => idx !== n))
                    }
                  >
                    ×
                  </button>
                </div>
              ))}
            </div>
          )}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            hidden
            onChange={(e) => {
              void addFiles(Array.from(e.target.files ?? []));
              e.target.value = "";
            }}
          />
          <div className="cc__input-row">
            <input
              className="cc__input"
              placeholder="Ask anything, paste a URL, or attach an image…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onPaste={handlePaste}
              disabled={isStreaming}
            />
            <button type="button" className="cc__icon-btn" title="Dictate">
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="9" y="2" width="6" height="11" rx="3" />
                <path d="M5 10a7 7 0 0 0 14 0" />
                <line x1="12" y1="19" x2="12" y2="22" />
              </svg>
            </button>
          </div>
          <div className="cc__toolbar">
            <button
              type="button"
              className="cc__icon-btn"
              title="Attach image"
              onClick={() => fileInputRef.current?.click()}
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </button>
            <button type="button" className="cc__icon-btn" title="Slash commands">
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="16" y1="5" x2="8" y2="19" />
              </svg>
            </button>
            <span className="cc__toolbar-spacer" />
            <span className="cc__mode">
              <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden>
                <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" />
              </svg>
              Auto mode
            </span>
            <button
              type="submit"
              className="cc__send"
              disabled={(!draft.trim() && !pendingImages.length) || isStreaming}
              title="Send"
            >
              <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="19" x2="12" y2="5" />
                <polyline points="6 11 12 5 18 11" />
              </svg>
            </button>
          </div>
        </form>
      </main>
    </div>
  );
}
