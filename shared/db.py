"""shared/db.py — Supabase client factory shared across applications.

Extracted from duplicate client-construction code in venture-studio's
save_idea.py and weekly_digest.py (see docs/adr/0001-personal-ai-os-philosophy.md).
"""

import os
import sys
import json


def get_client():
    """Return a configured Supabase client, or exit with a JSON error if unconfigured."""
    try:
        from supabase import create_client, Client
    except ImportError:
        print(json.dumps({"error": "supabase-py not installed. Run: pip install supabase"}))
        sys.exit(1)

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print(json.dumps({"error": "SUPABASE_URL and SUPABASE_KEY must be set in ~/.hermes/.env"}))
        sys.exit(1)

    return create_client(url, key)
