"""Playwright browser session + a per-thread session registry (Flow B).

A BrowserSession owns one Chromium browser/context/page. The page persists
across graph nodes within a run (observe → act → observe again all hit the same
live page), so we keep sessions in an in-process registry keyed by thread_id —
the Playwright objects are bound to the running event loop and can't be
serialized into graph state.

Because the registry is in-process, human-in-the-loop pauses (which keep the
session open between two HTTP requests) only work within a single worker. That's
fine for dev; a multi-worker deployment would need sticky sessions or a remote
browser (e.g. Playwright server / browserless).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from playwright.async_api import Browser, Page, async_playwright

from app.config.settings import settings

# Injects a stable data-agent-id onto each visible interactive element and
# returns a compact description list for the LLM to choose from.
_COLLECT_ELEMENTS_JS = """
(limit) => {
  const sel = 'a, button, input, textarea, select, [role=button], [role=link]';
  const els = Array.from(document.querySelectorAll(sel));
  const out = [];
  let i = 0;
  for (const el of els) {
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;            // skip hidden
    if (i >= limit) break;
    el.setAttribute('data-agent-id', String(i));
    const tag = el.tagName.toLowerCase();
    const kind = (tag === 'input' || tag === 'textarea' || tag === 'select')
      ? 'input' : (tag === 'a' ? 'link' : 'button');
    const label = (el.innerText || el.value || el.getAttribute('placeholder')
      || el.getAttribute('aria-label') || '').trim().replace(/\\s+/g, ' ').slice(0, 80);
    out.push({ id: i, kind, text: label });
    i++;
  }
  return out;
}
"""


@dataclass
class BrowserSession:
    thread_id: str
    _browser: Optional[Browser] = None
    _page: Optional[Page] = None
    _pw: Any = None
    started: bool = field(default=False)

    async def start(self) -> None:
        if self.started:
            return
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(
            headless=settings.BROWSER_HEADLESS
        )
        context = await self._browser.new_context(
            user_agent=settings.BROWSER_USER_AGENT,
            viewport={"width": 1280, "height": 800},
        )
        context.set_default_timeout(settings.BROWSER_NAV_TIMEOUT_MS)
        self._page = await context.new_page()
        self.started = True

    async def open(self, url: str) -> None:
        await self._page.goto(url, wait_until="domcontentloaded")
        await self._page.wait_for_timeout(settings.BROWSER_SETTLE_MS)

    async def observe(self) -> dict:
        """Snapshot the current page: url, title, visible text, elements."""
        page = self._page
        title = await page.title()
        text = await page.inner_text("body")
        elements = await page.evaluate(
            _COLLECT_ELEMENTS_JS, settings.BROWSER_MAX_ELEMENTS
        )
        return {
            "url": page.url,
            "title": title,
            "text": (text or "")[: settings.BROWSER_TEXT_LIMIT],
            "elements": elements,
        }

    async def click(self, agent_id: int) -> str:
        sel = f'[data-agent-id="{agent_id}"]'
        await self._page.click(sel, timeout=settings.BROWSER_NAV_TIMEOUT_MS)
        await self._page.wait_for_timeout(settings.BROWSER_SETTLE_MS)
        return f"clicked element #{agent_id}"

    async def type(self, agent_id: int, value: str) -> str:
        sel = f'[data-agent-id="{agent_id}"]'
        await self._page.fill(sel, value)
        return f"typed into element #{agent_id}"

    async def press_enter(self) -> str:
        await self._page.keyboard.press("Enter")
        await self._page.wait_for_timeout(settings.BROWSER_SETTLE_MS)
        return "pressed Enter"

    async def scroll(self) -> str:
        await self._page.mouse.wheel(0, 1200)
        await self._page.wait_for_timeout(600)
        return "scrolled down"

    async def screenshot(self) -> bytes:
        return await self._page.screenshot(full_page=False)

    async def close(self) -> None:
        try:
            if self._browser:
                await self._browser.close()
        finally:
            if self._pw:
                await self._pw.stop()
            self.started = False


# --- registry --------------------------------------------------------------

_SESSIONS: dict[str, BrowserSession] = {}


async def get_or_create_session(thread_id: str) -> BrowserSession:
    session = _SESSIONS.get(thread_id)
    if session is None:
        session = BrowserSession(thread_id=thread_id)
        await session.start()
        _SESSIONS[thread_id] = session
    return session


def get_session(thread_id: str) -> BrowserSession | None:
    return _SESSIONS.get(thread_id)


async def close_session(thread_id: str) -> None:
    session = _SESSIONS.pop(thread_id, None)
    if session:
        await session.close()
