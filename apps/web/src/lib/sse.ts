// SSE-over-fetch client for the agent-engine streaming endpoint.
//
// The browser's native EventSource only supports GET, but /agent/run is a POST
// (it carries the task body), so we stream the response with fetch + a
// ReadableStream reader and parse SSE frames ourselves.

const AGENT_URL = import.meta.env.VITE_AGENT_URL ?? "";

export interface ApprovalPayload {
  action: string;
  risk: string;
  risk_label: string;
  reason: string;
  url?: string | null;
}

export type AgentEvent =
  | { type: "run_started"; run_id: string; thread_id: string }
  | { type: "status"; node: string; message: string }
  | { type: "token"; text: string }
  | ({ type: "approval_required"; run_id: string; thread_id: string } & ApprovalPayload)
  | { type: "final"; run_id: string; answer: string }
  | { type: "error"; message: string }
  | { type: "run_ended"; run_id: string; paused?: boolean };

export interface HistoryTurn {
  role: "user" | "assistant";
  content: string;
}

export interface RunRequest {
  task: string;
  thread_id?: string;
  user_id?: string;
  site_origin?: string;
  history?: HistoryTurn[];
  images?: string[]; // data:image/...;base64,... URLs
}

export interface StreamHandlers {
  onEvent: (event: AgentEvent) => void;
  onError?: (error: Error) => void;
  signal?: AbortSignal;
}

/**
 * POST a task to the agent and dispatch each streamed event to `onEvent`.
 * Resolves when the stream closes. Pass `signal` to cancel an in-flight run.
 */
export async function streamAgentRun(
  req: RunRequest,
  handlers: StreamHandlers,
): Promise<void> {
  return postAndStream(`${AGENT_URL}/agent/run`, req, handlers);
}

/**
 * Resume a paused run with the user's Continue/Cancel decision and stream the
 * continuation.
 */
export async function approveAgentRun(
  threadId: string,
  decision: "approved" | "rejected",
  handlers: StreamHandlers,
): Promise<void> {
  return postAndStream(
    `${AGENT_URL}/agent/${encodeURIComponent(threadId)}/approve`,
    { decision },
    handlers,
  );
}

async function postAndStream(
  url: string,
  body: unknown,
  { onEvent, onError, signal }: StreamHandlers,
): Promise<void> {
  let res: Response;
  try {
    res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(body),
      signal,
    });
  } catch (err) {
    onError?.(err as Error);
    return;
  }

  if (!res.ok || !res.body) {
    onError?.(new Error(`Agent request failed (${res.status})`));
    return;
  }

  // Guard against a silent hang: if the dev proxy isn't routing /agent to the
  // agent-engine, Vite returns the SPA's index.html (200, text/html) and we'd
  // wait forever for events that never come. Surface it instead.
  const ctype = res.headers.get("content-type") ?? "";
  if (!ctype.includes("text/event-stream")) {
    onError?.(
      new Error(
        "Agent endpoint didn't return an event stream — is the agent-engine " +
          "running on :8100 and the Vite dev server restarted after the /agent " +
          "proxy was added? (got content-type: " + (ctype || "none") + ")",
      ),
    );
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      // Normalize CRLF -> LF. sse-starlette emits `\r\n` line endings, so frames
      // are separated by `\r\n\r\n`; without this we'd never find a boundary.
      buffer = (buffer + decoder.decode(value, { stream: true })).replace(/\r\n/g, "\n");

      // SSE frames are separated by a blank line.
      let sep: number;
      while ((sep = buffer.indexOf("\n\n")) !== -1) {
        const frame = buffer.slice(0, sep);
        buffer = buffer.slice(sep + 2);
        const data = parseFrameData(frame);
        if (data) {
          try {
            onEvent(JSON.parse(data) as AgentEvent);
          } catch {
            /* ignore keep-alive / non-JSON frames */
          }
        }
      }
    }
  } catch (err) {
    if ((err as Error).name !== "AbortError") onError?.(err as Error);
  } finally {
    reader.releaseLock();
  }
}

// Concatenate the `data:` lines of one SSE frame (ignoring `event:`/`id:`/`:`).
// Buffer is already CRLF-normalized, so splitting on "\n" is safe.
function parseFrameData(frame: string): string | null {
  const out: string[] = [];
  for (const line of frame.split("\n")) {
    if (line.startsWith("data:")) out.push(line.slice(5).trimStart());
  }
  return out.length ? out.join("\n") : null;
}
