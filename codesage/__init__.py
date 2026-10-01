"""CodeSage — static-analysis code reviewer for Python.

Analyzes Python source code using the ``ast`` module to compute cyclomatic
complexity, detect code smells, and produce severity-ranked findings with
Markdown/HTML reports.
"""

from .analyzer import analyze_file, analyze_path
from .models import Finding, FunctionMetrics, FileReport

__version__ = "1.0.0"
__all__ = [
    "analyze_file",
    "analyze_path",
    "Finding",
    "FunctionMetrics",
    "FileReport",
    "__version__",
]
