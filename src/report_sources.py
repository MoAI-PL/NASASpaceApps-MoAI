# Astrobalance — NASA Space Apps Challenge 2026
# AI-assisted: drafted with Claude (Anthropic), reviewed by the team. License: Apache-2.0
"""List every configuration entry as SOURCED or ASSUMPTION (markdown, for README → Data & sources).

Sources checked after the configs were frozen live in config/sources_extra.yaml (the frozen files
must not change); they are listed in a second table, and rows they confirm are marked in the first.

Usage:
    python -m src.report_sources > outputs/results/config_sources.md
"""

# ===== Imports =====
from __future__ import annotations

from src.common import CONFIG_DIR, load_yaml


# ===== Walk =====
def entries(node, path: str = ""):
    """Yield (path, value, status, note) for every leaf entry that carries a value."""
    if isinstance(node, dict):
        has_flag = "source" in node or "assumption" in node
        if has_flag:
            value = node.get("value", {k: v for k, v in node.items()
                                        if k not in ("source", "assumption", "note", "name", "unit", "role", "could")})
            status = "SOURCED" if node.get("source") else "ASSUMPTION"
            yield path, value, status, node.get("source") or node.get("note", "")
            return
        for key, child in node.items():
            yield from entries(child, f"{path}.{key}" if path else str(key))
    elif isinstance(node, list):
        for i, child in enumerate(node):
            if isinstance(child, dict) and "feature" in child:
                yield from entries(child, f"{path}[{child['feature']} {child.get('op', '')} {child.get('value', '')}]")
            else:
                yield from entries(child, f"{path}[{i}]")


def extra_sources() -> list[dict]:
    """Entries of config/sources_extra.yaml (sources checked after the freeze), or [] without it."""
    path = CONFIG_DIR / "sources_extra.yaml"
    return load_yaml(path).get("entries", []) if path.exists() else []


def table() -> str:
    """Markdown table over simulation.yaml, rules.yaml and ui.yaml, plus the post-freeze sources."""
    extra = extra_sources()
    confirmed = {(e["file"], e["entry"]): e for e in extra if e["verdict"] == "confirmed"}
    lines = ["| Config entry | Status | Source / note |", "|---|---|---|"]
    for name in ["simulation.yaml", "rules.yaml", "ui.yaml"]:
        for path, _, status, note in entries(load_yaml(CONFIG_DIR / name)):
            hit = confirmed.get((name, path))
            if hit and status == "ASSUMPTION":
                status = "PARTLY SOURCED"
                note = f"{hit['key']} = {hit['value']} confirmed after the freeze (table below); other parameters are assumptions."
            lines.append(f"| `{name}` {path} | {status} | {str(note).replace('|', '/')} |")
    if extra:
        lines += ["", "### Sources checked after the configs were frozen (config/sources_extra.yaml)", "",
                  "Values are unchanged: the frozen configs belong to the recorded hold-out result.", "",
                  "| Config value | Verdict | What the source says | Source |", "|---|---|---|---|"]
        for e in extra:
            lines.append(f"| `{e['file']}` {e['entry']}.{e['key']} = {e['value']} | {e['verdict']} | "
                         f"{str(e['source_says']).replace('|', '/')} | {str(e.get('source') or '—').replace('|', '/')} |")
    return "\n".join(lines)


# ===== Main =====
if __name__ == "__main__":
    print(table())
