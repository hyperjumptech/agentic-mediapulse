"""Shared test setup.

Importing the agent modules constructs the whole agent graph (LLM clients, skills
provider) at import time, so dummy credentials must exist before any test imports them.
These are set here, before collection imports the source packages. No network call is
made at construction time, so placeholder values are enough.
"""

import os

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("OPENAI_BASE_URL", "https://example.invalid/v1")
os.environ.setdefault("SERPER_API_KEY", "test-serper-key")
os.environ.setdefault("RESEND_API_KEY", "test-resend-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
