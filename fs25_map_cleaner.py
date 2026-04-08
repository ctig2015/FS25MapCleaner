from __future__ import annotations

import os
import re
import shutil
import sys
import traceback
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple
import xml.etree.ElementTree as ET

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except Exception:
    tk = None
    filedialog = None
    messagebox = None
    ttk = None

APP_NAME = "FS25 Map Cleaner"
APP_VERSION = "1.1.0"


@dataclass
class ModInfo:
    name: str
    path: Path
    title: str
    dependencies: List[str] = field(default_factory=list)
    is_map: bool = False
    valid: bool = False
    source_type: str = "unknown"  # zip | folder
    notes: List[str] = field(default_factory=list)


@dataclass
class AnalysisResult:
    target_name: str
    target_title: str
    to_delete: List[ModInfo] = field(default_factory=list)
    kept_shared: List[Tuple[ModInfo, List[str]]] = field(default_factory=list)
    missing_dependencies: List[str] = field(default_factory=list)
    dependents_on_target: List[ModInfo] = field(default_factory=list)
    dependency_tree: List[str] = field(default_factory=list)


# -----------------------------
# Core parsing / analysis logic
# -----------------------------

def strip_xml_namespaces(root: ET.Element) -> ET.Element:
    for elem in root.iter():
        if "}" in elem.tag:
            elem.tag = elem.tag.split("}", 1)[1]
    return root


def parse_moddesc(xml_text: str) -> Tuple[str, List[str], List[str]]:
    title = ""
    dependencies: List[str] = []
    notes: List[str] = []
    try:
        root = ET.fromstring(xml_text)
        root = strip_xml_namespaces(root)
    except ET.ParseError as exc:
        return title, dependencies, [f"Invalid modDesc.xml: {exc}"]

    # Title may be plain text or nested language elements
    title_elem = root.find("title")
    if title_elem is not None:
        if (title_elem.text or "").strip():
            title = (title_elem.text or "").strip()
        else:
            for child in list(title_elem):
                if (child.text or "").strip():
                    title = (child.text or "").strip()
                    break

    deps_elem = root.find("dependencies")
    if deps_elem is not None:
        for dep_elem in deps_elem.findall("dependency"):
            candidates = []
            dep_name_attr = dep_elem.attrib.get("name")
            if dep_name_attr:
                candidates.append(dep_name_attr)
            dep_text = (dep_elem.text or "").strip()
            if dep_text:
                candidates.append(dep_text)
            for candidate in candidates:
                cleaned = candidate.strip()
                if cleaned:
                    dependencies.append(cleaned)

    # normalize and unique, preserve order
    seen: Set[str] = set()
    unique_dependencies: List[str] = []
    for dep in dependencies:
        if dep not in seen:
            unique_dependencies.append(dep)
            seen.add(dep)

    return title, unique_dependencies, notes


def _zip_namelist_lower(zf: zipfile.ZipFile) -> List[str]:
    return [name.lower() for name in zf.namelist()]


def detect_probable_map_from_names(names_lower: Iterable[str]) -> bool:
    names = list(names_lower)
    indicators = (
        "map.xml",
        "/map.xml",
        "maps/map",
        "maps/",
        "pda/",
        "farmlandmanager.xml",
        "environment.xml",
        "splines/",
    )
    score = 0
    for name in names:
        if name.endswith("map.xml"):
            score += 2
        if any(ind in name for ind in indicators):
            score += 1
    return score >= 2


def read_mod_info(path: Path) -> ModInfo:
    mod_name = path.stem if path.is_file() else path.name
    info = ModInfo(
        name=mod_name,
        path=path,
        title=mod_name,
        dependencies=[],
        is_map=False,
        valid=False,
        source_type="zip" if path.is_file() else "folder",
        notes=[],
    )

    xml_text: Optional[str] = None

    try:
        if path.is_file() and path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path, "r") as zf:
                names_lower = _zip_namelist_lower(zf)
                info.is_map = detect_probable_map_from_names(names_lower)
                moddesc_name = next((n for n in zf.namelist() if n.lower() == "moddesc.xml"), None)
                if moddesc_name is None:
                    info.notes.append("modDesc.xml not found")
                    return info
                xml_text = zf.read(moddesc_name).decode("utf-8", errors="replace")
        elif path.is_dir():
            moddesc = path / "modDesc.xml"
            if not moddesc.exists():
                info.notes.append("modDesc.xml not found")
                return info
            xml_text = moddesc.read_text(encoding="utf-8", errors="replace")
            sample_names = []
            for root, dirs, files in os.walk(path):
                rel_root = os.path.relpath(root, path).replace("\\", "/")
                if rel_root == ".":
                    rel_root = ""
                for d in dirs[:10]:
                    sample_names.append(f"{rel_root}/{d}/".strip("/"))
                for f in files[:40]:
                    sample_names.append(f"{rel_root}/{f}".strip("/"))
                if len(sample_names) > 120:
                    break
            info.is_map = detect_probable_map_from_names(n.lower() for n in sample_names)
        else:
            info.notes.append("Unsupported item type")
            return info

        if xml_text is None:
            info.notes.append("Unable to read modDesc.xml")
            return info

        title, dependencies, parse_notes = parse_moddesc(xml_text)
        if title:
            info.title = title
        info.dependencies = dependencies
        info.notes.extend(parse_notes)
        info.valid = True
        return info
    except zipfile.BadZipFile:
        info.notes.append("Invalid ZIP file")
        return info
    except Exception as exc:
        info.notes.append(f"Read error: {exc}")
        return info


def scan_mods_folder(mods_folder: Path) -> Dict[str, ModInfo]:
    mods: Dict[str, ModInfo] = {}
    if not mods_folder.exists() or not mods_folder.is_dir():
        raise FileNotFoundError(f"Mods folder not found: {mods_folder}")

    for item in sorted(mods_folder.iterdir(), key=lambda p: p.name.lower()):
        if item.name.startswith("."):
            continue
        if item.name == "__pycache__":
            continue
        if item.is_file() and item.suffix.lower() != ".zip":
            continue
        if item.is_dir() and item.name.startswith("_cleanup_quarantine"):
            continue
        mod = read_mod_info(item)
        mods[mod.name] = mod
    return mods


def resolve_dependency_tree(root_name: str, mod_by_name: Dict[str, ModInfo]) -> List[str]:
    seen: Set[str] = set()
    stack: List[str] = [root_name]
    order: List[str] = []

    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        order.append(current)
        mod = mod_by_name.get(current)
        if not mod:
            continue
        for dep in reversed(mod.dependencies):
            if dep not in seen:
                stack.append(dep)
    return order


def analyze_target(target_name: str, mod_by_name: Dict[str, ModInfo]) -> AnalysisResult:
    if target_name not in mod_by_name:
        raise KeyError(f"Target mod not found: {target_name}")

    target = mod_by_name[target_name]
    tree = resolve_dependency_tree(target_name, mod_by_name)
    tree_set = set(tree)
    result = AnalysisResult(
        target_name=target.name,
        target_title=target.title,
        dependency_tree=tree,
    )

    # Other installed mods that depend on target directly.
    for mod in mod_by_name.values():
        if mod.name == target.name:
            continue
        if target.name in mod.dependencies:
            result.dependents_on_target.append(mod)

    for name in tree:
        mod = mod_by_name.get(name)
        if mod is None:
            result.missing_dependencies.append(name)
            continue

        if name == target_name:
            result.to_delete.append(mod)
            continue

        shared_with: List[str] = []
        for other in mod_by_name.values():
            if other.name == mod.name:
                continue
            if other.name in tree_set:
                continue
            if mod.name in other.dependencies:
                shared_with.append(other.name)

        if shared_with:
            result.kept_shared.append((mod, sorted(shared_with, key=str.lower)))
        else:
            result.to_delete.append(mod)

    result.to_delete.sort(key=lambda m: m.name.lower())
    result.kept_shared.sort(key=lambda item: item[0].name.lower())
    result.missing_dependencies.sort(key=str.lower)
    result.dependents_on_target.sort(key=lambda m: m.name.lower())
    return result


def permanently_delete_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    elif path.exists():
        path.unlink()


def move_to_quarantine(path: Path, quarantine_dir: Path) -> Path:
    quarantine_dir.mkdir(parents=True, exist_ok=True)
    destination = quarantine_dir / path.name
    if destination.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        destination = quarantine_dir / f"{path.stem}_{stamp}{path.suffix}"
    shutil.move(str(path), str(destination))
    return destination


def format_report(result: AnalysisResult, mods_folder: Path, permanent_delete: bool) -> str:
    lines: List[str] = []
    lines.append(f"{APP_NAME} {APP_VERSION}")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"Mods folder: {mods_folder}")
    lines.append("")
    lines.append(f"Target: {result.target_name} | Title: {result.target_title}")
    lines.append(f"Delete mode: {'PERMANENT DELETE' if permanent_delete else 'MOVE TO QUARANTINE'}")
    lines.append("")
    lines.append("Dependency tree:")
    for name in result.dependency_tree:
        lines.append(f"  - {name}")

    lines.append("")
    lines.append("Items to remove:")
    if result.to_delete:
        for mod in result.to_delete:
            lines.append(f"  - {mod.name} ({mod.path.name})")
    else:
        lines.append("  - none")

    lines.append("")
    lines.append("Items kept because they are shared with other installed mods:")
    if result.kept_shared:
        for mod, shared_with in result.kept_shared:
            lines.append(f"  - {mod.name}  [still needed by: {', '.join(shared_with)}]")
    else:
        lines.append("  - none")

    lines.append("")
    lines.append("Missing dependencies referenced by the selected mod tree:")
    if result.missing_dependencies:
        for dep in result.missing_dependencies:
            lines.append(f"  - {dep}")
    else:
        lines.append("  - none")

    lines.append("")
    lines.append("Installed mods that depend on the selected map/mod itself:")
    if result.dependents_on_target:
        for dep in result.dependents_on_target:
            lines.append(f"  - {dep.name}")
    else:
        lines.append("  - none")

    return "\n".join(lines)


def execute_cleanup(result: AnalysisResult, mods_folder: Path, permanent_delete: bool) -> Tuple[List[str], Optional[Path]]:
    removed: List[str] = []
    quarantine_dir: Optional[Path] = None

    if not permanent_delete:
        quarantine_dir = mods_folder / "_cleanup_quarantine" / datetime.now().strftime(f"%Y%m%d_%H%M%S_{result.target_name}")

    for mod in result.to_delete:
        if not mod.path.exists():
            continue
        if permanent_delete:
            permanently_delete_path(mod.path)
        else:
            move_to_quarantine(mod.path, quarantine_dir)
        removed.append(mod.name)

    return removed, quarantine_dir


# -----------------------------
# GUI
# -----------------------------

class MapCleanerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        try:
            self.root.iconbitmap(default="assets\\fs25_map_cleaner.ico")
        except Exception:
            pass
        self.root.geometry("1180x760")
        self.root.minsize(1000, 650)

        self.mods_folder_var = tk.StringVar()
        self.filter_var = tk.StringVar()
        self.show_maps_only_var = tk.BooleanVar(value=True)
        self.permanent_delete_var = tk.BooleanVar(value=True)

        self.mod_index: Dict[str, ModInfo] = {}
        self.filtered_keys: List[str] = []
        self.last_result: Optional[AnalysisResult] = None

        self._build_ui()

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=10)
        outer.pack(fill="both", expand=True)

        top = ttk.LabelFrame(outer, text="Mods folder", padding=10)
        top.pack(fill="x", pady=(0, 10))

        ttk.Entry(top, textvariable=self.mods_folder_var).pack(side="left", fill="x", expand=True, padx=(0, 8))
        ttk.Button(top, text="Browse…", command=self.pick_folder).pack(side="left", padx=(0, 8))
        ttk.Button(top, text="Scan", command=self.scan).pack(side="left")

        middle = ttk.Panedwindow(outer, orient="horizontal")
        middle.pack(fill="both", expand=True)

        left = ttk.Frame(middle, padding=(0, 0, 8, 0))
        right = ttk.Frame(middle)
        middle.add(left, weight=1)
        middle.add(right, weight=2)

        filter_row = ttk.Frame(left)
        filter_row.pack(fill="x", pady=(0, 8))
        ttk.Label(filter_row, text="Find:").pack(side="left")
        filter_entry = ttk.Entry(filter_row, textvariable=self.filter_var)
        filter_entry.pack(side="left", fill="x", expand=True, padx=(6, 8))
        filter_entry.bind("<KeyRelease>", lambda _e: self.refresh_list())
        ttk.Checkbutton(filter_row, text="Show probable maps only", variable=self.show_maps_only_var, command=self.refresh_list).pack(side="left")

        list_frame = ttk.LabelFrame(left, text="Select map / mod to remove", padding=6)
        list_frame.pack(fill="both", expand=True)

        columns = ("type", "deps", "title")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Filename")
        self.tree.heading("type", text="Type")
        self.tree.heading("deps", text="Deps")
        self.tree.heading("title", text="Title")
        self.tree.column("#0", width=210, stretch=True)
        self.tree.column("type", width=70, anchor="center")
        self.tree.column("deps", width=50, anchor="center")
        self.tree.column("title", width=220, stretch=True)
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.preview_selected())
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")

        actions = ttk.Frame(left)
        actions.pack(fill="x", pady=(8, 0))
        ttk.Button(actions, text="Analyze selected", command=self.analyze_selected).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Delete selected + unused deps", command=self.delete_selected).pack(side="left", padx=(0, 8))
        ttk.Checkbutton(actions, text="Permanent delete (skip quarantine)", variable=self.permanent_delete_var).pack(side="left")

        output_frame = ttk.LabelFrame(right, text="Analysis / log", padding=6)
        output_frame.pack(fill="both", expand=True)
        self.output = tk.Text(output_frame, wrap="word")
        self.output.pack(side="left", fill="both", expand=True)
        output_scroll = ttk.Scrollbar(output_frame, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=output_scroll.set)
        output_scroll.pack(side="right", fill="y")

        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(8, 0))
        ttk.Label(bottom, text=(
            "Tip: Scan your FS25 mods folder, pick a map, analyze it, then remove the map and only the dependencies that are not needed by any other installed mod."
        )).pack(side="left")

    def log(self, text: str, clear: bool = False) -> None:
        if clear:
            self.output.delete("1.0", "end")
        self.output.insert("end", text + "\n")
        self.output.see("end")

    def pick_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select your Farming Simulator 25 mods folder")
        if folder:
            self.mods_folder_var.set(folder)

    def scan(self) -> None:
        folder_text = self.mods_folder_var.get().strip()
        if not folder_text:
            messagebox.showerror(APP_NAME, "Pick your FS25 mods folder first.")
            return
        mods_folder = Path(folder_text)
        try:
            self.log("Scanning mods folder...", clear=True)
            self.mod_index = scan_mods_folder(mods_folder)
            self.refresh_list()
            total = len(self.mod_index)
            maps = sum(1 for m in self.mod_index.values() if m.is_map)
            valid = sum(1 for m in self.mod_index.values() if m.valid)
            self.log(f"Found {total} items | valid mods: {valid} | probable maps: {maps}")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
            self.log(traceback.format_exc(), clear=True)

    def refresh_list(self) -> None:
        query = self.filter_var.get().strip().lower()
        show_maps_only = self.show_maps_only_var.get()
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.filtered_keys = []

        mods = sorted(self.mod_index.values(), key=lambda m: (not m.is_map, m.name.lower()))
        for mod in mods:
            if show_maps_only and not mod.is_map:
                continue
            haystack = f"{mod.name} {mod.title}".lower()
            if query and query not in haystack:
                continue
            mod_type = "Map" if mod.is_map else "Mod"
            self.tree.insert("", "end", iid=mod.name, text=mod.path.name, values=(mod_type, len(mod.dependencies), mod.title))
            self.filtered_keys.append(mod.name)

    def get_selected_name(self) -> Optional[str]:
        selection = self.tree.selection()
        if not selection:
            return None
        return selection[0]

    def preview_selected(self) -> None:
        selected = self.get_selected_name()
        if not selected:
            return
        mod = self.mod_index.get(selected)
        if not mod:
            return
        text = [
            f"Selected: {mod.name}",
            f"Title: {mod.title}",
            f"Path: {mod.path}",
            f"Type: {'Map' if mod.is_map else 'Mod'}",
            f"Valid: {mod.valid}",
            "Dependencies:",
        ]
        if mod.dependencies:
            text.extend(f"  - {dep}" for dep in mod.dependencies)
        else:
            text.append("  - none")
        if mod.notes:
            text.append("Notes:")
            text.extend(f"  - {note}" for note in mod.notes)
        self.log("\n".join(text), clear=True)

    def analyze_selected(self) -> None:
        selected = self.get_selected_name()
        if not selected:
            messagebox.showerror(APP_NAME, "Select a map or mod first.")
            return
        try:
            self.last_result = analyze_target(selected, self.mod_index)
            report = format_report(
                self.last_result,
                Path(self.mods_folder_var.get().strip()),
                self.permanent_delete_var.get(),
            )
            self.log(report, clear=True)
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
            self.log(traceback.format_exc(), clear=True)

    def delete_selected(self) -> None:
        if not self.mod_index:
            messagebox.showerror(APP_NAME, "Scan the mods folder first.")
            return
        selected = self.get_selected_name()
        if not selected:
            messagebox.showerror(APP_NAME, "Select a map or mod first.")
            return

        try:
            result = analyze_target(selected, self.mod_index)
            self.last_result = result
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
            return

        permanent = self.permanent_delete_var.get()
        delete_names = [mod.name for mod in result.to_delete]
        shared_names = [f"{mod.name} (kept; used by {', '.join(shared)})" for mod, shared in result.kept_shared]

        confirm_lines = [
            f"Selected: {result.target_name}",
            "",
            f"This will {'PERMANENTLY DELETE' if permanent else 'MOVE TO QUARANTINE'} {len(delete_names)} item(s):",
            *[f"- {name}" for name in delete_names[:30]],
        ]
        if len(delete_names) > 30:
            confirm_lines.append(f"... and {len(delete_names) - 30} more")
        if shared_names:
            confirm_lines.extend(["", "These will be kept because they are shared:"])
            confirm_lines.extend(f"- {line}" for line in shared_names[:20])
            if len(shared_names) > 20:
                confirm_lines.append(f"... and {len(shared_names) - 20} more")
        if result.dependents_on_target:
            confirm_lines.extend(["", "Warning: installed mods depending on the selected map/mod:"])
            confirm_lines.extend(f"- {mod.name}" for mod in result.dependents_on_target)
        confirm_lines.extend(["", "Continue?"])

        ok = messagebox.askyesno(APP_NAME, "\n".join(confirm_lines))
        if not ok:
            return

        mods_folder = Path(self.mods_folder_var.get().strip())
        report_before = format_report(result, mods_folder, permanent)
        report_path = mods_folder / f"cleanup_report_{result.target_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        try:
            report_path.write_text(report_before, encoding="utf-8")
        except Exception:
            report_path = None

        try:
            removed, quarantine_dir = execute_cleanup(result, mods_folder, permanent)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"Cleanup failed: {exc}")
            self.log(traceback.format_exc(), clear=True)
            return

        summary = [
            f"Removed {len(removed)} item(s).",
            *[f"- {name}" for name in removed],
        ]
        if quarantine_dir:
            summary.extend(["", f"Moved to: {quarantine_dir}"])
        if report_path:
            summary.extend(["", f"Report saved to: {report_path}"])

        self.log("\n".join(summary), clear=True)
        messagebox.showinfo(APP_NAME, "\n".join(summary[:20]))
        self.scan()


# -----------------------------
# CLI (optional)
# -----------------------------

def run_cli(argv: List[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Analyze or clean FS25 map dependencies.")
    parser.add_argument("mods_folder", nargs="?", help="Path to the FS25 mods folder")
    parser.add_argument("target", nargs="?", help="Target map/mod filename without or with .zip")
    parser.add_argument("--analyze", action="store_true", help="Analyze only; do not delete")
    parser.add_argument("--delete", action="store_true", help="Delete/remove immediately")
    parser.add_argument("--quarantine", action="store_true", help="Move to quarantine instead of permanent delete")
    args = parser.parse_args(argv)

    if not args.mods_folder or not args.target:
        parser.print_help()
        return 2

    mods_folder = Path(args.mods_folder)
    target_name = Path(args.target).stem
    mod_index = scan_mods_folder(mods_folder)
    result = analyze_target(target_name, mod_index)
    report = format_report(result, mods_folder, permanent_delete=not args.quarantine)
    print(report)

    if args.delete:
        removed, quarantine_dir = execute_cleanup(result, mods_folder, permanent_delete=not args.quarantine)
        print("\nRemoved:")
        for name in removed:
            print(f"- {name}")
        if quarantine_dir:
            print(f"\nMoved to: {quarantine_dir}")
    return 0


def main() -> int:
    if len(sys.argv) > 1:
        return run_cli(sys.argv[1:])

    if tk is None:
        print("Tkinter is not available in this Python build.", file=sys.stderr)
        return 1

    root = tk.Tk()
    try:
        style = ttk.Style(root)
        if "vista" in style.theme_names():
            style.theme_use("vista")
    except Exception:
        pass
    app = MapCleanerApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
