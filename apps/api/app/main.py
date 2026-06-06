"""Entrypoint: `python -m app.main` or `uvicorn app.server:app`."""
import uvicorn

from app.server import app  # noqa: F401  (exported for `uvicorn app.main:app`)

if __name__ == "__main__":
    uvicorn.run("app.server:app", host="0.0.0.0", port=8000, reload=True)
