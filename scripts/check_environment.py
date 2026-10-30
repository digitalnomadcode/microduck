"""Report the local tools used for CPU-only MuJoCo checks."""

import platform
import shutil
import sys

import mujoco


def main() -> None:
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"MuJoCo: {mujoco.__version__}")
    print(f"Windows: {platform.platform()}")
    print(f"Git: {shutil.which('git') or 'not found in PATH'}")
    print(f"VS Code CLI: {shutil.which('code') or 'not found in PATH'}")


if __name__ == "__main__":
    main()
