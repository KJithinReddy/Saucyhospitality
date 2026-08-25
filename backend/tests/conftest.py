import os

os.environ["OPENROUTER_API_KEY"] = ""

from app.main import app  # noqa: F401, E402
