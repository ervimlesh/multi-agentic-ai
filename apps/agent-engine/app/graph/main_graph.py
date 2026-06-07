"""Compiled graph singleton.

Build once at import; reuse across requests. The compiled graph is thread-safe
for concurrent `astream`/`astream_events` calls keyed by distinct thread_ids.
"""
from __future__ import annotations

from functools import lru_cache


@lru_cache(maxsize=1)
def get_graph():
    # Imported lazily so importing this module doesn't require Groq creds.
    from app.graph.graph_builder import build_graph

    return build_graph()
