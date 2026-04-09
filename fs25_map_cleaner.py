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
    from tkinter import font as tkfont
except Exception:  # pragma: no cover
    tk = None
    filedialog = None
    messagebox = None
    ttk = None
    tkfont = None

APP_NAME = "FS25 Map Cleaner"
APP_VERSION = "1.1.1"
APP_BUILD = "2026-04-09"
APP_SUBTITLE = "Remove a map and only the dependency mods no other installed map or save still uses."

ACCENT = "#2676c8"
ACCENT_DARK = "#1f5fa1"
SUCCESS = "#2d8b57"
WARNING = "#e8b339"
DANGER = "#c94a4a"
BG = "#eef2f6"
CARD_BG = "#ffffff"
HEADER_BG = "#f7f9fc"
TEXT = "#1d2630"
MUTED = "#5d6b79"


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
class KeepReason:
    mod: ModInfo
    shared_with_mods: List[str] = field(default_factory=list)
    shared_with_savegames: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    target_name: str
    target_title: str
    to_delete: List[ModInfo] = field(default_factory=list)
    kept: List[KeepReason] = field(default_factory=list)
    missing_dependencies: List[str] = field(default_factory=list)
    dependents_on_target: List[ModInfo] = field(default_factory=list)
    dependency_tree: List[str] = field(default_factory=list)
    scanned_savegames: List[Path] = field(default_factory=list)


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


class ScanProgressCallback:
    def update(self, current: int, total: int, name: str) -> None:  # pragma: no cover - interface only
        pass


def scan_mods_folder(mods_folder: Path, progress: Optional[ScanProgressCallback] = None) -> Dict[str, ModInfo]:
    mods: Dict[str, ModInfo] = {}
    if not mods_folder.exists() or not mods_folder.is_dir():
        raise FileNotFoundError(f"Mods folder not found: {mods_folder}")

    items = [
        item for item in sorted(mods_folder.iterdir(), key=lambda p: p.name.lower())
        if not item.name.startswith(".")
        and item.name != "__pycache__"
        and not (item.is_file() and item.suffix.lower() != ".zip")
        and not (item.is_dir() and item.name.startswith("_cleanup_quarantine"))
    ]

    total = len(items)
    for idx, item in enumerate(items, start=1):
        if progress is not None:
            progress.update(idx, total, item.name)
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


def _compile_name_pattern(mod_name: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![a-z0-9]){re.escape(mod_name.lower())}(?![a-z0-9])")


def scan_savegame_usage(savegame_folders: Iterable[Path], candidate_mod_names: Iterable[str]) -> Dict[str, Dict[str, List[str]]]:
    candidates = [name for name in candidate_mod_names if name]
    if not candidates:
        return {}

    patterns = {name: _compile_name_pattern(name) for name in candidates}
    hits: Dict[str, Dict[str, List[str]]] = {}

    for folder in savegame_folders:
        if not folder.exists() or not folder.is_dir():
            continue
        save_label = folder.name
        for root, _dirs, files in os.walk(folder):
            for filename in files:
                if not filename.lower().endswith(".xml"):
                    continue
                xml_path = Path(root) / filename
                try:
                    text = xml_path.read_text(encoding="utf-8", errors="replace").lower()
                except Exception:
                    continue

                rel_path = str(xml_path.relative_to(folder)).replace("\\", "/")
                for mod_name, pattern in patterns.items():
                    if pattern.search(text):
                        save_hits = hits.setdefault(mod_name, {}).setdefault(save_label, [])
                        if rel_path not in save_hits:
                            save_hits.append(rel_path)
    return hits


def analyze_target(
    target_name: str,
    mod_by_name: Dict[str, ModInfo],
    savegame_folders: Optional[Iterable[Path]] = None,
) -> AnalysisResult:
    if target_name not in mod_by_name:
        raise KeyError(f"Target mod not found: {target_name}")

    target = mod_by_name[target_name]
    tree = resolve_dependency_tree(target_name, mod_by_name)
    tree_set = set(tree)
    scanned_savegames = [Path(p) for p in (savegame_folders or []) if Path(p).exists()]
    save_hits = scan_savegame_usage(scanned_savegames, [name for name in tree if name != target_name])

    result = AnalysisResult(
        target_name=target.name,
        target_title=target.title,
        dependency_tree=tree,
        scanned_savegames=scanned_savegames,
    )

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

        shared_with_mods: List[str] = []
        for other in mod_by_name.values():
            if other.name == mod.name:
                continue
            if other.name in tree_set:
                continue
            if mod.name in other.dependencies:
                shared_with_mods.append(other.name)

        shared_with_savegames = {
            save_name: files
            for save_name, files in sorted(save_hits.get(mod.name, {}).items(), key=lambda item: item[0].lower())
        }

        if shared_with_mods or shared_with_savegames:
            result.kept.append(
                KeepReason(
                    mod=mod,
                    shared_with_mods=sorted(shared_with_mods, key=str.lower),
                    shared_with_savegames=shared_with_savegames,
                )
            )
        else:
            result.to_delete.append(mod)

    result.to_delete.sort(key=lambda m: m.name.lower())
    result.kept.sort(key=lambda item: item.mod.name.lower())
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
    lines.append(f"{APP_NAME} v{APP_VERSION} | Build {APP_BUILD}")
    lines.append(f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    lines.append(f"Mods folder: {mods_folder}")
    lines.append(f"Delete mode: {'PERMANENT DELETE' if permanent_delete else 'MOVE TO QUARANTINE'}")
    if result.scanned_savegames:
        lines.append("Savegame protection:")
        for folder in result.scanned_savegames:
            lines.append(f"  - {folder}")
    else:
        lines.append("Savegame protection: off")

    lines.append("")
    lines.append(f"Target: {result.target_name} | Title: {result.target_title}")
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
    lines.append("Items kept because they are still used elsewhere:")
    if result.kept:
        for keep in result.kept:
            reason_bits = []
            if keep.shared_with_mods:
                reason_bits.append(f"used by mods/maps: {', '.join(keep.shared_with_mods)}")
            if keep.shared_with_savegames:
                save_bits = []
                for save_name, files in keep.shared_with_savegames.items():
                    if files:
                        save_bits.append(f"{save_name} ({', '.join(files[:3])}{'...' if len(files) > 3 else ''})")
                    else:
                        save_bits.append(save_name)
                reason_bits.append(f"used by savegames: {', '.join(save_bits)}")
            lines.append(f"  - {keep.mod.name}  [{' | '.join(reason_bits)}]")
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
# GUI helpers
# -----------------------------

def try_set_icon(root: tk.Tk) -> None:
    try:
        icon_path = Path(__file__).resolve().parent / "assets" / "fs25_map_cleaner.ico"
        if icon_path.exists():
            root.iconbitmap(default=str(icon_path))
    except Exception:
        pass


def make_card(parent: tk.Widget, title: str) -> Tuple[tk.Frame, tk.Frame]:
    card = tk.Frame(parent, bg=CARD_BG, bd=1, relief="solid", highlightthickness=0)
    header = tk.Label(
        card,
        text=title,
        bg=ACCENT,
        fg="white",
        font=("Segoe UI", 12, "bold"),
        anchor="w",
        padx=14,
        pady=10,
    )
    header.pack(fill="x")
    body = tk.Frame(card, bg=CARD_BG, padx=12, pady=12)
    body.pack(fill="both", expand=True)
    return card, body


class _TkProgressAdapter(ScanProgressCallback):
    def __init__(self, app: "MapCleanerApp"):
        self.app = app

    def update(self, current: int, total: int, name: str) -> None:
        self.app.set_status(f"Scanning {current}/{total}: {name}")
        self.app.root.update_idletasks()


# -----------------------------
# GUI
# -----------------------------

class MapCleanerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1460x940")
        self.root.minsize(1240, 840)
        self.root.configure(bg=BG)
        try_set_icon(root)

        self.mods_folder_var = tk.StringVar()
        self.filter_var = tk.StringVar()
        self.show_maps_only_var = tk.BooleanVar(value=True)
        self.permanent_delete_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready")
        self.summary_var = tk.StringVar(value="Select your FS25 mods folder, scan it, pick a map, then analyze the result.")

        self.mod_index: Dict[str, ModInfo] = {}
        self.filtered_keys: List[str] = []
        self.last_result: Optional[AnalysisResult] = None
        self.savegame_folders: List[Path] = []

        self._setup_styles()
        self._build_ui()
        self.render_welcome()

    def _setup_styles(self) -> None:
        style = ttk.Style(self.root)
        try:
            if "clam" in style.theme_names():
                style.theme_use("clam")
        except Exception:
            pass

        style.configure("App.TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD_BG)
        style.configure("TLabel", background=CARD_BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=CARD_BG, foreground=MUTED, font=("Segoe UI", 10))
        style.configure("Section.TLabel", background=CARD_BG, foreground=TEXT, font=("Segoe UI", 11, "bold"))
        style.configure("TEntry", padding=6)
        style.configure("TCombobox", padding=6)
        style.configure("Primary.TButton", background=ACCENT, foreground="white", borderwidth=0, focusthickness=3, focuscolor=ACCENT)
        style.map("Primary.TButton", background=[("active", ACCENT_DARK), ("disabled", "#96bde3")], foreground=[("disabled", "#f3f7fb")])
        style.configure("Danger.TButton", background=WARNING, foreground="#202020", borderwidth=0)
        style.map("Danger.TButton", background=[("active", "#cf9e2f"), ("disabled", "#f2dda1")])
        style.configure("Secondary.TButton", background="#e8edf4", foreground=TEXT, borderwidth=0)
        style.map("Secondary.TButton", background=[("active", "#d9e2ec")])
        style.configure("Treeview", rowheight=32, font=("Segoe UI", 10), background="white", fieldbackground="white")
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), padding=(8, 8))

    def _build_ui(self) -> None:
        outer = tk.Frame(self.root, bg=BG, padx=14, pady=14)
        outer.pack(fill="both", expand=True)

        self._build_header(outer)
        self._build_step1(outer)

        middle = tk.Frame(outer, bg=BG)
        middle.pack(fill="both", expand=True, pady=(12, 12))
        middle.columnconfigure(0, weight=7)
        middle.columnconfigure(1, weight=6)
        middle.rowconfigure(0, weight=1)

        self._build_step2(middle)

        right_col = tk.Frame(middle, bg=BG)
        right_col.grid(row=0, column=1, sticky="nsew")
        right_col.columnconfigure(0, weight=1)
        right_col.rowconfigure(0, weight=1)

        self._build_step3(right_col)
        self._build_step4(right_col)

        self._build_status_bar(outer)

    def _build_header(self, parent: tk.Widget) -> None:
        header = tk.Frame(parent, bg=HEADER_BG, bd=1, relief="solid")
        header.pack(fill="x")

        title_row = tk.Frame(header, bg=HEADER_BG, padx=16, pady=14)
        title_row.pack(fill="x")

        badge = tk.Label(
            title_row,
            text="FS25",
            bg=ACCENT,
            fg="white",
            font=("Segoe UI", 11, "bold"),
            padx=10,
            pady=6,
        )
        badge.pack(side="left", padx=(0, 12))

        text_col = tk.Frame(title_row, bg=HEADER_BG)
        text_col.pack(side="left", fill="x", expand=True)
        tk.Label(text_col, text=APP_NAME, bg=HEADER_BG, fg=TEXT, font=("Segoe UI", 24, "bold")).pack(anchor="w")
        tk.Label(text_col, text=APP_SUBTITLE, bg=HEADER_BG, fg=MUTED, font=("Segoe UI", 12), wraplength=980, justify="left").pack(anchor="w", pady=(4, 0))
        tk.Label(
            title_row,
            text=f"Version {APP_VERSION} | Build {APP_BUILD}",
            bg=HEADER_BG,
            fg=MUTED,
            font=("Segoe UI", 11),
        ).pack(side="right")

    def _build_step1(self, parent: tk.Widget) -> None:
        card, body = make_card(parent, "Step 1 – Select FS25 Mods Folder and Optional Savegame Protection")
        card.pack(fill="x", pady=(12, 0))
        body.columnconfigure(1, weight=1)

        tk.Label(body, text="FS25 Mods Folder", bg=CARD_BG, fg=TEXT, font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 8))
        mods_row = tk.Frame(body, bg=CARD_BG)
        mods_row.grid(row=1, column=0, columnspan=4, sticky="ew")
        mods_row.columnconfigure(0, weight=1)
        ttk.Entry(mods_row, textvariable=self.mods_folder_var).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(mods_row, text="Browse…", style="Secondary.TButton", command=self.pick_mods_folder).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(mods_row, text="Scan Mods", style="Primary.TButton", command=self.scan).grid(row=0, column=2)

        hint = (
            "Optional savegame scan protects dependency mods if they are still referenced in another savegame "
            "(for example in vehicles.xml or placeables.xml)."
        )
        tk.Label(body, text=hint, bg=CARD_BG, fg=MUTED, wraplength=1180, justify="left", font=("Segoe UI", 10)).grid(
            row=2, column=0, columnspan=4, sticky="w", pady=(12, 8)
        )

        save_frame = tk.Frame(body, bg=CARD_BG)
        save_frame.grid(row=3, column=0, columnspan=4, sticky="ew")
        save_frame.columnconfigure(0, weight=1)

        self.savegame_listbox = tk.Listbox(
            save_frame,
            height=4,
            activestyle="none",
            font=("Segoe UI", 10),
            selectmode="extended",
            relief="solid",
            bd=1,
            highlightthickness=0,
        )
        self.savegame_listbox.grid(row=0, column=0, rowspan=3, sticky="nsew", padx=(0, 10))

        ttk.Button(save_frame, text="Add Savegame…", style="Secondary.TButton", command=self.add_savegame_folder).grid(row=0, column=1, sticky="ew", pady=(0, 6))
        ttk.Button(save_frame, text="Remove Selected", style="Secondary.TButton", command=self.remove_selected_savegames).grid(row=1, column=1, sticky="ew", pady=(0, 6))
        ttk.Button(save_frame, text="Clear", style="Secondary.TButton", command=self.clear_savegames).grid(row=2, column=1, sticky="ew")

    def _build_step2(self, parent: tk.Widget) -> None:
        card, body = make_card(parent, "Step 2 – Choose Map")
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        body.rowconfigure(2, weight=1)
        body.columnconfigure(0, weight=1)

        top_row = tk.Frame(body, bg=CARD_BG)
        top_row.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        top_row.columnconfigure(0, weight=1)
        search_entry = ttk.Entry(top_row, textvariable=self.filter_var)
        search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        search_entry.bind("<KeyRelease>", lambda _e: self.refresh_list())
        tk.Checkbutton(
            top_row,
            text="Show maps only",
            variable=self.show_maps_only_var,
            command=self.refresh_list,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BG,
            activeforeground=TEXT,
            selectcolor="white",
            font=("Segoe UI", 10),
        ).grid(row=0, column=1)

        tk.Label(body, text="Pick the map or mod you want to remove.", bg=CARD_BG, fg=MUTED, font=("Segoe UI", 10)).grid(row=1, column=0, sticky="w", pady=(0, 8))

        list_frame = tk.Frame(body, bg=CARD_BG)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        columns = ("type", "deps", "title")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="Filename")
        self.tree.heading("type", text="Type")
        self.tree.heading("deps", text="Deps")
        self.tree.heading("title", text="Title")
        self.tree.column("#0", width=250, stretch=True)
        self.tree.column("type", width=80, anchor="center")
        self.tree.column("deps", width=60, anchor="center")
        self.tree.column("title", width=260, stretch=True)
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.preview_selected())

        yscroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=yscroll.set)
        yscroll.grid(row=0, column=1, sticky="ns")

        xscroll = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(xscrollcommand=xscroll.set)
        xscroll.grid(row=1, column=0, sticky="ew")

        button_row = tk.Frame(body, bg=CARD_BG)
        button_row.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(button_row, text="Analyze Map", style="Primary.TButton", command=self.analyze_selected).pack(side="right")

    def _build_step3(self, parent: tk.Widget) -> None:
        card, body = make_card(parent, "Step 3 – Review Results")
        card.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        body.rowconfigure(1, weight=1)
        body.columnconfigure(0, weight=1)

        tk.Label(
            body,
            textvariable=self.summary_var,
            bg=CARD_BG,
            fg=TEXT,
            justify="left",
            anchor="w",
            wraplength=560,
            font=("Segoe UI", 11, "bold"),
        ).grid(row=0, column=0, sticky="ew", pady=(0, 8))

        output_wrap = tk.Frame(body, bg="#fdfefe", bd=1, relief="solid")
        output_wrap.grid(row=1, column=0, sticky="nsew")
        output_wrap.rowconfigure(0, weight=1)
        output_wrap.columnconfigure(0, weight=1)
        self.output = tk.Text(
            output_wrap,
            wrap="word",
            relief="flat",
            bd=0,
            padx=14,
            pady=14,
            font=("Segoe UI", 11),
            fg=TEXT,
            bg="#fdfefe",
            state="disabled",
        )
        self.output.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(output_wrap, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=scroll.set)
        scroll.grid(row=0, column=1, sticky="ns")
        self.output.tag_configure("h1", font=("Segoe UI", 14, "bold"), spacing1=10, spacing3=8)
        self.output.tag_configure("h2", font=("Segoe UI", 11, "bold"), spacing1=8, spacing3=4)
        self.output.tag_configure("ok", foreground=SUCCESS)
        self.output.tag_configure("warn", foreground="#9c6a00")
        self.output.tag_configure("danger", foreground=DANGER)
        self.output.tag_configure("muted", foreground=MUTED)

    def _build_step4(self, parent: tk.Widget) -> None:
        card, body = make_card(parent, "Step 4 – Remove Files")
        card.grid(row=1, column=0, sticky="ew")
        body.columnconfigure(0, weight=1)

        tk.Checkbutton(
            body,
            text="Delete permanently (skip quarantine)",
            variable=self.permanent_delete_var,
            bg=CARD_BG,
            fg=TEXT,
            activebackground=CARD_BG,
            activeforeground=TEXT,
            selectcolor="white",
            font=("Segoe UI", 10),
        ).grid(row=0, column=0, sticky="w")

        tk.Label(
            body,
            text="Shared dependencies and savegame-used mods are kept automatically, even when permanent delete is enabled.",
            bg=CARD_BG,
            fg=MUTED,
            font=("Segoe UI", 10),
            wraplength=560,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))

        danger_row = tk.Frame(body, bg=CARD_BG)
        danger_row.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        danger_row.columnconfigure(0, weight=1)

        ttk.Button(danger_row, text="About", style="Secondary.TButton", command=self.show_about).grid(row=0, column=0, sticky="w")
        self.delete_button = ttk.Button(
            danger_row,
            text="Remove Map + Unused Dependencies",
            style="Danger.TButton",
            command=self.delete_selected,
        )
        self.delete_button.grid(row=0, column=1, sticky="e")
        self._set_delete_enabled(False)

    def _build_status_bar(self, parent: tk.Widget) -> None:
        bar = tk.Frame(parent, bg=HEADER_BG, bd=1, relief="solid", padx=12, pady=8)
        bar.pack(fill="x", pady=(0, 0))
        tk.Label(bar, textvariable=self.status_var, bg=HEADER_BG, fg=SUCCESS, font=("Segoe UI", 11, "bold")).pack(side="left")
        tk.Label(bar, text=f"Version {APP_VERSION} | Build {APP_BUILD}", bg=HEADER_BG, fg=MUTED, font=("Segoe UI", 10)).pack(side="right")

    def _set_delete_enabled(self, enabled: bool) -> None:
        if not hasattr(self, "delete_button"):
            return
        if enabled:
            self.delete_button.state(["!disabled"])
        else:
            self.delete_button.state(["disabled"])

    def set_status(self, text: str) -> None:
        self.status_var.set(text)

    def log(self, text: str, clear: bool = False) -> None:
        self.output.configure(state="normal")
        if clear:
            self.output.delete("1.0", "end")
        self.output.insert("end", text + "\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def clear_output(self) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def render_welcome(self) -> None:
        self.summary_var.set("Select your FS25 mods folder, scan it, pick a map, then analyze the result.")
        self._set_delete_enabled(False)
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("end", "FS25 Map Cleaner\n", "h1")
        self.output.insert("end", "Designed to make removing large FS25 maps far easier when they need lots of extra mods.\n\n")
        self.output.insert("end", "What it does\n", "h2")
        self.output.insert("end", "• Scans your mods folder and reads dependency data from modDesc.xml\n")
        self.output.insert("end", "• Lets you analyze a map before deleting anything\n")
        self.output.insert("end", "• Keeps dependencies used by other installed maps or mods\n")
        self.output.insert("end", "• Optionally scans selected savegames and keeps mods still referenced there\n\n")
        self.output.insert("end", "Suggested flow\n", "h2")
        self.output.insert("end", "1. Pick your FS25 mods folder\n2. Add any savegames you want protected\n3. Scan mods\n4. Select the map\n5. Analyze the result\n6. Click Remove Map + Unused Dependencies only after checking the review panel\n", "muted")
        self.output.configure(state="disabled")

    def pick_mods_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select your Farming Simulator 25 mods folder")
        if folder:
            self.mods_folder_var.set(folder)

    def add_savegame_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select an FS25 savegame folder to protect")
        if not folder:
            return
        path = Path(folder)
        if path in self.savegame_folders:
            return
        self.savegame_folders.append(path)
        self.savegame_listbox.insert("end", str(path))
        self.set_status(f"Added savegame protection: {path.name}")

    def remove_selected_savegames(self) -> None:
        indices = list(self.savegame_listbox.curselection())
        if not indices:
            return
        for index in reversed(indices):
            self.savegame_listbox.delete(index)
            del self.savegame_folders[index]
        self.set_status("Removed selected savegame protection folder(s).")

    def clear_savegames(self) -> None:
        self.savegame_folders.clear()
        self.savegame_listbox.delete(0, "end")
        self.set_status("Savegame protection cleared.")

    def scan(self) -> None:
        folder_text = self.mods_folder_var.get().strip()
        if not folder_text:
            messagebox.showerror(APP_NAME, "Pick your FS25 mods folder first.")
            return
        mods_folder = Path(folder_text)
        try:
            self.last_result = None
            self._set_delete_enabled(False)
            self.summary_var.set("Scanning mods folder…")
            self.clear_output()
            self.set_status("Starting scan…")
            progress = _TkProgressAdapter(self)
            self.mod_index = scan_mods_folder(mods_folder, progress=progress)
            self.refresh_list()
            total = len(self.mod_index)
            maps = sum(1 for m in self.mod_index.values() if m.is_map)
            valid = sum(1 for m in self.mod_index.values() if m.valid)
            self.summary_var.set(f"Scan complete: {total} items found | {maps} probable maps | {len(self.savegame_folders)} protected savegame(s)")
            self.log(f"Found {total} items\nValid mods: {valid}\nProbable maps: {maps}\nProtected savegames: {len(self.savegame_folders)}", clear=True)
            self.set_status(f"Ready — scanned {total} items.")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
            self.summary_var.set("Scan failed.")
            self.log(traceback.format_exc(), clear=True)
            self.set_status("Scan failed.")

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
        self._set_delete_enabled(False)
        if not selected:
            return
        mod = self.mod_index.get(selected)
        if not mod:
            return
        self.summary_var.set(f"Selected: {mod.title or mod.name} ({mod.path.name})")
        lines = [
            f"Selected: {mod.name}",
            f"Title: {mod.title}",
            f"Path: {mod.path}",
            f"Type: {'Map' if mod.is_map else 'Mod'}",
            f"Valid: {'Yes' if mod.valid else 'No'}",
            "",
            "Dependencies:",
        ]
        if mod.dependencies:
            lines.extend(f"- {dep}" for dep in mod.dependencies)
        else:
            lines.append("- none")
        if mod.notes:
            lines.append("")
            lines.append("Notes:")
            lines.extend(f"- {note}" for note in mod.notes)
        self.log("\n".join(lines), clear=True)
        self.set_status(f"Previewing {mod.path.name}")

    def _render_analysis_text(self, result: AnalysisResult) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.insert("end", f"Selected map: {result.target_title} ({result.target_name})\n", "h1")

        if result.scanned_savegames:
            self.output.insert("end", "Protected savegames\n", "h2")
            for folder in result.scanned_savegames:
                self.output.insert("end", f"• {folder.name}: {folder}\n", "muted")
            self.output.insert("end", "\n")

        self.output.insert("end", "Will remove\n", "h2")
        if result.to_delete:
            for mod in result.to_delete:
                prefix = "🗑 " if mod.name == result.target_name else "✓ "
                self.output.insert("end", f"{prefix}{mod.path.name}\n", "danger" if mod.name == result.target_name else None)
        else:
            self.output.insert("end", "Nothing is currently marked for removal.\n", "muted")

        self.output.insert("end", "\nWill keep\n", "h2")
        if result.kept:
            for keep in result.kept:
                self.output.insert("end", f"• {keep.mod.path.name}\n", "ok")
                if keep.shared_with_mods:
                    self.output.insert("end", f"  Still used by installed mods/maps: {', '.join(keep.shared_with_mods)}\n", "muted")
                if keep.shared_with_savegames:
                    save_parts = []
                    for save_name, files in keep.shared_with_savegames.items():
                        sample = ", ".join(files[:2])
                        if len(files) > 2:
                            sample += ", …"
                        save_parts.append(f"{save_name} ({sample})")
                    self.output.insert("end", f"  Still referenced by savegames: {', '.join(save_parts)}\n", "muted")
        else:
            self.output.insert("end", "No shared dependencies were found.\n", "muted")

        if result.missing_dependencies:
            self.output.insert("end", "\nMissing dependencies\n", "h2")
            for name in result.missing_dependencies:
                self.output.insert("end", f"• {name}\n", "warn")

        if result.dependents_on_target:
            self.output.insert("end", "\nInstalled mods depending on the selected map/mod\n", "h2")
            for mod in result.dependents_on_target:
                self.output.insert("end", f"• {mod.name}\n", "warn")

        delete_count = len(result.to_delete)
        dep_count = max(0, delete_count - 1)
        self.output.insert("end", "\nSummary\n", "h2")
        self.output.insert(
            "end",
            f"Total files affected: {delete_count} ({'1 map' if delete_count else '0 maps'} + {dep_count} dependency{'ies' if dep_count != 1 else ''})\n",
            "muted",
        )
        self.output.configure(state="disabled")

    def analyze_selected(self) -> None:
        selected = self.get_selected_name()
        if not selected:
            messagebox.showerror(APP_NAME, "Select a map or mod first.")
            return
        try:
            self.set_status("Analyzing selection…")
            self.last_result = analyze_target(selected, self.mod_index, self.savegame_folders)
            self.summary_var.set(
                f"Analysis complete: {len(self.last_result.to_delete)} item(s) would be removed, {len(self.last_result.kept)} item(s) would be kept."
            )
            self._render_analysis_text(self.last_result)
            self._set_delete_enabled(True)
            self.set_status("Analysis complete.")
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
            self._set_delete_enabled(False)
            self.log(traceback.format_exc(), clear=True)
            self.summary_var.set("Analysis failed.")
            self.set_status("Analysis failed.")

    def delete_selected(self) -> None:
        if not self.mod_index:
            messagebox.showerror(APP_NAME, "Scan the mods folder first.")
            return
        selected = self.get_selected_name()
        if not selected:
            messagebox.showerror(APP_NAME, "Select a map or mod first.")
            return

        try:
            result = analyze_target(selected, self.mod_index, self.savegame_folders)
            self.last_result = result
        except Exception as exc:
            messagebox.showerror(APP_NAME, str(exc))
            return

        permanent = self.permanent_delete_var.get()
        delete_names = [mod.name for mod in result.to_delete]
        confirm_lines = [
            f"Selected: {result.target_name}",
            "",
            f"This will {'PERMANENTLY DELETE' if permanent else 'MOVE TO QUARANTINE'} {len(delete_names)} item(s):",
        ]
        confirm_lines.extend(f"- {name}" for name in delete_names[:30])
        if len(delete_names) > 30:
            confirm_lines.append(f"... and {len(delete_names) - 30} more")

        if result.kept:
            confirm_lines.extend(["", "These will be kept automatically:"])
            for keep in result.kept[:20]:
                reason_bits = []
                if keep.shared_with_mods:
                    reason_bits.append(f"used by mods/maps: {', '.join(keep.shared_with_mods)}")
                if keep.shared_with_savegames:
                    reason_bits.append(f"used by savegames: {', '.join(keep.shared_with_savegames)}")
                confirm_lines.append(f"- {keep.mod.name} ({' | '.join(reason_bits)})")
            if len(result.kept) > 20:
                confirm_lines.append(f"... and {len(result.kept) - 20} more")

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
            self.set_status("Cleanup failed.")
            return

        summary = [f"Removed {len(removed)} item(s)."]
        summary.extend(f"- {name}" for name in removed)
        if quarantine_dir:
            summary.extend(["", f"Moved to: {quarantine_dir}"])
        if report_path:
            summary.extend(["", f"Report saved to: {report_path}"])

        self.log("\n".join(summary), clear=True)
        self.summary_var.set(f"Cleanup complete: removed {len(removed)} item(s).")
        self.set_status("Cleanup complete.")
        messagebox.showinfo(APP_NAME, "\n".join(summary[:20]))
        self.scan()

    def show_about(self) -> None:
        savegame_line = f"Protected savegames loaded: {len(self.savegame_folders)}"
        messagebox.showinfo(
            "About",
            f"{APP_NAME}\n\n"
            f"Version: {APP_VERSION}\n"
            f"Build: {APP_BUILD}\n\n"
            f"This tool helps remove a selected FS25 map and only the dependency mods that are no longer used by other installed maps/mods or selected savegames.\n\n"
            f"{savegame_line}",
        )


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
    parser.add_argument("--savegame", action="append", default=[], help="Optional savegame folder to protect. Can be used more than once.")
    args = parser.parse_args(argv)

    if not args.mods_folder or not args.target:
        parser.print_help()
        return 2

    mods_folder = Path(args.mods_folder)
    target_name = Path(args.target).stem
    mod_index = scan_mods_folder(mods_folder)
    result = analyze_target(target_name, mod_index, [Path(p) for p in args.savegame])
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
    app = MapCleanerApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
