import sys
print("Python executable:", sys.executable)
print("Python version:", sys.version)
print("Python path:", sys.path)
print()

try:
    import click
    print("✅ Click installed:", click.__file__)
    print("   Click version:", click.__version__)
except ImportError as e:
    print("❌ Click NOT installed:", e)

try:
    import torch
    print("✅ Torch installed")
except ImportError:
    print("❌ Torch NOT installed")

try:
    import flask
    print("✅ Flask installed")
except ImportError:
    print("❌ Flask NOT installed")

try:
    from src.cli import cli
    print("✅ CLI module can be imported")
except Exception as e:
    print("❌ CLI import error:", e)