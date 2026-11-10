"""raw-ask scripts をテストから import できるよう scripts/ を sys.path に載せる。"""
import pathlib
import sys

_SCRIPTS = pathlib.Path(__file__).resolve().parent.parent / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))
