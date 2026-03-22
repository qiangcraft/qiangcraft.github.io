#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Import an existing HTML post into posts/<category>/ and update index.html.

Usage:
  python3 tools/import_post.py --file /path/to/post.html --cat robotics
"""

from __future__ import annotations

import argparse
import html as html_lib
import math
import os
import re
import shutil
import webbrowser
from datetime import date, datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
POSTS = ROOT / "posts"

CATEGORIES = {
    "cs": {"name": "计算机基础", "class": "cat--cs"},
    "cpp": {"name": "C++", "class": "cat--cpp"},
    "robotics": {"name": "机器人", "class": "cat--robotics"},
    "personal": {"name": "随笔", "class": "cat--personal"},
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def strip_tags(s: str) -> str:
    s = re.sub(r"<[^>]+>", "", s)
    return html_lib.unescape(s).strip()


def normalize_inline_md(s: str) -> str:
    """Normalize common inline markdown typos like '** text**' -> '**text**'."""
    t = s or ""
    t = re.sub(r"\*\*\s+(.+?)\s*\*\*", r"**\1**", t)
    t = re.sub(r"(?<!\*)\*\s+(.+?)\s*\*(?!\*)", r"*\1*", t)
    return t


def strip_inline_md(s: str) -> str:
    t = normalize_inline_md(s)
    t = re.sub(r"\*\*(.+?)\*\*", r"\1", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", t)
    t = re.sub(r"`(.+?)`", r"\1", t)
    return t


def inline_md_to_html_safe(s: str) -> str:
    """Render a tiny safe subset for subtitle: **bold**, *italic*, `code`."""
    t = normalize_inline_md(s)
    t = html_lib.escape(t)
    t = re.sub(r"`([^`]+?)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", t)
    return t


def extract_first(html: str, pattern: str) -> str | None:
    m = re.search(pattern, html, re.S | re.I)
    if not m:
        return None
    return strip_tags(m.group(1))


def extract_attr(html: str, pattern: str) -> str | None:
    m = re.search(pattern, html, re.S | re.I)
    if not m:
        return None
    return html_lib.unescape(m.group(1)).strip()


def guess_title(html: str) -> str | None:
    # Prefer real title tag line; avoid matching <title> text inside HTML comments.
    m = re.search(r"(?im)^\s*<title>\s*([^<]+?)\s*</title>\s*$", html)
    title = m.group(1).strip() if m else None
    if title:
        return title.replace("— QiangCraft", "").strip()
    h1 = extract_first(html, r"<h1[^>]*>(.*?)</h1>")
    return h1


def guess_excerpt(html: str) -> str | None:
    meta = extract_attr(html, r"<meta\s+name=\"description\"\s+content=\"(.*?)\"")
    if meta:
        return meta
    sub = extract_first(html, r"<p\s+class=\"post-subtitle\"[^>]*>(.*?)</p>")
    if sub:
        return sub
    sub2 = extract_first(html, r"<p\s+class=\"subtitle\"[^>]*>(.*?)</p>")
    return sub2


def guess_date(html: str) -> str | None:
    d = extract_first(html, r"<span\s+class=\"post-head-date\"[^>]*>(.*?)</span>")
    if d:
        return d
    return None


def guess_read(html: str) -> str | None:
    r = extract_first(html, r"<span\s+class=\"post-head-read\"[^>]*>(.*?)</span>")
    return r


def prompt_if_missing(label: str, value: str | None, default: str | None = None) -> str:
    if value:
        return value
    prompt = f"{label}"
    if default:
        prompt += f" [默认: {default}]"
    prompt += ": "
    v = input(prompt).strip()
    if not v and default is not None:
        return default
    return v


def ui_pick_file() -> Optional[str]:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:
        return None
    root = tk.Tk()
    root.withdraw()
    path = filedialog.askopenfilename(
        title="选择要导入的 HTML 文件",
        filetypes=[("HTML files", "*.html"), ("All files", "*.*")]
    )
    root.destroy()
    return path or None


def ui_ask_string(title: str, prompt: str, default: str | None = None) -> Optional[str]:
    try:
        import tkinter as tk
        from tkinter import simpledialog
    except Exception:
        return None
    root = tk.Tk()
    root.withdraw()
    value = simpledialog.askstring(title, prompt, initialvalue=default)
    root.destroy()
    if value is None:
        return None
    return value.strip()


def ui_pick_category(default: str = "robotics") -> Optional[str]:
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        return None
    root = tk.Tk()
    root.title("选择分类")
    root.resizable(False, False)

    value = tk.StringVar(value=default)
    label = ttk.Label(root, text="选择分类 (cs/cpp/robotics/personal):")
    label.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="w")
    combo = ttk.Combobox(root, textvariable=value, values=list(CATEGORIES.keys()), state="readonly", width=24)
    combo.grid(row=1, column=0, padx=12, pady=(0, 8), sticky="w")

    result: Optional[str] = None

    def confirm() -> None:
        nonlocal result
        result = value.get().strip()
        root.destroy()

    def cancel() -> None:
        root.destroy()

    btns = ttk.Frame(root)
    btns.grid(row=2, column=0, padx=12, pady=(0, 12), sticky="e")
    ttk.Button(btns, text="确定", command=confirm).grid(row=0, column=0, padx=(0, 8))
    ttk.Button(btns, text="取消", command=cancel).grid(row=0, column=1)

    root.protocol("WM_DELETE_WINDOW", cancel)
    root.mainloop()
    return result


def ui_choose_mode() -> Optional[str]:
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        return None
    root = tk.Tk()
    root.title("QiangCraft · 导入文章")
    root.resizable(False, False)
    root.geometry("760x260")

    wrap = ttk.Frame(root, padding=16)
    wrap.pack(fill="both", expand=True)

    ttk.Label(wrap, text="选择导入方式", font=("Helvetica Neue", 16, "bold")).pack(anchor="w")
    ttk.Label(wrap, text="你可以导入现成 HTML，或用 Markdown 生成新文章。", foreground="#555").pack(anchor="w", pady=(4, 12))

    cards = ttk.Frame(wrap)
    cards.pack(fill="x", expand=True)
    cards.columnconfigure(0, weight=1)
    cards.columnconfigure(1, weight=1)
    cards.columnconfigure(2, weight=1)

    result: Optional[str] = None

    def pick_html() -> None:
        nonlocal result
        result = "html"
        root.destroy()

    def pick_md() -> None:
        nonlocal result
        result = "md"
        root.destroy()

    def pick_manage_tags() -> None:
        nonlocal result
        result = "manage_tags"
        root.destroy()

    card1 = ttk.Frame(cards, padding=12, relief="ridge")
    card1.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
    ttk.Label(card1, text="导入现成 HTML", font=("Helvetica Neue", 13, "bold")).pack(anchor="w")
    ttk.Label(card1, text="从已有的 .html 文件导入到 posts/<分类>/", foreground="#666").pack(anchor="w", pady=(4, 10))
    ttk.Button(card1, text="选择 HTML 文件", command=pick_html).pack(anchor="w")

    card2 = ttk.Frame(cards, padding=12, relief="ridge")
    card2.grid(row=0, column=1, padx=8, sticky="nsew")
    ttk.Label(card2, text="Markdown 生成", font=("Helvetica Neue", 13, "bold")).pack(anchor="w")
    ttk.Label(card2, text="用 Markdown 编辑器生成 HTML 并自动导入", foreground="#666").pack(anchor="w", pady=(4, 10))
    ttk.Button(card2, text="打开编辑器", command=pick_md).pack(anchor="w")

    card3 = ttk.Frame(cards, padding=12, relief="ridge")
    card3.grid(row=0, column=2, padx=(0, 0), sticky="nsew")
    ttk.Label(card3, text="已有文章标签管理", font=("Helvetica Neue", 13, "bold")).pack(anchor="w")
    ttk.Label(card3, text="编辑 posts 里已有 HTML 的标签", foreground="#666").pack(anchor="w", pady=(4, 10))
    ttk.Button(card3, text="管理标签", command=pick_manage_tags).pack(anchor="w")

    root.mainloop()
    return result


def load_existing_tags() -> list[str]:
    if not INDEX.exists():
        return []
    html = read_text(INDEX)
    m = re.search(r'<div class="tags-cloud">(.*?)</div>', html, re.S)
    if not m:
        return []
    inner = m.group(1)
    tags = re.findall(r'<span class="tag-pill">\s*(.*?)\s*</span>', inner, re.S)
    out = []
    seen = set()
    for t in tags:
        tt = html_lib.unescape(strip_tags(t)).strip()
        if tt and tt not in seen:
            seen.add(tt)
            out.append(tt)
    return out


def normalize_tags(tags: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for t in tags:
        tt = t.strip()
        if tt and tt not in seen:
            seen.add(tt)
            out.append(tt)
    return out


def extract_keywords_meta(html: str) -> list[str]:
    m = re.search(r'<meta\s+name=["\']keywords["\']\s+content=["\'](.*?)["\']\s*/?>', html, re.I | re.S)
    if not m:
        return []
    content = html_lib.unescape(m.group(1))
    return normalize_tags([s.strip() for s in content.split(",")])


def list_existing_post_files() -> list[Path]:
    items: list[Path] = []
    for cat in CATEGORIES.keys():
        cat_dir = POSTS / cat
        if not cat_dir.exists():
            continue
        for p in sorted(cat_dir.glob("*.html")):
            if p.name.startswith("_"):
                continue
            items.append(p)
    return sorted(items, key=lambda p: p.stat().st_mtime, reverse=True)


def ui_pick_existing_post_file() -> Optional[str]:
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        return None

    files = list_existing_post_files()
    if not files:
        return None

    root = tk.Tk()
    root.title("选择要管理标签的文章")
    root.geometry("920x560")

    wrap = ttk.Frame(root, padding=12)
    wrap.pack(fill="both", expand=True)

    ttk.Label(wrap, text="posts 文章列表（按修改时间倒序）").pack(anchor="w")
    search_var = tk.StringVar()
    ttk.Entry(wrap, textvariable=search_var).pack(fill="x", pady=(6, 8))

    cols = ("cat", "date", "title", "tags", "path")
    tree = ttk.Treeview(wrap, columns=cols, show="headings")
    tree.heading("cat", text="分类")
    tree.heading("date", text="日期")
    tree.heading("title", text="标题")
    tree.heading("tags", text="标签")
    tree.heading("path", text="路径")
    tree.column("cat", width=90, anchor="center")
    tree.column("date", width=110, anchor="center")
    tree.column("title", width=260, anchor="w")
    tree.column("tags", width=260, anchor="w")
    tree.column("path", width=320, anchor="w")
    tree.pack(fill="both", expand=True)

    records: list[dict] = []
    for p in files:
        html = read_text(p)
        cat = p.parent.name
        d = guess_date(html) or "-"
        title = guess_title(html) or p.stem
        tags = ", ".join(extract_keywords_meta(html)) or "-"
        rel = str(p.relative_to(ROOT)).replace(os.sep, "/")
        records.append({"cat": cat, "date": d, "title": title, "tags": tags, "path": rel, "abs": str(p)})

    def refill() -> None:
        q = search_var.get().strip().lower()
        tree.delete(*tree.get_children())
        for r in records:
            if q and q not in (r["cat"] + " " + r["date"] + " " + r["title"] + " " + r["tags"] + " " + r["path"]).lower():
                continue
            tree.insert("", "end", values=(r["cat"], r["date"], r["title"], r["tags"], r["path"]))

    refill()
    search_var.trace_add("write", lambda *_: refill())

    result: Optional[str] = None

    def pick() -> None:
        nonlocal result
        sel = tree.selection()
        cur = sel[0] if sel else tree.focus()
        if not cur:
            return
        vals = tree.item(cur, "values")
        path_rel = vals[4] if len(vals) >= 5 else None
        if not path_rel:
            return
        result = str((ROOT / path_rel).resolve())
        root.destroy()

    def cancel() -> None:
        root.destroy()

    btns = ttk.Frame(wrap)
    btns.pack(fill="x", pady=(8, 0))
    ttk.Button(btns, text="选择", command=pick).pack(side="left")
    ttk.Button(btns, text="取消", command=cancel).pack(side="left", padx=(8, 0))

    tree.bind("<Double-1>", lambda _e: pick())
    root.protocol("WM_DELETE_WINDOW", cancel)
    root.mainloop()
    return result


def ui_edit_post_tags(file_path: str, *, existing_tags: list[str], initial_tags: list[str]) -> Optional[list[str]]:
    try:
        import tkinter as tk
        from tkinter import ttk
    except Exception:
        return None

    root = tk.Tk()
    root.title("管理文章标签")
    root.geometry("760x520")

    wrap = ttk.Frame(root, padding=12)
    wrap.pack(fill="both", expand=True)

    ttk.Label(wrap, text="文章").pack(anchor="w")
    path_var = tk.StringVar(value=file_path)
    ttk.Entry(wrap, textvariable=path_var, state="readonly", width=100).pack(fill="x", pady=(4, 8))

    tags_wrap = ttk.LabelFrame(wrap, text="标签（可多选）", padding=12)
    tags_wrap.pack(fill="both", expand=True)

    tags_list = tk.Listbox(tags_wrap, selectmode="multiple", height=14, exportselection=False)
    tags_list.grid(row=0, column=0, columnspan=3, sticky="nsew")
    tags_wrap.columnconfigure(0, weight=1)
    tags_wrap.rowconfigure(0, weight=1)

    combined = normalize_tags(existing_tags + initial_tags)
    for t in combined:
        tags_list.insert("end", t)
    for i, t in enumerate(tags_list.get(0, "end")):
        if t in initial_tags:
            tags_list.selection_set(i)

    new_tag_var = tk.StringVar()
    ttk.Entry(tags_wrap, textvariable=new_tag_var, width=24).grid(row=1, column=0, sticky="w", pady=(8, 0))

    def add_tag() -> None:
        tag = new_tag_var.get().strip()
        if not tag:
            return
        values = tags_list.get(0, "end")
        if tag not in values:
            tags_list.insert("end", tag)
            idx = tags_list.size() - 1
        else:
            idx = values.index(tag)
        tags_list.selection_set(idx)
        new_tag_var.set("")

    ttk.Button(tags_wrap, text="新建标签", command=add_tag).grid(row=1, column=1, padx=(8, 0), pady=(8, 0), sticky="w")
    ttk.Label(tags_wrap, text="不选即清空该文章标签").grid(row=1, column=2, padx=(8, 0), pady=(8, 0), sticky="w")

    result: Optional[list[str]] = None

    def submit() -> None:
        nonlocal result
        selected = [tags_list.get(i) for i in tags_list.curselection()]
        result = normalize_tags(selected)
        root.destroy()

    def cancel() -> None:
        root.destroy()

    btns = ttk.Frame(wrap)
    btns.pack(fill="x", pady=(10, 0))
    ttk.Button(btns, text="保存", command=submit).pack(side="left")
    ttk.Button(btns, text="取消", command=cancel).pack(side="left", padx=(8, 0))

    root.protocol("WM_DELETE_WINDOW", cancel)
    root.mainloop()
    return result


def ui_html_import_form(
    *,
    file_path: str,
    default_cat: str,
    default_title: str,
    default_excerpt: str,
    default_date: str,
    default_meta: str,
    existing_tags: list[str],
) -> Optional[dict]:
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except Exception:
        return None

    root = tk.Tk()
    root.title("导入 HTML 文章")
    root.geometry("860x660")

    form = ttk.Frame(root, padding=12)
    form.pack(fill="x")

    ttk.Label(form, text="文件").grid(row=0, column=0, sticky="w")
    file_var = tk.StringVar(value=file_path)
    ttk.Entry(form, textvariable=file_var, state="readonly", width=82).grid(row=0, column=1, columnspan=3, padx=(8, 0), sticky="we")

    ttk.Label(form, text="分类").grid(row=1, column=0, sticky="w", pady=(8, 0))
    cat_var = tk.StringVar(value=default_cat or "robotics")
    ttk.Combobox(form, textvariable=cat_var, values=list(CATEGORIES.keys()), state="readonly", width=18).grid(row=1, column=1, padx=(8, 0), pady=(8, 0), sticky="w")

    ttk.Label(form, text="日期").grid(row=1, column=2, sticky="e", pady=(8, 0))
    date_var = tk.StringVar(value=default_date)
    ttk.Entry(form, textvariable=date_var, width=20).grid(row=1, column=3, padx=(8, 0), pady=(8, 0), sticky="w")

    ttk.Label(form, text="标题").grid(row=2, column=0, sticky="w", pady=(8, 0))
    title_var = tk.StringVar(value=default_title)
    ttk.Entry(form, textvariable=title_var, width=82).grid(row=2, column=1, columnspan=3, padx=(8, 0), pady=(8, 0), sticky="we")

    ttk.Label(form, text="摘要").grid(row=3, column=0, sticky="nw", pady=(8, 0))
    excerpt_text = tk.Text(form, height=4, wrap="word")
    excerpt_text.grid(row=3, column=1, columnspan=3, padx=(8, 0), pady=(8, 0), sticky="we")
    excerpt_text.insert("1.0", default_excerpt)

    ttk.Label(form, text="元信息").grid(row=4, column=0, sticky="w", pady=(8, 0))
    meta_var = tk.StringVar(value=default_meta)
    ttk.Entry(form, textvariable=meta_var, width=24).grid(row=4, column=1, padx=(8, 0), pady=(8, 0), sticky="w")
    ttk.Label(form, text="(自动计算，可修改)").grid(row=4, column=2, columnspan=2, sticky="w", pady=(8, 0))

    tags_wrap = ttk.LabelFrame(root, text="标签", padding=12)
    tags_wrap.pack(fill="both", expand=True, padx=12, pady=(8, 0))

    listbox = tk.Listbox(tags_wrap, selectmode="multiple", height=10, exportselection=False)
    listbox.grid(row=0, column=0, columnspan=3, sticky="nsew")
    for t in existing_tags:
        listbox.insert("end", t)

    tags_wrap.columnconfigure(0, weight=1)
    tags_wrap.columnconfigure(1, weight=0)
    tags_wrap.columnconfigure(2, weight=0)
    tags_wrap.rowconfigure(0, weight=1)

    new_tag_var = tk.StringVar()
    ttk.Entry(tags_wrap, textvariable=new_tag_var, width=24).grid(row=1, column=0, sticky="w", pady=(8, 0))

    def add_tag() -> None:
        tag = new_tag_var.get().strip()
        if not tag:
            return
        values = listbox.get(0, "end")
        if tag not in values:
            listbox.insert("end", tag)
        idx = listbox.get(0, "end").index(tag)
        listbox.selection_set(idx)
        new_tag_var.set("")

    ttk.Button(tags_wrap, text="新建标签", command=add_tag).grid(row=1, column=1, padx=(8, 0), pady=(8, 0), sticky="w")
    ttk.Label(tags_wrap, text="可多选").grid(row=1, column=2, padx=(8, 0), pady=(8, 0), sticky="w")

    btns = ttk.Frame(root, padding=12)
    btns.pack(fill="x")

    result: Optional[dict] = None

    def submit() -> None:
        nonlocal result
        cat = cat_var.get().strip()
        title = title_var.get().strip()
        excerpt = excerpt_text.get("1.0", "end").strip()
        d = date_var.get().strip()
        meta = meta_var.get().strip()
        if cat not in CATEGORIES:
            messagebox.showerror("分类错误", "请选择有效分类")
            return
        if not title:
            messagebox.showerror("标题为空", "请填写标题")
            return
        if not excerpt:
            messagebox.showerror("摘要为空", "请填写摘要")
            return
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", d):
            messagebox.showerror("日期格式错误", "请使用 YYYY-MM-DD")
            return
        selected = [listbox.get(i) for i in listbox.curselection()]
        result = {
            "cat": cat,
            "title": title,
            "excerpt": excerpt,
            "date": d,
            "meta": meta or default_meta,
            "tags": selected,
        }
        root.destroy()

    def cancel() -> None:
        root.destroy()

    ttk.Button(btns, text="导入", command=submit).pack(side="right")
    ttk.Button(btns, text="取消", command=cancel).pack(side="right", padx=(0, 8))

    root.protocol("WM_DELETE_WINDOW", cancel)
    root.mainloop()
    return result


def ui_markdown_import(
    default_filename: str,
    default_cat: str,
    default_md: str,
    template_html: str,
    *,
    existing_tags: list[str],
) -> Optional[dict]:
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox
    except Exception:
        return None

    root = tk.Tk()
    root.title("导入 Markdown 生成文章")
    root.geometry("860x680")

    form = ttk.Frame(root, padding=12)
    form.pack(fill="x")

    ttk.Label(form, text="文件名（不含路径）").grid(row=0, column=0, sticky="w")
    filename_var = tk.StringVar(value=default_filename)
    filename_entry = ttk.Entry(form, textvariable=filename_var, width=40)
    filename_entry.grid(row=0, column=1, sticky="w", padx=(8, 0))

    ttk.Label(form, text="分类").grid(row=0, column=2, sticky="w", padx=(16, 0))
    cat_var = tk.StringVar(value=default_cat)
    cat_combo = ttk.Combobox(form, textvariable=cat_var, values=list(CATEGORIES.keys()), state="readonly", width=18)
    cat_combo.grid(row=0, column=3, sticky="w", padx=(8, 0))

    editor_wrap = ttk.Frame(root, padding=(12, 6))
    editor_wrap.pack(fill="both", expand=True)

    ttk.Label(editor_wrap, text="Markdown 内容").pack(anchor="w")
    text = tk.Text(editor_wrap, wrap="word")
    text.pack(fill="both", expand=True, pady=(6, 0))
    text.insert("1.0", default_md)

    tags_wrap = ttk.LabelFrame(root, text="标签", padding=12)
    tags_wrap.pack(fill="both", expand=False, padx=12, pady=(8, 0))

    tags_list = tk.Listbox(tags_wrap, selectmode="multiple", height=6, exportselection=False)
    tags_list.grid(row=0, column=0, columnspan=3, sticky="nsew")
    for t in existing_tags:
        tags_list.insert("end", t)

    tags_wrap.columnconfigure(0, weight=1)
    tags_wrap.rowconfigure(0, weight=1)

    new_tag_var = tk.StringVar()
    ttk.Entry(tags_wrap, textvariable=new_tag_var, width=24).grid(row=1, column=0, sticky="w", pady=(8, 0))

    def add_tag() -> None:
        tag = new_tag_var.get().strip()
        if not tag:
            return
        values = tags_list.get(0, "end")
        if tag not in values:
            tags_list.insert("end", tag)
        idx = tags_list.get(0, "end").index(tag)
        tags_list.selection_set(idx)
        new_tag_var.set("")

    ttk.Button(tags_wrap, text="新建标签", command=add_tag).grid(row=1, column=1, padx=(8, 0), pady=(8, 0), sticky="w")
    ttk.Label(tags_wrap, text="可多选").grid(row=1, column=2, padx=(8, 0), pady=(8, 0), sticky="w")

    btns = ttk.Frame(root, padding=12)
    btns.pack(fill="x")

    result: Optional[dict] = None

    def preview() -> None:
        md = text.get("1.0", "end").strip("\n")
        if not md.strip():
            messagebox.showwarning("内容为空", "请先输入 Markdown 内容")
            return
        cat = cat_var.get().strip()
        if not cat or cat not in CATEGORIES:
            messagebox.showwarning("分类错误", "请选择有效分类")
            return

        fm, md_body = parse_front_matter(md)
        title = fm.get("title") or extract_title(md_body) or "未命名文章"
        excerpt = fm.get("description") or fm.get("excerpt") or extract_excerpt(md_body) or "新文章"
        date_str = fm.get("date") or date.today().isoformat()
        read_label = fm.get("read") or estimate_read_time(md_body)

        md_clean = clean_markdown_body(md_body, title, excerpt)
        html_out = apply_template(
            template_html,
            title=title,
            excerpt=excerpt,
            date_str=date_str,
            read_text=read_label,
            cat=cat,
            markdown=md_clean,
        )

        prev = tk.Toplevel(root)
        prev.title("预览 HTML")
        prev.geometry("860x640")
        pwrap = ttk.Frame(prev, padding=12)
        pwrap.pack(fill="both", expand=True)
        ptext = tk.Text(pwrap, wrap="none")
        ptext.pack(fill="both", expand=True)
        ptext.insert("1.0", html_out)
        ptext.configure(state="disabled")

    def preview_browser() -> None:
        md = text.get("1.0", "end").strip("\n")
        if not md.strip():
            messagebox.showwarning("内容为空", "请先输入 Markdown 内容")
            return
        cat = cat_var.get().strip()
        if not cat or cat not in CATEGORIES:
            messagebox.showwarning("分类错误", "请选择有效分类")
            return

        fm, md_body = parse_front_matter(md)
        title = fm.get("title") or extract_title(md_body) or "未命名文章"
        excerpt = fm.get("description") or fm.get("excerpt") or extract_excerpt(md_body) or "新文章"
        date_str = fm.get("date") or date.today().isoformat()
        read_text = fm.get("read") or estimate_read_time(md_body)

        md_clean = clean_markdown_body(md_body, title, excerpt)
        html_out = apply_template(
            template_html,
            title=title,
            excerpt=excerpt,
            date_str=date_str,
            read_text=read_text,
            cat=cat,
            markdown=md_clean,
        )
        # write preview into posts/<cat>/ to keep relative assets working
        preview_path = POSTS / cat / "_preview.html"
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_text(html_out, encoding="utf-8")
        webbrowser.open(f"file://{preview_path}")

    def submit() -> None:
        nonlocal result
        filename = filename_var.get().strip()
        cat = cat_var.get().strip()
        md = text.get("1.0", "end").strip("\n")
        if not filename:
            messagebox.showerror("缺少文件名", "请输入文件名，例如 my-post.html")
            return
        if not cat or cat not in CATEGORIES:
            messagebox.showerror("分类错误", "请选择有效分类")
            return
        if not md.strip():
            messagebox.showerror("内容为空", "请填写 Markdown 内容")
            return
        result = {
            "filename": filename,
            "cat": cat,
            "markdown": md,
            "tags": [tags_list.get(i) for i in tags_list.curselection()],
        }
        root.destroy()

    def cancel() -> None:
        root.destroy()

    ttk.Button(btns, text="生成并导入", command=submit).pack(side="right")
    ttk.Button(btns, text="浏览器预览", command=preview_browser).pack(side="right", padx=(0, 8))
    ttk.Button(btns, text="预览 HTML", command=preview).pack(side="right", padx=(0, 8))
    ttk.Button(btns, text="取消", command=cancel).pack(side="right", padx=(0, 8))

    root.protocol("WM_DELETE_WINDOW", cancel)
    root.mainloop()
    return result


def parse_front_matter(md: str) -> tuple[dict, str]:
    lines = md.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, md
    meta = {}
    i = 1
    while i < len(lines):
        line = lines[i].strip()
        if line == "---":
            body = "\n".join(lines[i + 1 :])
            return meta, body
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip()
        i += 1
    return {}, md


def extract_title(md: str) -> Optional[str]:
    for line in md.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def extract_excerpt(md: str) -> Optional[str]:
    lines = md.splitlines()
    in_code = False
    para = []
    for line in lines:
        l = line.rstrip()
        if l.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not l.strip():
            if para:
                break
            continue
        if re.match(r"^#{1,6}\s+", l):
            continue
        if re.match(r"^(\-|\*|\d+\.)\s+", l):
            continue
        if l.strip().startswith(">"):
            continue
        para.append(l.strip())
    if not para:
        return None
    return " ".join(para)


def estimate_read_time(md: str) -> str:
    # remove code fences
    md = re.sub(r"```.*?```", "", md, flags=re.S)
    md = re.sub(r"`[^`]+`", "", md)
    cjk = len(re.findall(r"[\u4e00-\u9fff]", md))
    words = len(re.findall(r"[A-Za-z0-9]+", md))
    # Mixed-language estimate:
    # Chinese reading speed ~300 chars/min, English ~200 words/min.
    mins = max(1, int(math.ceil((cjk / 300) + (words / 200))))
    return f"约 {mins} 分钟"


def estimate_read_time_from_html(html: str) -> str:
    # Remove non-content blocks first.
    txt = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    txt = re.sub(r"<style[\s\S]*?</style>", " ", txt, flags=re.I)
    # Strip tags and collapse spaces.
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = html_lib.unescape(txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    cjk = len(re.findall(r"[\u4e00-\u9fff]", txt))
    words = len(re.findall(r"[A-Za-z0-9]+", txt))
    mins = max(1, int(math.ceil((cjk / 300) + (words / 200))))
    return f"约 {mins} 分钟"


def _norm_text(s: str) -> str:
    return re.sub(r"\s+", "", (s or "")).strip().lower()


def clean_markdown_body(md: str, title: str, excerpt: str) -> str:
    lines = md.splitlines()
    i = 0

    # Drop leading blank lines
    while i < len(lines) and not lines[i].strip():
        i += 1

    # Drop first H1 if it duplicates hero title
    if i < len(lines):
        m = re.match(r"^#\s+(.*)$", lines[i].strip())
        if m and _norm_text(m.group(1)) == _norm_text(title):
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1

    # Drop first paragraph if it duplicates hero subtitle/excerpt
    j = i
    para = []
    while j < len(lines) and lines[j].strip() and not re.match(r"^#{1,6}\s+", lines[j].strip()):
        if lines[j].strip().startswith("```"):
            break
        para.append(lines[j].strip())
        j += 1
    if para and _norm_text(" ".join(para)) == _norm_text(excerpt):
        i = j
        while i < len(lines) and not lines[i].strip():
            i += 1

    return "\n".join(lines[i:]).strip()


def apply_template(template_html: str, *, title: str, excerpt: str, date_str: str, read_text: str, cat: str, markdown: str) -> str:
    safe_title = html_lib.escape(title)
    safe_excerpt_meta = html_lib.escape(strip_inline_md(excerpt))
    safe_excerpt_html = inline_md_to_html_safe(excerpt)
    safe_md = markdown.replace("</script>", "<\\/script>")

    out = template_html
    out = re.sub(r"(?m)^<title>.*?</title>", f"<title>{safe_title} — QiangCraft</title>", out, count=1, flags=re.S)
    out = re.sub(r"(?m)^<meta name=\"description\" content=\".*?\"/>",
                 f"<meta name=\"description\" content=\"{safe_excerpt_meta}\"/>", out, count=1, flags=re.S)
    out = re.sub(r"(<span class=\"post-head-date\">).*?(</span>)", rf"\g<1>{date_str}\g<2>", out, count=1, flags=re.S)
    out = re.sub(r"(<span class=\"post-head-read\">).*?(</span>)", rf"\g<1>{read_text}\g<2>", out, count=1, flags=re.S)
    out = re.sub(r"(<h1 class=\"post-title\">).*?(</h1>)", rf"\g<1>{safe_title}\g<2>", out, count=1, flags=re.S)
    out = re.sub(r"(<p class=\"post-subtitle\">).*?(</p>)", rf"\g<1>{safe_excerpt_html}\g<2>", out, count=1, flags=re.S)

    cat_name = CATEGORIES[cat]["name"]
    cat_class = CATEGORIES[cat]["class"]
    out = re.sub(
        r"<span class=\"cat cat--[^\"]+\"><span class=\"cat-dot\"></span>.*?</span>",
        f"<span class=\"cat {cat_class}\"><span class=\"cat-dot\"></span>{cat_name}</span>",
        out,
        count=1,
        flags=re.S,
    )

    def repl_script(m: re.Match) -> str:
        open_tag, _, close_tag = m.group(1), m.group(2), m.group(3)
        return f"{open_tag}\n\n{safe_md}\n\n          {close_tag}"

    out = re.sub(r"(<script type=\"text/markdown\"[^>]*>)(.*?)(</script>)", repl_script, out, count=1, flags=re.S)
    return out


def adjust_relative_paths(html: str) -> str:
    # normalize assets/index paths for posts/<cat>/
    html = re.sub(r'href=\"\.\./assets/', 'href="../../assets/', html)
    html = re.sub(r'src=\"\.\./assets/', 'src="../../assets/', html)
    html = re.sub(r'href=\"\.\./index\.html\"', 'href="../../index.html"', html)
    html = re.sub(r'href=\"index\.html\"', 'href="../../index.html"', html)
    return html


def set_keywords_meta(html: str, tags: list[str]) -> str:
    tags = normalize_tags(tags)
    meta_re = r'<meta\s+name=["\']keywords["\']\s+content=["\'].*?["\']\s*/?>'
    if not tags:
        return re.sub(meta_re + r'\n?', "", html, count=1, flags=re.I)

    content = html_lib.escape(", ".join(tags), quote=True)
    meta_tag = f'<meta name="keywords" content="{content}"/>'
    if re.search(meta_re, html, re.I):
        return re.sub(meta_re, meta_tag, html, count=1, flags=re.I)
    if re.search(r'<meta\s+name="description"\s+content=".*?"\s*/?>', html, re.I):
        return re.sub(r'(<meta\s+name="description"\s+content=".*?"\s*/?>)', r'\1\n' + meta_tag, html, count=1, flags=re.I)
    return re.sub(r'(<head\b[^>]*>)', r'\1\n' + meta_tag, html, count=1, flags=re.I)


def apply_keywords_meta(html: str, tags: list[str]) -> str:
    return set_keywords_meta(html, tags)


def normalize_subtitle_inline_md(html: str) -> str:
    def repl(m: re.Match) -> str:
        open_tag, inner, close_tag = m.group(1), m.group(2), m.group(3)
        # Already contains HTML tags (e.g. <strong>) -> keep as is.
        if "<" in inner and ">" in inner:
            return m.group(0)
        text = html_lib.unescape(inner)
        return f"{open_tag}{inline_md_to_html_safe(text)}{close_tag}"

    return re.sub(
        r'(<p\s+class="post-subtitle"[^>]*>)(.*?)(</p>)',
        repl,
        html,
        count=1,
        flags=re.S | re.I,
    )


def update_tags_cloud(index_html: str, new_tags: list[str]) -> str:
    new_tags = normalize_tags(new_tags)
    if not new_tags:
        return index_html
    m = re.search(r'(<div class="tags-cloud">)(.*?)(</div>)', index_html, re.S)
    if not m:
        return index_html
    inner = m.group(2)
    old = re.findall(r'<span class="tag-pill">\s*(.*?)\s*</span>', inner, re.S)
    tags = []
    seen = set()
    for t in old + new_tags:
        tt = html_lib.unescape(strip_tags(t)).strip()
        if tt and tt not in seen:
            seen.add(tt)
            tags.append(tt)
    rebuilt = "".join(f'<span class="tag-pill">{html_lib.escape(t)}</span>' for t in tags)
    return index_html[:m.start(2)] + rebuilt + index_html[m.end(2):]


def rebuild_tags_cloud_from_cards(index_html: str) -> str:
    anchor_re = r'<a\b[^>]*class="[^"]*\bpost-card\b[^"]*"[^>]*>'
    tags: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(anchor_re, index_html, re.I):
        tag = m.group(0)
        mt = re.search(r'data-tags="([^"]*)"', tag, re.I)
        if not mt:
            continue
        for t in mt.group(1).split(","):
            tt = html_lib.unescape(t).strip()
            if tt and tt not in seen:
                seen.add(tt)
                tags.append(tt)

    m = re.search(r'(<div class="tags-cloud">)(.*?)(</div>)', index_html, re.S)
    if not m:
        return index_html
    rebuilt = "".join(f'<span class="tag-pill">{html_lib.escape(t)}</span>' for t in tags)
    return index_html[:m.start(2)] + rebuilt + index_html[m.end(2):]


def update_card_tags(index_html: str, href: str, tags: list[str]) -> tuple[str, bool]:
    href_escaped = html_lib.escape(href, quote=True)
    anchor_re = rf'(<a\b[^>]*\bhref="{re.escape(href_escaped)}"[^>]*\bclass="[^"]*\bpost-card\b[^"]*"[^>]*>)'
    m = re.search(anchor_re, index_html, re.I)
    if not m:
        return index_html, False

    tag = m.group(1)
    norm_tags = normalize_tags(tags)
    if norm_tags:
        attr_value = html_lib.escape(",".join(norm_tags), quote=True)
        if re.search(r'\sdata-tags="[^"]*"', tag, re.I):
            new_tag = re.sub(r'\sdata-tags="[^"]*"', f' data-tags="{attr_value}"', tag, count=1, flags=re.I)
        else:
            new_tag = tag[:-1] + f' data-tags="{attr_value}">'
    else:
        new_tag = re.sub(r'\sdata-tags="[^"]*"', "", tag, count=1, flags=re.I)

    return index_html[:m.start(1)] + new_tag + index_html[m.end(1):], True


def inject_template_elements(
    html: str,
    template_html: str,
    *,
    cat: str | None = None,
    current_name: str | None = None,
) -> str:
    """Inject/replace structural template elements (header, footer, wechat modal, scripts)
    from the site template into an imported HTML post."""

    def extract_block(src: str, open_re: str, close_tag: str) -> str | None:
        m = re.search(open_re, src, re.I | re.S)
        if not m:
            return None
        start = m.start()
        end = src.find(close_tag, m.end())
        if end == -1:
            return None
        return src[start : end + len(close_tag)]

    # ── Extract template sections ────────────────────────────────────────
    tmpl_header = extract_block(template_html, r'<header\b', '</header>')
    tmpl_footer = extract_block(template_html, r'<footer\b', '</footer>')

    # WeChat modal: outer div ends right before the first <script> block
    wm = re.search(r'(<div class="wechat-modal"[\s\S]*?</div>)\s*\n\n<script', template_html)
    tmpl_wechat = wm.group(1) if wm else None

    # ── 1. Header (nav) ─────────────────────────────────────────────────
    if tmpl_header:
        existing = extract_block(html, r'<header\b', '</header>')
        if existing:
            html = html.replace(existing, tmpl_header, 1)
        else:
            html = re.sub(
                r'(<body\b[^>]*>)',
                r'\1\n\n' + tmpl_header + '\n',
                html, count=1, flags=re.I,
            )

    # ── 2. Footer ────────────────────────────────────────────────────────
    if tmpl_footer:
        existing = extract_block(html, r'<footer\b', '</footer>')
        if existing:
            html = html.replace(existing, tmpl_footer, 1)
        else:
            html = html.replace('</body>', tmpl_footer + '\n\n</body>', 1)

    # ── 3. WeChat modal ──────────────────────────────────────────────────
    if tmpl_wechat and 'wechat-modal' not in html:
        m2 = re.search(r'<script\b', html)
        if m2:
            html = html[: m2.start()] + tmpl_wechat + '\n\n' + html[m2.start() :]
        else:
            html = html.replace('</body>', tmpl_wechat + '\n\n</body>', 1)

    # ── 4. favicon ─────────────────────────────────────────────────────────
    if 'rel="icon"' not in html:
        html = re.sub(
            r'(<meta\s+name="viewport"[^>]*>\s*)',
            r'\1<link rel="icon" type="image/svg+xml" href="../../assets/favicon.svg"/>\n',
            html, count=1, flags=re.I,
        )

    # ── 5. CSS / font assets ──────────────────────────────────────────────
    # Inject style.css FIRST (right after <head>) so original inline <style>
    # blocks appear later in the cascade and keep their design intact.
    # Only IBM Plex Mono is needed for the header — skip Noto Sans SC to
    # avoid CJK font-fallback issues (Korean glyphs, etc.).
    fonts_tag = (
        '<link rel="preconnect" href="https://fonts.googleapis.com"/>\n'
        '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono'
        ':ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap" rel="stylesheet"/>'
    )
    if 'assets/style.css' not in html:
        html = re.sub(
            r'(<head\b[^>]*>)',
            r'\1\n' + fonts_tag + '\n<link rel="stylesheet" href="../../assets/style.css"/>',
            html, count=1, flags=re.I,
        )

    # ── 6. JS assets ─────────────────────────────────────────────────────
    js_deps = [
        ('cdn.jsdelivr.net/npm/marked',
         '<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>'),
        ('highlight.js/11',
         '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.11.1/highlight.min.js"></script>'),
        ('assets/main.js',
         '<script src="../../assets/main.js"></script>'),
    ]
    for needle, tag in js_deps:
        if needle not in html:
            html = html.replace('</body>', tag + '\n</body>', 1)

    # ── 7. Auto prev/next for current imported post ──────────────────────
    if cat and current_name:
        cat_dir = POSTS / cat
        if cat_dir.exists():
            posts = []
            for path in sorted(cat_dir.glob("*.html")):
                if path.name.startswith("_"):
                    continue
                try:
                    p_html = read_text(path)
                except Exception:
                    continue
                p_title = (
                    extract_first(p_html, r"<h1[^>]*class=\"post-title\"[^>]*>(.*?)</h1>")
                    or extract_first(p_html, r"<h1[^>]*>(.*?)</h1>")
                    or guess_title(p_html)
                    or path.stem
                )
                p_date = parse_iso_date(guess_date(p_html))
                if p_date is None:
                    p_date = datetime.fromtimestamp(path.stat().st_mtime).date()
                posts.append({"name": path.name, "title": p_title, "date": p_date})

            posts.sort(key=lambda x: (x["date"], x["name"]), reverse=True)
            idx = next((i for i, p in enumerate(posts) if p["name"] == current_name), -1)
            if idx >= 0:
                newer = posts[idx - 1] if idx - 1 >= 0 else None
                older = posts[idx + 1] if idx + 1 < len(posts) else None
                html = replace_nav_link(html, "prev", render_nav_link("prev", newer))
                html = replace_nav_link(html, "next", render_nav_link("next", older))

    # ── 8. Normalize inline markdown inside subtitle ─────────────────────
    html = normalize_subtitle_inline_md(html)

    return html


def insert_card(index_html: str, card_html: str) -> str:
    if card_html.strip() in index_html:
        return index_html
    # insert after featured card if present
    m = re.search(r"<a[^>]*post-card--featured[^>]*>.*?</a>", index_html, re.S)
    if m:
        insert_at = m.end()
        return index_html[:insert_at] + card_html + index_html[insert_at:]
    # otherwise insert right after posts-grid opening
    m = re.search(r"<div class=\"posts-grid[^>]*>\s*", index_html)
    if m:
        insert_at = m.end()
        return index_html[:insert_at] + card_html + index_html[insert_at:]
    raise RuntimeError("未找到 posts-grid 位置，无法插入卡片")


def update_counts(index_html: str) -> str:
    cards = re.findall(r"<a[^>]*class=\"post-card[^\"]*\"[^>]*data-cat=\"([^\"]+)\"", index_html)
    total = len(cards)
    counts = {k: 0 for k in CATEGORIES}
    for c in cards:
        if c in counts:
            counts[c] += 1

    # total counts
    index_html = re.sub(r"(<span class=\"posts-count\" id=\"post-count\">)\d+\s*篇(</span>)",
                        rf"\g<1>{total} 篇\2", index_html)
    index_html = re.sub(r"(<span class=\"pk\">total</span><span class=\"pv\">)\d+\s*篇(</span>)",
                        rf"\g<1>{total} 篇\2", index_html)

    # per-category counts in hero panel
    for cat, meta in CATEGORIES.items():
        name = meta["name"]
        index_html = re.sub(
            rf"(<span class=\"pk\">{re.escape(name)}</span><span class=\"pv[^\"]*\">)\d+\s*篇(</span>)",
            rf"\g<1>{counts[cat]} 篇\2",
            index_html
        )

    # sidebar topic counts
    for cat, meta in CATEGORIES.items():
        index_html = re.sub(
            rf"(<div class=\"topic-row\" data-filter=\"{re.escape(cat)}\".*?<span class=\"t-count\">)\d+(</span>)",
            rf"\g<1>{counts[cat]}\2",
            index_html,
            flags=re.S
        )

    # update percentages in pbar-labels
    def pct(n: int) -> int:
        if total == 0:
            return 0
        return int(round(n * 100 / total))

    for cat, meta in CATEGORIES.items():
        name = meta["name"]
        index_html = re.sub(
            rf"(<div class=\"pbar-label\"><span>{re.escape(name)}</span><span>)\d+%(</span></div>)",
            rf"\g<1>{pct(counts[cat])}%\2",
            index_html
        )

    return index_html


def build_card(
    href: str,
    cat: str,
    title: str,
    excerpt: str,
    date_str: str,
    meta_text: str,
    tags: Optional[list[str]] = None,
) -> str:
    cat_name = CATEGORIES[cat]["name"]
    cat_class = CATEGORIES[cat]["class"]
    tag_attr = ""
    if tags:
        safe = [t.strip() for t in tags if t.strip()]
        if safe:
            tag_attr = f' data-tags="{html_lib.escape(",".join(safe), quote=True)}"'
    # keep indentation consistent with index.html (8 spaces)
    return (
        "\n\n        <!-- {cat_name} -->\n"
        "        <a href=\"{href}\" class=\"post-card\" data-cat=\"{cat}\"{tag_attr}>\n"
        "          <div class=\"pc-top\"><span class=\"cat {cat_class}\"><span class=\"cat-dot\"></span>{cat_name}</span><span class=\"post-date\">{date}</span></div>\n"
        "          <h2 class=\"post-title\">{title}</h2>\n"
        "          <p class=\"post-excerpt\">{excerpt}</p>\n"
        "          <div class=\"pc-footer\"><span class=\"post-meta\">{meta}</span><span class=\"post-arrow\">↗</span></div>\n"
        "        </a>"
    ).format(
        cat_name=cat_name,
        href=href,
        cat=cat,
        tag_attr=tag_attr,
        cat_class=cat_class,
        date=date_str,
        title=title,
        excerpt=excerpt,
        meta=meta_text,
    )


def parse_iso_date(s: str | None) -> Optional[date]:
    if not s:
        return None
    try:
        return datetime.strptime(s.strip(), "%Y-%m-%d").date()
    except Exception:
        return None


def render_nav_link(kind: str, item: Optional[dict]) -> str:
    if kind == "prev":
        label = "← 上一篇"
        cls = "post-nav-link post-nav-link--prev"
    else:
        label = "下一篇 →"
        cls = "post-nav-link post-nav-link--next"

    if not item:
        return (
            f'<a href="#" class="{cls}" style="pointer-events:none;opacity:.45">'
            f'<span class="post-nav-label">{label}</span>'
            f'<span class="post-nav-title">暂无</span>'
            f"</a>"
        )

    return (
        f'<a href="./{item["name"]}" class="{cls}">'
        f'<span class="post-nav-label">{label}</span>'
        f'<span class="post-nav-title">{html_lib.escape(item["title"])}</span>'
        f"</a>"
    )


def replace_nav_link(html: str, kind: str, replacement: str) -> str:
    cls = "post-nav-link--prev" if kind == "prev" else "post-nav-link--next"
    # Be tolerant to class order/additional classes/attributes.
    pat = rf'<a\b[^>]*class="[^"]*\b{cls}\b[^"]*"[^>]*>.*?</a>'
    m = re.search(r'(<nav\b[^>]*class="[^"]*\bpost-footer-nav\b[^"]*"[^>]*>)(.*?)(</nav>)', html, re.S | re.I)
    if not m:
        return html
    body = m.group(2)
    body2, n = re.subn(pat, replacement, body, count=1, flags=re.S)
    if n == 0:
        body2 = body.rstrip() + "\n          " + replacement + "\n"
    return html[:m.start(2)] + body2 + html[m.end(2):]


def update_nav_links_for_category(cat: str) -> None:
    cat_dir = POSTS / cat
    if not cat_dir.exists():
        return

    posts = []
    for path in sorted(cat_dir.glob("*.html")):
        if path.name.startswith("_"):
            continue
        html = read_text(path)
        title = (
            extract_first(html, r"<h1[^>]*class=\"post-title\"[^>]*>(.*?)</h1>")
            or extract_first(html, r"<h1[^>]*>(.*?)</h1>")
            or guess_title(html)
            or path.stem
        )
        d = parse_iso_date(guess_date(html))
        if d is None:
            d = datetime.fromtimestamp(path.stat().st_mtime).date()
        posts.append({"path": path, "name": path.name, "title": title, "date": d})

    if not posts:
        return

    # Newest first; ties by filename for stable order
    posts.sort(key=lambda x: (x["date"], x["name"]), reverse=True)

    for idx, item in enumerate(posts):
        newer = posts[idx - 1] if idx - 1 >= 0 else None
        older = posts[idx + 1] if idx + 1 < len(posts) else None

        html = read_text(item["path"])
        html = replace_nav_link(html, "prev", render_nav_link("prev", newer))
        html = replace_nav_link(html, "next", render_nav_link("next", older))
        write_text(item["path"], html)


def main() -> None:
    ap = argparse.ArgumentParser(description="Import an HTML post and update index.html")
    ap.add_argument("--file", help="Path to the HTML file")
    ap.add_argument("--cat", choices=list(CATEGORIES.keys()), help="Category key")
    ap.add_argument("--date", help="Publish date YYYY-MM-DD")
    ap.add_argument("--title", help="Post title")
    ap.add_argument("--excerpt", help="Post excerpt")
    ap.add_argument("--meta", help="Post meta text (e.g., 约 8 分钟)")
    ap.add_argument("--ui", action="store_true", help="Use UI dialogs to pick file and fields")
    ap.add_argument("--ui-md", action="store_true", help="Use Markdown editor UI to generate HTML and import")
    ap.add_argument("--manage-tags", action="store_true", help="Manage tags for an existing HTML post")
    ap.add_argument("--repair", action="store_true", help="Repair an existing generated HTML using template + embedded Markdown")
    args = ap.parse_args()

    if not args.file and not args.ui and not args.ui_md:
        args.ui = True

    if args.repair:
        if not args.file:
            raise SystemExit("修复模式需要 --file")
        src = Path(args.file).expanduser().resolve()
        if not src.exists():
            raise SystemExit("文件不存在")
        html = read_text(src)
        template_html = read_text(ROOT / "posts" / "_template.html")
        m = re.search(r"<script type=\"text/markdown\"[^>]*>(.*?)</script>", html, re.S)
        if not m:
            raise SystemExit("未找到 Markdown 源内容")
        markdown = m.group(1).strip()

        fm, md_body = parse_front_matter(markdown)
        title = fm.get("title") or extract_title(md_body) or guess_title(html) or "未命名文章"
        excerpt = fm.get("description") or fm.get("excerpt") or extract_excerpt(md_body) or guess_excerpt(html) or "新文章"
        date_str = fm.get("date") or guess_date(html) or date.today().isoformat()
        # In repair mode, recompute read time unless front matter explicitly pins it.
        read_label = fm.get("read") or estimate_read_time(md_body)

        cat = src.parent.name
        if cat not in CATEGORIES:
            cat = fm.get("cat") or fm.get("category") or "cs"
        if cat not in CATEGORIES:
            raise SystemExit("无法识别分类")

        md_clean = clean_markdown_body(md_body, title, excerpt)
        html_out = apply_template(
            template_html,
            title=title,
            excerpt=excerpt,
            date_str=date_str,
            read_text=read_label,
            cat=cat,
            markdown=md_clean,
        )
        write_text(src, html_out)
        update_nav_links_for_category(cat)
        print("修复完成：", src)
        return

    if args.ui:
        mode = ui_choose_mode()
        if mode == "md":
            args.ui_md = True
        elif mode == "html":
            args.ui = True
        elif mode == "manage_tags":
            args.manage_tags = True
            args.ui = True
        else:
            raise SystemExit("已取消")

    if args.manage_tags:
        while True:
            target_file = args.file
            if args.ui or not target_file:
                picked = ui_pick_existing_post_file()
                if not picked:
                    print("已退出标签管理。")
                    return
                target_file = picked

            src = Path(target_file).expanduser().resolve()
            if not src.exists() or src.suffix.lower() != ".html":
                raise SystemExit("输入文件不存在或不是 .html 文件")

            try:
                src.relative_to(POSTS)
            except ValueError:
                raise SystemExit("请选择 posts/ 目录下的文章文件")

            html = read_text(src)
            current_tags = extract_keywords_meta(html)
            edited_tags = ui_edit_post_tags(
                str(src),
                existing_tags=load_existing_tags(),
                initial_tags=current_tags,
            )
            if edited_tags is None:
                if args.ui:
                    # 返回文章列表继续选择，而不是退出。
                    args.file = None
                    continue
                raise SystemExit("已取消")

            html = set_keywords_meta(html, edited_tags)
            write_text(src, html)

            href = str(src.relative_to(ROOT)).replace(os.sep, "/")
            index_html = read_text(INDEX)
            index_html, found = update_card_tags(index_html, href, edited_tags)
            index_html = rebuild_tags_cloud_from_cards(index_html)
            write_text(INDEX, index_html)

            print("标签已更新：")
            print(f"- 页面: {src}")
            print(f"- 标签: {', '.join(edited_tags) if edited_tags else '(无)'}")
            if not found:
                print("- 提示: 首页未找到对应卡片，仅更新了文章 meta keywords。")

            if not args.ui:
                return

            # UI 模式下，完成一篇后回到列表继续管理
            args.file = None

    if args.ui_md:
        template_html = read_text(ROOT / "posts" / "_template.html")
        # extract default markdown from template
        m = re.search(r"<script type=\"text/markdown\"[^>]*>(.*?)</script>", template_html, re.S)
        default_md = m.group(1).strip() if m else "# 标题\\n\\n正文内容。"
        ui_result = ui_markdown_import(
            "my-post.html",
            "robotics",
            default_md,
            template_html,
            existing_tags=load_existing_tags(),
        )
        if not ui_result:
            raise SystemExit("已取消")

        filename = ui_result["filename"]
        cat = ui_result["cat"]
        markdown = ui_result["markdown"]
        tags = ui_result.get("tags", [])

        if not filename.lower().endswith(".html"):
            filename += ".html"
        filename = filename.replace("/", "_").replace("\\\\", "_")

        fm, md_body = parse_front_matter(markdown)
        title = fm.get("title") or extract_title(md_body) or "未命名文章"
        excerpt = fm.get("description") or fm.get("excerpt") or extract_excerpt(md_body) or "新文章"
        date_str = fm.get("date") or date.today().isoformat()
        read_label = fm.get("read") or estimate_read_time(md_body)

        md_clean = clean_markdown_body(md_body, title, excerpt)
        html_out = apply_template(
            template_html,
            title=title,
            excerpt=excerpt,
            date_str=date_str,
            read_text=read_label,
            cat=cat,
            markdown=md_clean,
        )

        dest_dir = POSTS / cat
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename
        html_out = apply_keywords_meta(html_out, tags)
        write_text(dest, html_out)

        # update index.html
        index_html = read_text(INDEX)
        href = f"posts/{cat}/{dest.name}"
        if href not in index_html:
            card_html = build_card(
                href,
                cat,
                html_lib.escape(strip_inline_md(title)),
                html_lib.escape(strip_inline_md(excerpt)),
                date_str,
                read_label,
                tags=tags,
            )
            index_html = insert_card(index_html, card_html)
        index_html = update_counts(index_html)
        index_html = update_tags_cloud(index_html, tags)
        write_text(INDEX, index_html)
        update_nav_links_for_category(cat)

        print("完成：")
        print(f"- 页面: {dest}")
        print(f"- 首页卡片: {href}")
        return

    if not args.file and not args.ui:
        raise SystemExit("请提供 --file 或使用 --ui")

    file_path = args.file
    if args.ui:
        picked = ui_pick_file()
        if picked:
            file_path = picked
        else:
            raise SystemExit("未选择文件")

    src = Path(file_path).expanduser().resolve()
    if not src.exists() or src.suffix.lower() != ".html":
        raise SystemExit("输入文件不存在或不是 .html 文件")

    html = read_text(src)

    tags: list[str] = []
    if args.ui:
        form = ui_html_import_form(
            file_path=str(src),
            default_cat=args.cat or "robotics",
            default_title=args.title or guess_title(html) or "",
            default_excerpt=args.excerpt or guess_excerpt(html) or "",
            default_date=args.date or guess_date(html) or date.today().isoformat(),
            default_meta=args.meta or guess_read(html) or estimate_read_time_from_html(html),
            existing_tags=load_existing_tags(),
        )
        if not form:
            raise SystemExit("已取消")
        cat = form["cat"]
        title = form["title"]
        excerpt = form["excerpt"]
        date_str = form["date"]
        meta_text = form["meta"]
        tags = form.get("tags", [])
    else:
        cat = args.cat
        if not cat:
            cat = prompt_if_missing("分类 (cs/cpp/robotics/personal)", None)
            if not cat or cat not in CATEGORIES:
                raise SystemExit("分类不合法")

        title = args.title or guess_title(html)
        title = prompt_if_missing("标题", title)

        excerpt = args.excerpt or guess_excerpt(html)
        excerpt = prompt_if_missing("摘要", excerpt)

        date_str = args.date or guess_date(html) or date.today().isoformat()
        date_str = prompt_if_missing("日期 (YYYY-MM-DD)", date_str, date_str)

        # 元信息默认自动计算，不再要求手填。
        # 优先使用页面已有 post-head-read，其次按正文估算阅读时长。
        meta_text = args.meta or guess_read(html) or estimate_read_time_from_html(html)

    # move/copy into posts/<cat>/
    dest_dir = POSTS / cat
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name

    # If source is already in destination, just rewrite relative paths
    if src.resolve() != dest.resolve():
        shutil.copy2(src, dest)

    template_html = read_text(ROOT / "posts" / "_template.html")
    dest_html = read_text(dest)
    dest_html = adjust_relative_paths(dest_html)
    dest_html = inject_template_elements(
        dest_html,
        template_html,
        cat=cat,
        current_name=dest.name,
    )
    dest_html = apply_keywords_meta(dest_html, tags)
    write_text(dest, dest_html)

    # update index.html
    index_html = read_text(INDEX)
    href = f"posts/{cat}/{dest.name}"
    if href in index_html:
        print("index.html 已包含该链接，跳过插入卡片。")
    else:
        card_html = build_card(
            href,
            cat,
            html_lib.escape(strip_inline_md(title)),
            html_lib.escape(strip_inline_md(excerpt)),
            date_str,
            meta_text,
            tags=tags,
        )
        index_html = insert_card(index_html, card_html)

    index_html = update_counts(index_html)
    index_html = update_tags_cloud(index_html, tags)
    write_text(INDEX, index_html)
    update_nav_links_for_category(cat)

    print("完成：")
    print(f"- 页面: {dest}")
    print(f"- 首页卡片: {href}")


if __name__ == "__main__":
    main()
