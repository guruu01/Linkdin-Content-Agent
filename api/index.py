import sys
from pathlib import Path

# Add project root directory to sys.path so modules like agent and web resolve cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from web.app import app as original_app

async def app(scope, receive, send):
    """
    ASGI Middleware to normalize paths rewritten by Vercel serverless functions.
    Removes '/api/index.py' or '/api/index' prefixes injected by Vercel rewrites.
    """
    if scope.get("type") == "http":
        path = scope.get("path", "")
        for prefix in ("/api/index.py", "/api/index"):
            if path.startswith(prefix):
                normalized = path[len(prefix):]
                scope["path"] = normalized if normalized.startswith("/") else ("/" + normalized if normalized else "/")
                break
    await original_app(scope, receive, send)
