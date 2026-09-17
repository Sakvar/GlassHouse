"""Single deployment bootstrap; worker starts after API readiness."""
import os
import subprocess
import sys

subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], check=True)
os.execv(sys.executable, [sys.executable, '-m', 'uvicorn', 'apps.api.main:app',
                         '--host', '0.0.0.0', '--port', '8000', '--no-proxy-headers'])
