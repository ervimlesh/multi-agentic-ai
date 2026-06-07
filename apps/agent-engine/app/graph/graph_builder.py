r"""Assemble the LangGraph StateGraph.

Topology:

    START -> supervisor -> (analyze) fetch -> synthesize -----------------> reviewer -> END
                        \-> (browser) open_browser -> observer -> decision -+-> safety -> execute -+
                                                          ^                  |                       |
                                                          +------------------+-----------------------+
                                                          (loop: observe -> decide -> gate -> act)

Flow A (analyze) reads a URL and answers. Flow B (browser) drives a real
Chromium page in an observe→decide→safety→execute loop; `safety` pauses before
`execute` (interrupt_before) so risky actions need human approval. Nodes for
fetch/synthesize live here because they're thin glue between the ingestion
loader, the synthesis chain, and graph state.
"""
from __future__ import annotations

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from app.agents.browser_agent import execute_node, observer_node, open_browser_node
from app.agents.evaluator_agent import reviewer_node
from app.agents.qa_agent import respond_node
from app.agents.reasoning_agent import decision_node
from app.agents.safety_agent import safety_node
from app.agents.supervisor_agent import supervisor_node
from app.chains.answer_synthesis_chain import stream_answer
from app.graph.graph_checkpointer import get_checkpointer
from app.graph.graph_router import (
    route_after_decision,
    route_after_execute,
    route_after_supervisor,
)
from app.graph.graph_state import AgentState
from app.rag.ingestion.web_loader import FetchError, fetch_page


async def fetch_node(state: AgentState) -> dict:
    """Flow A: download the URL and reduce it to readable text."""
    url = state.get("url")
    if not url:
        return {
            "final_answer": (
                "I didn't find a URL in your message. Paste a link and tell me "
                "what you'd like to know about it."
            )
        }
    try:
        page = await fetch_page(url)
    except FetchError as exc:
        return {"error": str(exc)}
    return {"page_text": page.text, "page_title": page.title, "url": page.url}


async def synthesize_node(state: AgentState, config: RunnableConfig) -> dict:
    """Flow A: answer the task from the fetched page text (streamed).

    `config` is forwarded to the LLM so token streaming works on Python 3.10.
    """
    if state.get("error") or not state.get("page_text"):
        return {}
    page = {
        "url": state.get("url"),
        "title": state.get("page_title"),
        "text": state.get("page_text"),
        "truncated": False,
    }
    parts: list[str] = []
    async for token in stream_answer(state.get("task", ""), page, config=config):
        parts.append(token)
    return {"final_answer": "".join(parts)}


def build_graph():
    """Build and compile the agent graph."""
    g = StateGraph(AgentState)

    g.add_node("supervisor", supervisor_node)
    g.add_node("respond", respond_node)
    g.add_node("fetch", fetch_node)
    g.add_node("synthesize", synthesize_node)
    g.add_node("open_browser", open_browser_node)
    g.add_node("observer", observer_node)
    g.add_node("decision", decision_node)
    g.add_node("safety", safety_node)
    g.add_node("execute", execute_node)
    g.add_node("reviewer", reviewer_node)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {"respond": "respond", "fetch": "fetch", "browser": "open_browser"},
    )
    # Chat + vision
    g.add_edge("respond", "reviewer")
    # Flow A
    g.add_edge("fetch", "synthesize")
    g.add_edge("synthesize", "reviewer")
    # Flow B: open -> observe -> decide -> (safety -> execute -> observe ...) | reviewer
    g.add_edge("open_browser", "observer")
    g.add_edge("observer", "decision")
    g.add_conditional_edges(
        "decision",
        route_after_decision,
        {"safety": "safety", "reviewer": "reviewer"},
    )
    g.add_edge("safety", "execute")
    g.add_conditional_edges(
        "execute",
        route_after_execute,
        {"observer": "observer", "reviewer": "reviewer"},
    )
    g.add_edge("reviewer", END)

    # Pause before the Executor so risky actions can be approved by a human.
    # The streaming layer auto-resumes when the action wasn't actually risky.
    return g.compile(
        checkpointer=get_checkpointer(),
        interrupt_before=["execute"],
    )
