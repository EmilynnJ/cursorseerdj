"""
Netlify serverless function — wraps the Django WSGI application.

Netlify Functions execute as AWS Lambda-compatible handlers, so we use
serverless-wsgi to translate the Lambda event/context interface into a
WSGI environ that Django understands.

Limitations on Netlify vs Fly.io:
  - No persistent processes: Celery workers (billing ticks, session
    finalization) must continue to run on Fly.io or another platform.
  - Default function timeout is 10 s (26 s on Pro). Long-running admin
    operations should be offloaded to Celery tasks rather than blocking
    HTTP responses.
  - Cold-start latency on first request (~1-2 s); use Netlify's
    "On-demand Builders" or keep-alive pings to reduce it.
"""

import os
import sys

# Ensure the project root is on the path so all Django apps are importable
_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _root not in sys.path:
    sys.path.insert(0, _root)

# Tell Django which settings module to use (also set in netlify.toml)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "soulseer.settings")

# Netlify terminates TLS at the edge and forwards requests as HTTP internally,
# setting the x-forwarded-proto header to "https". Django needs to know this
# so SECURE_SSL_REDIRECT does not loop and CSRF/session cookies are marked
# secure. (SECURE_PROXY_SSL_HEADER is set in settings.py.)

import serverless_wsgi  # noqa: E402  (installed via requirements.txt)
from soulseer.wsgi import application  # noqa: E402


def handler(event, context):
    """Entry point called by the Netlify / Lambda runtime."""
    return serverless_wsgi.handle_request(application, event, context)
