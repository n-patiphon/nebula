#!/usr/bin/env python3

import argparse
import ast
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _parse_python_call_args(args_src: str) -> tuple[list, dict]:
    expr = ast.parse(f"f({args_src})", mode="eval").body
    if not isinstance(expr, ast.Call):
        raise ValueError("unexpected AST (not a call)")

    def lit(node):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.List):
            return [lit(e) for e in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(lit(e) for e in node.elts)
        if isinstance(node, ast.Dict):
            return {lit(k): lit(v) for k, v in zip(node.keys, node.values)}
        raise ValueError(f"unsupported literal in macro args: {type(node).__name__}")

    positional = [lit(a) for a in expr.args]
    keywords = {}
    for kw in expr.keywords:
        if kw.arg is None:
            raise ValueError("**kwargs not supported in macro args")
        keywords[kw.arg] = lit(kw.value)
    return positional, keywords


_MACRO_RE = re.compile(
    r"\{\{\s*json_to_markdown\s*\((?P<args>.*?)\)\s*\}\}",
    flags=re.DOTALL,
)


def render_json_to_markdown_macros_in_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "{{" not in text or "json_to_markdown" not in text:
        return False

    from mkdocs_macros import json_to_markdown_impl

    def repl(match: re.Match) -> str:
        args_src = match.group("args")
        pos, kw = _parse_python_call_args(args_src)
        return str(json_to_markdown_impl(*pos, **kw))

    new_text, count = _MACRO_RE.subn(repl, text)
    if count == 0:
        return False

    path.write_text(new_text, encoding="utf-8")
    return True


def write_zensical_config(mkdocs_yml: Path, out_config: Path, docs_dir: str) -> None:
    # Keep mkdocs.yml as source of truth; write a derived config for Zensical that points to the
    # generated docs directory.
    lines = mkdocs_yml.read_text(encoding="utf-8").splitlines(keepends=True)
    wrote = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("docs_dir:"):
            indent = line[: len(line) - len(line.lstrip())]
            lines[i] = f"{indent}docs_dir: {docs_dir}\n"
            wrote = True
            break
    if not wrote:
        lines.insert(0, f"docs_dir: {docs_dir}\n")

    out_config.parent.mkdir(parents=True, exist_ok=True)
    out_config.write_text("".join(lines), encoding="utf-8")


def run_mkdocs_build_to_generate_mkdoxy(site_dir: Path) -> None:
    # mkdoxy runs as a MkDocs plugin and writes its generated pages into .mkdoxy/
    # (configured via mkdocs.yml). We only use MkDocs here as a generator step.
    subprocess.run(
        ["mkdocs", "build", "--site-dir", str(site_dir)],
        check=True,
        cwd=str(ROOT),
    )


def copy_tree(src: Path, dst: Path) -> None:
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a Zensical-compatible docs source tree from MkDocs sources."
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / ".zensical" / "docs"),
        help="Output directory for generated docs sources.",
    )
    parser.add_argument(
        "--config-out",
        default=str(ROOT / ".zensical" / "mkdocs.yml"),
        help="Output path for derived mkdocs.yml used by Zensical.",
    )
    parser.add_argument(
        "--mkdocs-yml",
        default=str(ROOT / "mkdocs.yml"),
        help="Path to source mkdocs.yml.",
    )
    parser.add_argument(
        "--skip-api",
        action="store_true",
        help="Skip mkdoxy/API generation (useful when doxygen isn't installed).",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    config_out = Path(args.config_out)
    mkdocs_yml = Path(args.mkdocs_yml)

    work_dir = out_dir.parent
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1) Generate mkdoxy pages into .mkdoxy/ (ignored) using MkDocs plugin.
    mkdocs_site_dir = work_dir / "_mkdocs_site"
    if not args.skip_api:
        run_mkdocs_build_to_generate_mkdoxy(mkdocs_site_dir)

    # 2) Assemble docs for Zensical.
    copy_tree(ROOT / "docs", out_dir)

    mkdoxy_dir = ROOT / ".mkdoxy"
    if mkdoxy_dir.exists():
        # Merge into the generated docs_dir so nav items like core/*.md resolve.
        for item in mkdoxy_dir.iterdir():
            target = out_dir / item.name
            if item.is_dir():
                if target.exists():
                    shutil.rmtree(target)
                shutil.copytree(item, target)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target)

    # 3) Expand json_to_markdown macros (keep macro syntax in source docs/).
    rendered = 0
    for md in out_dir.rglob("*.md"):
        try:
            if render_json_to_markdown_macros_in_file(md):
                rendered += 1
        except Exception as e:
            raise RuntimeError(f"Failed rendering macros in {md}: {e}") from e

    # 4) Write derived config for Zensical pointing at generated docs_dir.
    docs_dir_in_config = os.path.relpath(out_dir, start=ROOT)
    write_zensical_config(mkdocs_yml, config_out, docs_dir_in_config)

    print(f"Prepared Zensical docs source in {docs_dir_in_config} (rendered {rendered} file(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
