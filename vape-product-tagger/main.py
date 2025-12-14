"""
Wrapper module to allow importing ControlledTagger from tests.
This module re-exports the main tagging class from scripts/1_main.py
"""
import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

# Import from 1_main.py using importlib to handle the numeric prefix
import importlib.util
spec = importlib.util.spec_from_file_location("main_module", str(scripts_dir / "1_main.py"))
main_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(main_module)

# Re-export the class
ControlledTagger = main_module.ControlledTagger

__all__ = ['ControlledTagger']
