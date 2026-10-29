import sys
import urllib.parse
from pathlib import Path

# Add project root directory to sys.path so modules like agent and web resolve cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from web.app import app as original_app

async def app(scope, receive, send):
    """
    ASGI Middleware to normalize paths rewritten by Vercel serverless functions.
    Restores the exact requested path from query param '__path=$1' or 'x-forwarded-uri'.
    """
    try:
        if scope.get("type") == "http":
            qs = scope.get("query_string", b"")
            if isinstance(qs, bytes):
                qs_str = qs.decode("latin1")
            else:
                qs_str = str(qs)
            params = urllib.parse.parse_qs(qs_str)
            
            # 1. Primary: Extract from __path=$1 injected by vercel.json rewrite
            if "__path" in params:
                captured = params["__path"][0]
                clean_path = "/" + captured.lstrip("/")
                scope["path"] = clean_path
                scope["raw_path"] = clean_path.encode("ascii")
                
                # Clean up query string so application doesn't see __path internal param
                clean_params = {k: v for k, v in params.items() if k != "__path"}
                scope["query_string"] = urllib.parse.urlencode(clean_params, doseq=True).encode("latin1")
                
            else:
                # 2. Fallback: Check Vercel proxy headers
                headers = {k.decode("latin1").lower() if isinstance(k, bytes) else str(k).lower(): v.decode("latin1") if isinstance(v, bytes) else str(v) for k, v in scope.get("headers", [])}
                orig_uri = headers.get("x-forwarded-uri") or headers.get("x-original-url")
                if orig_uri and not orig_uri.startswith("/api/index"):
                    clean = orig_uri.split("?")[0]
                    scope["path"] = clean
                    scope["raw_path"] = clean.encode("ascii")
                else:
                    # 3. Fallback: Strip /api/index.py or /api/index prefix
                    path = scope.get("path", "")
                    for prefix in ("/api/index.py", "/api/index"):
                        if path.startswith(prefix):
                            normalized = path[len(prefix):]
                            clean = normalized if normalized.startswith("/") else ("/" + normalized if normalized else "/")
                            scope["path"] = clean
                            scope["raw_path"] = clean.encode("ascii")
                            break

        await original_app(scope, receive, send)
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        body = f"ASGI Handler Error: {e}\n\n{tb}".encode("utf-8")
        await send({
            "type": "http.response.start",
            "status": 500,
            "headers": [
                [b"content-type", b"text/plain; charset=utf-8"],
                [b"content-length", str(len(body)).encode("ascii")]
            ]
        })
        await send({
            "type": "http.response.body",
            "body": body
        })
