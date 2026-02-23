"""
Static code analyzer — extracts structure from source files without imports.

Uses AST parsing for Python, regex patterns for JS/TS.
"""

import ast
import re
from pathlib import Path
from typing import List, Dict, Any, Optional


# Directories to always exclude
EXCLUDE_DIRS = {
    "venv", ".venv", "env", ".env", "node_modules", "__pycache__",
    ".git", ".graphbus", ".tox", ".mypy_cache", ".pytest_cache",
    "dist", "build", "egg-info", ".eggs", ".hg", ".svn",
}

# File patterns to exclude
EXCLUDE_PATTERNS = {
    "setup.py", "conftest.py", "manage.py",
}


def detect_language(project_path: Path) -> str:
    """Detect the primary language of a project."""
    project_path = Path(project_path)

    # Check for language-specific markers
    if (project_path / "package.json").exists():
        # Check if it's TypeScript
        ts_files = list(project_path.rglob("*.ts"))
        if ts_files or (project_path / "tsconfig.json").exists():
            return "typescript"
        return "javascript"

    if (project_path / "pyproject.toml").exists() or (project_path / "setup.py").exists():
        return "python"

    # Count files by extension
    py_count = len(list(project_path.rglob("*.py")))
    js_count = len(list(project_path.rglob("*.js"))) + len(list(project_path.rglob("*.ts")))

    if py_count >= js_count:
        return "python"
    return "javascript"


def _load_gitignore_patterns(project_path: Path) -> List[str]:
    """Load patterns from .gitignore."""
    gitignore = project_path / ".gitignore"
    if not gitignore.exists():
        return []

    patterns = []
    for line in gitignore.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            # Normalize: remove trailing /
            patterns.append(line.rstrip("/"))
    return patterns


def _is_excluded(path: Path, project_path: Path, gitignore_patterns: List[str]) -> bool:
    """Check if a path should be excluded."""
    rel = path.relative_to(project_path)

    # Check directory exclusions
    for part in rel.parts:
        if part in EXCLUDE_DIRS:
            return True

    # Check gitignore patterns (simple implementation)
    rel_str = str(rel)
    for pattern in gitignore_patterns:
        # Direct match on any path component
        if pattern in rel.parts:
            return True
        # Prefix match
        if rel_str.startswith(pattern):
            return True

    return False


def scan_source_files(project_path: Path) -> List[Path]:
    """
    Scan project directory for source files, respecting .gitignore and exclusions.

    Returns list of source file paths (excludes __init__.py, tests, etc.)
    """
    project_path = Path(project_path)
    gitignore_patterns = _load_gitignore_patterns(project_path)

    language = detect_language(project_path)
    if language == "python":
        extensions = {".py"}
    else:
        extensions = {".js", ".ts", ".jsx", ".tsx"}

    files = []
    for ext in extensions:
        for f in project_path.rglob(f"*{ext}"):
            if _is_excluded(f, project_path, gitignore_patterns):
                continue
            # Skip __init__.py, test files, and excluded patterns
            if f.name == "__init__.py":
                continue
            if f.name.startswith("test_") or f.name.endswith("_test.py"):
                continue
            if f.name in EXCLUDE_PATTERNS:
                continue
            files.append(f)

    return sorted(files)


def extract_symbols(file_path: Path) -> List[Dict[str, Any]]:
    """
    Extract symbols (functions, classes, methods) from a source file using AST.

    Returns list of symbol dicts with: name, type, params, docstring, decorators, file
    """
    file_path = Path(file_path)
    source = file_path.read_text(encoding="utf-8", errors="replace")

    if file_path.suffix == ".py":
        return _extract_python_symbols(source, str(file_path))
    elif file_path.suffix in (".js", ".ts", ".jsx", ".tsx"):
        return _extract_js_symbols(source, str(file_path))
    return []


def _extract_python_symbols(source: str, file_path: str) -> List[Dict[str, Any]]:
    """Extract symbols from Python source using AST."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    symbols = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            symbols.append(_python_func_to_symbol(node, file_path))
        elif isinstance(node, ast.ClassDef):
            class_symbol = {
                "name": node.name,
                "type": "class",
                "params": {},
                "docstring": ast.get_docstring(node) or "",
                "decorators": [_decorator_name(d) for d in node.decorator_list],
                "methods": [],
                "file": file_path,
            }
            # Extract methods
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method = _python_func_to_symbol(item, file_path)
                    method["type"] = "method"
                    class_symbol["methods"].append(method)

            symbols.append(class_symbol)

    return symbols


def _python_func_to_symbol(node, file_path: str) -> Dict[str, Any]:
    """Convert a Python AST function node to a symbol dict."""
    params = {}
    for arg in node.args.args:
        if arg.arg == "self":
            continue
        annotation = ""
        if arg.annotation:
            if isinstance(arg.annotation, ast.Name):
                annotation = arg.annotation.id
            elif isinstance(arg.annotation, ast.Constant):
                annotation = str(arg.annotation.value)
            elif isinstance(arg.annotation, ast.Attribute):
                annotation = ast.dump(arg.annotation)
        params[arg.arg] = annotation or "Any"

    return {
        "name": node.name,
        "type": "function",
        "params": params,
        "docstring": ast.get_docstring(node) or "",
        "decorators": [_decorator_name(d) for d in node.decorator_list],
        "file": file_path,
    }


def _decorator_name(node) -> str:
    """Get decorator name as string."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{ast.dump(node)}"
    elif isinstance(node, ast.Call):
        return _decorator_name(node.func)
    return ""


def _extract_js_symbols(source: str, file_path: str) -> List[Dict[str, Any]]:
    """Extract symbols from JS/TS source using regex (best-effort)."""
    symbols = []

    # Match function declarations and exports
    func_pattern = re.compile(
        r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)',
        re.MULTILINE
    )
    for m in func_pattern.finditer(source):
        params = {}
        for param in m.group(2).split(","):
            param = param.strip()
            if param:
                parts = param.split(":")
                name = parts[0].strip().lstrip("?")
                ptype = parts[1].strip() if len(parts) > 1 else "any"
                params[name] = ptype
        symbols.append({
            "name": m.group(1),
            "type": "function",
            "params": params,
            "docstring": "",
            "decorators": [],
            "file": file_path,
        })

    # Match class declarations
    class_pattern = re.compile(
        r'(?:export\s+)?class\s+(\w+)',
        re.MULTILINE
    )
    for m in class_pattern.finditer(source):
        symbols.append({
            "name": m.group(1),
            "type": "class",
            "params": {},
            "docstring": "",
            "decorators": [],
            "methods": [],
            "file": file_path,
        })

    # Match arrow function exports: export const foo = (...) =>
    arrow_pattern = re.compile(
        r'(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(([^)]*)\)\s*(?::\s*\w+\s*)?=>',
        re.MULTILINE
    )
    for m in arrow_pattern.finditer(source):
        params = {}
        for param in m.group(2).split(","):
            param = param.strip()
            if param:
                parts = param.split(":")
                name = parts[0].strip()
                ptype = parts[1].strip() if len(parts) > 1 else "any"
                params[name] = ptype
        symbols.append({
            "name": m.group(1),
            "type": "function",
            "params": params,
            "docstring": "",
            "decorators": [],
            "file": file_path,
        })

    return symbols


def extract_imports(file_path: Path) -> List[str]:
    """Extract import statements from a source file."""
    file_path = Path(file_path)
    source = file_path.read_text(encoding="utf-8", errors="replace")

    if file_path.suffix == ".py":
        return _extract_python_imports(source)
    elif file_path.suffix in (".js", ".ts", ".jsx", ".tsx"):
        return _extract_js_imports(source)
    return []


def _extract_python_imports(source: str) -> List[str]:
    """Extract Python imports using AST."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return imports


def _extract_js_imports(source: str) -> List[str]:
    """Extract JS/TS imports using regex."""
    imports = []
    pattern = re.compile(r"(?:import|require)\s*\(?['\"]([^'\"]+)['\"]", re.MULTILINE)
    for m in pattern.finditer(source):
        imports.append(m.group(1))
    return imports
