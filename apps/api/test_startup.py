#!/usr/bin/env python
"""Test script to verify FastAPI server starts correctly."""

import subprocess
import time
import sys
import os
from pathlib import Path

# Add the api directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


def test_import():
    """Test that the app can be imported."""
    print("Testing app import...")
    try:
        from main import app
        print("✓ App imported successfully")
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_startup():
    """Test that the server starts."""
    print("\nStarting test server on http://localhost:8000...")

    # Start uvicorn
    env = os.environ.copy()
    env["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:8000"

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )

    # Wait for server to start
    time.sleep(3)

    # Check if process is still running
    if proc.poll() is not None:
        stdout, stderr = proc.communicate()
        print(f"✗ Server failed to start")
        if stdout:
            print(f"STDOUT:\n{stdout}")
        if stderr:
            print(f"STDERR:\n{stderr}")
        return False

    print("✓ Server started successfully")

    # Test health endpoint
    print("\nTesting health endpoint...")
    try:
        import urllib.request
        response = urllib.request.urlopen("http://localhost:8000/health", timeout=5)
        data = response.read().decode()
        print(f"✓ Health endpoint responded: {data}")

        # Clean up
        proc.terminate()
        proc.wait(timeout=5)
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("EDGP FastAPI Server Startup Test")
    print("=" * 60)

    if not test_import():
        sys.exit(1)

    if not test_startup():
        sys.exit(1)

    print("\n" + "=" * 60)
    print("All tests passed! Server is ready.")
    print("=" * 60)
    print("\nTo run the server normally:")
    print("  cd apps/api")
    print("  uvicorn main:app --reload")
    print("\nThen visit:")
    print("  http://localhost:8000/docs")
