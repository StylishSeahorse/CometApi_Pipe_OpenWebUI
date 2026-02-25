#!/usr/bin/env python3
"""
Open WebUI CometAPI Pipe Loader with GitHub auto-download support.

This loader automatically downloads the bundled CometAPI pipe from GitHub,
caches it locally, and imports it into Open WebUI.

Features:
  - Auto-downloads from GitHub on first use
  - Caches locally to minimize network requests
  - Falls back to local copy if GitHub is unavailable
  - Validates module integrity

Configuration:
  - GITHUB_REPO: GitHub repository URL
  - CACHE_DIR: Local cache directory (defaults to ~/.cache/open-webui)
  - GITHUB_RAW_URL: Direct raw GitHub URL for the bundled file
"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional
import urllib.request
import urllib.error

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
GITHUB_REPO = "https://github.com/StylishSeahorse/CometApi_Pipe_OpenWebUI"
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/StylishSeahorse/CometApi_Pipe_OpenWebUI/main"
BUNDLED_FILENAME = "open_webui_cometapi_pipe_bundled.py"
CACHE_DIR = Path.home() / ".cache" / "open-webui-cometapi"
CACHE_FILE = CACHE_DIR / BUNDLED_FILENAME
METADATA_FILE = CACHE_DIR / ".metadata.json"

# URLs
GITHUB_DOWNLOAD_URL = f"{GITHUB_RAW_BASE}/{BUNDLED_FILENAME}"


def _ensure_cache_dir() -> Path:
    """Create cache directory if it doesn't exist."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def _download_from_github() -> Optional[str]:
    """Download the bundled module from GitHub and cache it locally."""
    logger.info(f"📥 Downloading CometAPI pipe from GitHub: {GITHUB_DOWNLOAD_URL}")
    
    try:
        _ensure_cache_dir()
        
        # Download with a timeout
        with urllib.request.urlopen(GITHUB_DOWNLOAD_URL, timeout=30) as response:
            content = response.read().decode('utf-8')
        
        # Save to cache
        CACHE_FILE.write_text(content, encoding='utf-8')
        
        # Update metadata
        metadata = {
            "source": "github",
            "url": GITHUB_DOWNLOAD_URL,
            "timestamp": str(Path.cwd()),
        }
        METADATA_FILE.write_text(json.dumps(metadata), encoding='utf-8')
        
        logger.info(f"✅ Successfully cached CometAPI pipe to {CACHE_FILE}")
        return str(CACHE_FILE)
        
    except urllib.error.URLError as e:
        logger.warning(f"⚠️ Failed to download from GitHub: {e}")
        return None
    except Exception as e:
        logger.warning(f"⚠️ Unexpected error during download: {e}")
        return None


def _load_cached_module() -> Optional[str]:
    """Load the cached bundled module if it exists."""
    if CACHE_FILE.exists():
        logger.info(f"📦 Using cached CometAPI pipe from {CACHE_FILE}")
        return str(CACHE_FILE)
    return None


def _get_bundled_module_path() -> str:
    """Get the path to the bundled module, downloading from GitHub if needed."""
    # Prefer local file first so local fixes are used immediately.
    local_path = Path(__file__).parent / BUNDLED_FILENAME
    if local_path.exists():
        logger.info(f"📄 Using local bundled module from {local_path}")
        return str(local_path)

    # Then try cached version.
    cached_path = _load_cached_module()
    if cached_path:
        return cached_path
    
    # Try to download from GitHub
    logger.info("No cached version found, attempting to download from GitHub...")
    github_path = _download_from_github()
    if github_path:
        return github_path
    
    # Error: can't find the module anywhere
    raise FileNotFoundError(
        f"Could not find CometAPI bundled module:\n"
        f"  - GitHub download failed\n"
        f"  - No cached copy at {CACHE_FILE}\n"
        f"  - No local copy at {local_path}\n"
        f"\nPlease check your internet connection or download manually from:\n"
        f"  {GITHUB_REPO}"
    )


def _import_bundled_module():
    """Dynamically import the bundled module from its path."""
    module_path = _get_bundled_module_path()
    
    # Add the parent directory to sys.path
    module_dir = str(Path(module_path).parent)
    if module_dir not in sys.path:
        sys.path.insert(0, module_dir)
    
    # Import the module
    try:
        import open_webui_cometapi_pipe_bundled
        logger.info("✅ Successfully imported CometAPI pipe module")
        return open_webui_cometapi_pipe_bundled
    except ImportError as e:
        logger.error(f"❌ Failed to import CometAPI pipe: {e}")
        raise


# Lazy import and export
_module = None

def _get_module():
    """Lazy-load the module on first access."""
    global _module
    if _module is None:
        _module = _import_bundled_module()
    return _module


def __getattr__(name: str):
    """Dynamically export Pipe, Valves, and UserValves on first access."""
    module = _get_module()
    return getattr(module, name)


__all__ = ["Pipe", "Valves", "UserValves"]


if __name__ == "__main__":
    """Validation and test script."""
    print("\n" + "="*60)
    print("Open WebUI CometAPI Pipe - GitHub Loader Validation")
    print("="*60 + "\n")
    
    try:
        # Trigger the module load
        module = _get_module()
        
        print(f"✅ Module loaded successfully from: {_get_bundled_module_path()}\n")
        
        # Show available exports
        print("Available exports:")
        for name in __all__:
            obj = getattr(module, name)
            print(f"  • {name}: {obj}")
        
        print("\n" + "="*60)
        print("✅ Validation successful! Ready to use with Open WebUI")
        print("="*60 + "\n")
        
        # Show cache info
        if CACHE_FILE.exists():
            size_kb = CACHE_FILE.stat().st_size / 1024
            print(f"📦 Cached file: {CACHE_FILE} ({size_kb:.1f} KB)")
        
    except Exception as e:
        print(f"\n❌ Validation failed: {e}\n")
        sys.exit(1)
