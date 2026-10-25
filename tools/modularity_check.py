"""Enforcement delle regole di AGENTS.md.

Verifica: R1 (budget), R2 (radice), R3 (dati nel codice), R5 (layer), R8/R10 (mappa),
R11 (segreti e path assoluti), R12 (import da legacy), R13 (print, hack stdout).

    py tools/modularity_check.py              # src, tools, tests
    py tools/modularity_check.py --strict     # warning = errori
    py tools/modularity_check.py --audit-all  # + legacy/ e app Gen 2, con audit segreti
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CODE_ZONES = ("src", "tools", "tests")
AUDIT_ZONES = ("legacy", "conversione gemini")
DOC_ZONE = "docs"
MODULE_MAP = ROOT / "docs" / "MODULE_MAP.md"

FILE_WARN, FILE_ERROR = 300, 450
FUNC_WARN, FUNC_ERROR = 50, 80
DEFS_WARN, DEFS_ERROR = 12, 16
DOC_WARN, DOC_ERROR = 400, 600
DATA_STRING_LEN, DATA_STRING_MAX = 200, 3

# Pattern composti a runtime: il file non deve contenere chiavi "in chiaro"
# nemmeno come esempio, altrimenti violerebbe il proprio controllo R11.
SECRET_PATTERNS = (
    ("sk" + "-ant-", "chiave Anthropic"),
    ("sk" + "-[A-Za-z0-9]{24,}", "chiave OpenAI/DeepSeek"),
    ("AI" + "za[0-9A-Za-z_-]{30,}", "chiave Google"),
    ("gh" + "p_[A-Za-z0-9]{30,}", "token GitHub"),
)
CONFIG_GLOBS = ("*.json", "*.md", "*.toml", "*.yml", "*.yaml", ".env*")
SKIP_DIRS = {"build", "dist", "node_modules", "test_output", "__pycache__", ".git", ".venv"}

ABS_PATH_RE = re.compile(r"[A-Za-z]:\\\\?Users\\\\?|/home/[a-z]|/Users/[A-Za-z]")
STDOUT_HACK_RE = re.compile(r"sys\.stdout\s*=\s*io\.TextIOWrapper")
PRINT_ALLOWED_PREFIXES = ("tools/", "src/pdfbook/gui/", "src/pdfbook/cli.py")

_ALL_DOMAIN = {"domain", "config", "qa", "extraction", "fonts", "layout",
               "translation", "rendering"}
LAYER_ALLOWED = {
    "domain": set(),
    "config": {"domain"},
    "qa": {"domain", "config"},
    "extraction": {"domain"},
    "fonts": {"domain"},
    "layout": {"domain", "fonts"},
    "translation": {"domain", "config"},
    "rendering": {"domain", "fonts", "layout", "qa"},
    "app": set(_ALL_DOMAIN),
    "gui": set(_ALL_DOMAIN) | {"app", "gui"},
    "cli": set(_ALL_DOMAIN) | {"app", "cli"},
}


@dataclass
class Issue:
    level: str
    rule: str
    where: str
    line: int
    message: str


@dataclass
class Report:
    issues: list[Issue] = field(default_factory=list)
    scanned: int = 0

    def add(self, level: str, rule: str, where: str, line: int, message: str) -> None:
        self.issues.append(Issue(level, rule, where, line, message))

    def by_rule(self) -> dict[str, list[Issue]]:
        grouped: dict[str, list[Issue]] = {}
        for issue in self.issues:
            grouped.setdefault(f"{issue.level}/{issue.rule}", []).append(issue)
        return grouped


class Checker:
    """Un metodo per regola: nessuna funzione lunga, nessun effetto globale."""

    def __init__(self, audit_all: bool, with_secrets: bool) -> None:
        self.audit_all = audit_all
        self.with_secrets = with_secrets
        self.rep = Report()

    # ---------- utilità ----------

    @staticmethod
    def rel(path: Path) -> str:
        return path.relative_to(ROOT).as_posix()

    @staticmethod
    def layer_of(relpath: str) -> str | None:
        parts = relpath.split("/")
        if len(parts) > 3 and parts[0] == "src" and parts[1] == "pdfbook":
            return parts[2]
        return None

    def python_files(self, zones: tuple[str, ...]) -> list[Path]:
        files: list[Path] = []
        for zone in zones:
            base = ROOT / zone
            if base.exists():
                files.extend(sorted(base.rglob("*.py")))
        return files

    def config_files(self) -> list[Path]:
        found: set[Path] = set()
        for pattern in CONFIG_GLOBS:
            for path in ROOT.rglob(pattern):
                if set(path.relative_to(ROOT).parts[:-1]) & SKIP_DIRS:
                    continue
                found.add(path)
        return sorted(found)

    # ---------- R1: budget ----------

    def check_sizes(self, path: Path, name: str) -> None:
        lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        if lines > FILE_ERROR:
            self.rep.add("ERROR", "R1", name, 1, f"{lines} righe (limite {FILE_ERROR})")
        elif lines > FILE_WARN:
            self.rep.add("WARN", "R1", name, 1, f"{lines} righe (target {FILE_WARN})")

    # ---------- R1/R3/R5/R12/R13 via AST ----------

    def check_ast(self, name: str, tree: ast.AST) -> None:
        layer = self.layer_of(name)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.check_def_size(name, node)
            elif isinstance(node, ast.ImportFrom) and node.module:
                self.check_import(name, layer, node)
            elif isinstance(node, ast.Name) and node.id == "print":
                self.check_print(name, layer, node)
        self.check_top_level_defs(name, tree)
        self.check_inline_data(name, tree)

    def check_def_size(self, name: str, node: ast.AST) -> None:
        """Il budget 50/80 riguarda funzioni e metodi; le classi seguono il budget di file."""
        if isinstance(node, ast.ClassDef):
            return
        length = (node.end_lineno or node.lineno) - node.lineno + 1
        label = getattr(node, "name", "?")
        if length > FUNC_ERROR:
            self.rep.add("ERROR", "R1", name, node.lineno, f"{label}: {length} righe")
        elif length > FUNC_WARN:
            self.rep.add("WARN", "R1", name, node.lineno, f"{label}: {length} righe")

    def check_import(self, name: str, layer: str | None, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if module.startswith("legacy") or ".legacy" in module:
            self.rep.add("ERROR", "R12", name, node.lineno, f"import da legacy: {module}")
            return
        if layer and module.startswith("pdfbook."):
            target = module.split(".")[1]
            if target not in LAYER_ALLOWED.get(layer, set()) | {layer}:
                self.rep.add("ERROR", "R5", name, node.lineno, f"{layer} -> {target}")

    def check_print(self, name: str, layer: str | None, node: ast.Name) -> None:
        if name.startswith(PRINT_ALLOWED_PREFIXES) or layer in ("cli", "gui"):
            return
        self.rep.add("WARN", "R13", name, node.lineno, "print nel codice")

    def check_top_level_defs(self, name: str, tree: ast.AST) -> None:
        top = [
            n for n in getattr(tree, "body", [])
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        if len(top) > DEFS_ERROR:
            self.rep.add("ERROR", "R1", name, 1, f"{len(top)} def top-level")
        elif len(top) > DEFS_WARN:
            self.rep.add("WARN", "R1", name, 1, f"{len(top)} def top-level")

    def check_inline_data(self, name: str, tree: ast.AST) -> None:
        literals = [
            n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
            and len(n.value) > DATA_STRING_LEN
        ]
        if len(literals) > DATA_STRING_MAX:
            self.rep.add("ERROR", "R3", name, 1,
                         f"{len(literals)} stringhe > {DATA_STRING_LEN} caratteri: dati nel codice?")

    # ---------- R11/R13 via testo ----------

    def check_text(self, name: str, text: str, secrets: bool, abs_paths: bool = True) -> None:
        for lineno, line in enumerate(text.splitlines(), start=1):
            if secrets:
                self.check_secret(name, lineno, line)
            if abs_paths and ABS_PATH_RE.search(line):
                self.rep.add("WARN", "R11", name, lineno, "percorso assoluto utente")
            if name.endswith(".py") and STDOUT_HACK_RE.search(line):
                self.rep.add("ERROR", "R13", name, lineno, "hack sys.stdout")

    def check_secret(self, name: str, lineno: int, line: str) -> None:
        for pattern, what in SECRET_PATTERNS:
            if re.search(pattern, line):
                self.rep.add("ERROR", "R11", name, lineno, f"{what} in chiaro")

    # ---------- R8/R10: mappa ----------

    def check_map(self) -> None:
        if not MODULE_MAP.exists():
            self.rep.add("ERROR", "R10", "docs/MODULE_MAP.md", 1, "mappa assente")
            return
        text = MODULE_MAP.read_text(encoding="utf-8")
        for path in self.python_files(("src",)):
            name = self.rel(path)
            if path.name != "__init__.py" and name not in text:
                self.rep.add("ERROR", "R8", name, 1, "modulo non registrato in MODULE_MAP")

    # ---------- R2/R8: luoghi canonici ----------

    def check_root_python(self) -> None:
        for path in sorted(ROOT.glob("*.py")):
            self.rep.add("WARN", "R2", path.name, 1, "codice alla radice: spostare in legacy/")

    def check_docs(self) -> None:
        base = ROOT / DOC_ZONE
        if not base.exists():
            return
        for path in sorted(base.rglob("*.md")):
            lines = len(path.read_text(encoding="utf-8", errors="replace").splitlines())
            level = "ERROR" if lines > DOC_ERROR else "WARN" if lines > DOC_WARN else None
            if level:
                self.rep.add(level, "R8", self.rel(path), 1, f"{lines} righe (target {DOC_WARN})")

    # ---------- orchestrazione ----------

    def run(self) -> Report:
        zones = CODE_ZONES + (AUDIT_ZONES if self.audit_all else ())
        for path in self.python_files(zones):
            self.rep.scanned += 1
            name = self.rel(path)
            self.check_sizes(path, name)
            tree = self.parse(name, path)
            if tree is not None:
                self.check_ast(name, tree)
            self.check_text(name, path.read_text(encoding="utf-8", errors="replace"), self.with_secrets)
        if self.audit_all and self.with_secrets:
            for path in self.config_files():
                self.rep.scanned += 1
                text = path.read_text(encoding="utf-8", errors="replace")
                self.check_text(self.rel(path), text, secrets=True, abs_paths=False)
        self.check_map()
        self.check_root_python()
        self.check_docs()
        return self.rep

    def parse(self, name: str, path: Path) -> ast.AST | None:
        try:
            return ast.parse(path.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError as exc:
            self.rep.add("ERROR", "R1", name, exc.lineno or 1, f"sintassi non valida: {exc.msg}")
            return None


def render(rep: Report) -> None:
    """Stampa il report: massimo 5 esempi per regola, conteggi completi."""
    errors = sum(1 for i in rep.issues if i.level == "ERROR")
    warns = sum(1 for i in rep.issues if i.level == "WARN")
    print(f"== modularity_check == file analizzati: {rep.scanned} | "
          f"errori: {errors} | warning: {warns}")
    for key in sorted(rep.by_rule(), key=lambda k: (not k.startswith("ERROR"), k)):
        issues = rep.by_rule()[key]
        print(f"\n-- {key}: {len(issues)}")
        for issue in issues[:5]:
            print(f"   {issue.where}:{issue.line}  {issue.message}")
        if len(issues) > 5:
            print(f"   ... e altri {len(issues) - 5}")
    if not rep.issues:
        print("\nNessuna violazione: struttura conforme ad AGENTS.md.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verifica le regole di AGENTS.md")
    parser.add_argument("--strict", action="store_true", help="warning = errore")
    parser.add_argument("--audit-all", action="store_true", help="include legacy/ e app Gen 2")
    parser.add_argument("--no-secrets", action="store_true", help="salta il controllo chiavi")
    args = parser.parse_args(argv)
    rep = Checker(audit_all=args.audit_all, with_secrets=not args.no_secrets).run()
    render(rep)
    failed = any(i.level == "ERROR" for i in rep.issues) or (
        args.strict and any(i.level == "WARN" for i in rep.issues)
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
