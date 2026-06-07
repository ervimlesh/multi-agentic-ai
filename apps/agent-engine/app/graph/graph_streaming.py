"""Drive the graph and translate its events into stream events for the widget.

Yields plain event dicts (`{"type": ..., ...}`); the API layer JSON-encodes them
into SSE frames. Uses LangGraph's dual stream mode:
  - "updates"  -> per-node state deltas  -> STATUS / FINAL events
  - "messages" -> LLM token chunks       -> TOKEN events (the streamed answer)

Human-in-the-loop: the graph is compiled with interrupt_before=["execute"], so a
browser run pauses before the Executor. After each astream pass we inspect the
checkpoint:
  - paused at execute + pending_approval set  -> emit approval_required, stop
  - paused at execute + no pending_approval   -> auto-resume (action was safe)
  - not paused                                -> emit FINAL

Two entry points share `_drive`:
  - run_and_stream:    start a fresh run from a task
  - resume_and_stream: continue a paused run after a Continue/Cancel decision
"""
from __future__ import annotations

from typing import Any, AsyncIterator

from app.graph.graph_events import EventType, event
from app.graph.graph_state import initial_state
from app.graph.main_graph import get_graph

# Friendly labels for the status line in the UI.
_NODE_LABELS = {
    "supervisor": "Understanding your request…",
    "respond": "Thinking…",
    "fetch": "Fetching the page…",
    "synthesize": "Reading and analyzing…",
    "open_browser": "Opening the browser…",
    "observer": "Looking at the page…",
    "decision": "Deciding what to do next…",
    "safety": "Checking if this needs your approval…",
    "execute": "Carrying out the action…",
    "reviewer": "Finalizing the answer…",
}

# Nodes whose streamed LLM tokens should be forwarded to the UI as the answer.
_TOKEN_NODES = {"synthesize", "respond"}


async def run_and_stream(
    *,
    run_id: str,
    thread_id: str,
    task: str,
    user_id: str | None = None,
    site_origin: str | None = None,
    history: list[dict] | None = None,
    images: list[str] | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Start a fresh run and stream its events."""
    state = initial_state(
        run_id=run_id,
        thread_id=thread_id,
        task=task,
        user_id=user_id,
        site_origin=site_origin,
        history=history,
        images=images,
    )
    async for ev in _drive(run_id=run_id, thread_id=thread_id, graph_input=state):
        yield ev


async def resume_and_stream(
    *,
    run_id: str,
    thread_id: str,
    decision: str,
) -> AsyncIterator[dict[str, Any]]:
    """Resume a paused run with a human decision ("approved" | "rejected")."""
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}
    # Record the decision so the Executor can read it, then resume (input=None).
    await graph.aupdate_state(config, {"approval_decision": decision})
    async for ev in _drive(run_id=run_id, thread_id=thread_id, graph_input=None):
        yield ev


async def _drive(
    *, run_id: str, thread_id: str, graph_input: Any
) -> AsyncIterator[dict[str, Any]]:
    graph = get_graph()
    config = {"configurable": {"thread_id": thread_id}}

    yield event(EventType.RUN_STARTED, run_id=run_id, thread_id=thread_id)

    final_answer: str | None = None
    current_input = graph_input
    try:
        while True:
            async for mode, chunk in graph.astream(
                current_input, config=config, stream_mode=["updates", "messages"]
            ):
                if mode == "messages":
                    msg_chunk, metadata = chunk
                    if metadata.get("langgraph_node") in _TOKEN_NODES:
                        text = getattr(msg_chunk, "content", "")
                        if text:
                            yield event(EventType.TOKEN, text=text)

                elif mode == "updates":
                    for node_name, update in chunk.items():
                        if node_name == "__interrupt__":
                            continue  # handled below via the checkpoint
                        label = _NODE_LABELS.get(node_name)
                        if label:
                            yield event(
                                EventType.STATUS, node=node_name, message=label
                            )
                        if isinstance(update, dict):
                            # Surface the action the Decision agent picked.
                            action = update.get("next_action")
                            if action and action.get("description"):
                                yield event(
                                    EventType.STATUS,
                                    node="action",
                                    message=f"→ {action['description']}",
                                )
                            if update.get("error"):
                                final_answer = None
                                yield event(EventType.ERROR, message=update["error"])
                            if update.get("final_answer"):
                                final_answer = update["final_answer"]

            # Did we pause before the Executor?
            snapshot = await graph.aget_state(config)
            if snapshot.next and "execute" in snapshot.next:
                pending = snapshot.values.get("pending_approval")
                if pending:
                    yield event(
                        EventType.APPROVAL_REQUIRED,
                        run_id=run_id,
                        thread_id=thread_id,
                        **pending,
                    )
                    yield event(EventType.RUN_ENDED, run_id=run_id, paused=True)
                    return
                # Safe action — resume automatically without asking.
                current_input = None
                continue
            break

        if final_answer is None:
            snapshot = await graph.aget_state(config)
            final_answer = snapshot.values.get("final_answer")
        yield event(EventType.FINAL, run_id=run_id, answer=final_answer or "")
        yield event(EventType.RUN_ENDED, run_id=run_id, paused=False)
    except Exception as exc:  # noqa: BLE001 — surface any failure to the client
        yield event(EventType.ERROR, message=f"{type(exc).__name__}: {exc}")
        yield event(EventType.RUN_ENDED, run_id=run_id, paused=False)
