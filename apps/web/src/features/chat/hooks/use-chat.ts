// Drives one agent conversation against the agent-engine SSE endpoint.
//
// Keeps a stable thread_id across turns, streams assistant tokens into the last
// message, surfaces node status, and handles the human-in-the-loop approval:
// when the agent pauses on a risky action it attaches an `approval` payload to
// the assistant message; `approve()` resumes the run.
import { useCallback, useEffect, useRef, useState } from "react";
import {
  approveAgentRun,
  streamAgentRun,
  type AgentEvent,
  type ApprovalPayload,
} from "@/lib/sse";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  images?: string[]; // attached image data URLs (user messages)
  status?: string; // transient node label while streaming
  error?: boolean;
  approval?: ApprovalPayload; // present while awaiting Continue/Cancel
  decided?: "approved" | "rejected"; // set once the user has chosen
}

function uid() {
  return Math.random().toString(36).slice(2);
}

export function useAgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const threadId = useRef<string | undefined>(undefined);
  const messagesRef = useRef<ChatMessage[]>([]);
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const patchLast = useCallback((patch: Partial<ChatMessage>) => {
    setMessages((prev) => {
      if (!prev.length) return prev;
      const next = [...prev];
      next[next.length - 1] = { ...next[next.length - 1], ...patch };
      return next;
    });
  }, []);

  const handleEvent = useCallback(
    (ev: AgentEvent) => {
      switch (ev.type) {
        case "run_started":
          threadId.current = ev.thread_id;
          break;
        case "status":
          patchLast({ status: ev.message });
          break;
        case "token":
          setMessages((prev) => {
            if (!prev.length) return prev;
            const next = [...prev];
            const last = next[next.length - 1];
            next[next.length - 1] = {
              ...last,
              text: last.text + ev.text,
              status: undefined,
            };
            return next;
          });
          break;
        case "approval_required":
          patchLast({
            status: undefined,
            approval: {
              action: ev.action,
              risk: ev.risk,
              risk_label: ev.risk_label,
              reason: ev.reason,
              url: ev.url,
            },
          });
          break;
        case "final":
          setMessages((prev) => {
            if (!prev.length) return prev;
            const next = [...prev];
            const last = next[next.length - 1];
            next[next.length - 1] = {
              ...last,
              status: undefined,
              text: last.text || ev.answer || "",
            };
            return next;
          });
          break;
        case "error":
          patchLast({ text: ev.message, status: undefined, error: true });
          break;
        case "run_ended":
          break;
      }
    },
    [patchLast],
  );

  const send = useCallback(
    async (task: string, images?: string[]) => {
      const trimmed = task.trim();
      if ((!trimmed && !images?.length) || isStreaming) return;

      // Build conversation history from completed turns (exclude the new ones).
      const history = messagesRef.current
        .filter((m) => m.text && !m.approval)
        .map((m) => ({ role: m.role, content: m.text }));

      setMessages((prev) => [
        ...prev,
        { id: uid(), role: "user", text: trimmed, images },
        { id: uid(), role: "assistant", text: "", status: "Starting…" },
      ]);
      setIsStreaming(true);

      await streamAgentRun(
        { task: trimmed, thread_id: threadId.current, history, images },
        { onEvent: handleEvent, onError: (e) => patchLast({ text: e.message, error: true, status: undefined }) },
      );

      setIsStreaming(false);
    },
    [isStreaming, handleEvent, patchLast],
  );

  const approve = useCallback(
    async (messageId: string, decision: "approved" | "rejected") => {
      if (isStreaming || !threadId.current) return;

      // Lock the decision on the approval message (hides the buttons) and add a
      // placeholder for the continuation.
      setMessages((prev) => [
        ...prev.map((m) =>
          m.id === messageId ? { ...m, decided: decision, approval: undefined } : m,
        ),
        { id: uid(), role: "assistant", text: "", status: "Resuming…" },
      ]);
      setIsStreaming(true);

      await approveAgentRun(threadId.current, decision, {
        onEvent: handleEvent,
        onError: (e) => patchLast({ text: e.message, error: true, status: undefined }),
      });

      setIsStreaming(false);
    },
    [isStreaming, handleEvent, patchLast],
  );

  return { messages, isStreaming, send, approve };
}
