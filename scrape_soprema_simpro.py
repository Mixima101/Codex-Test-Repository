#!/usr/bin/env python3
"""Scrape Soprema product pages and build a simPRO Catalog CSV.

This script supports two modes:
1) GUI mode (default):
   python scrape_soprema_simpro.py
2) CLI mode:
   python scrape_soprema_simpro.py --no-gui --template Catalog-Import-Template-US.csv --output output.csv

Prerequisites:
  pip install playwright
  playwright install chromium
"""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from queue import Empty, Queue
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_URL = "https://www.soprema.ca/en/products-systems"


@dataclass(frozen=True)
class ProductRecord:
    name: str
    code: str | None
    uom: str


def infer_uom(name: str) -> str:
    n = name.lower()
    if any(k in n for k in ["sealant", "adhesive", "mastic", "primer", "coating"]):
        return "Pail"
    if any(k in n for k in ["spray", "foam kit", "kit"]):
        return "Kit"
    if any(k in n for k in ["board", "iso", "xps", "panel"]):
        return "Panel"
    if any(k in n for k in ["tape", "flashing", "membrane", "roll", "sheet"]):
        return "Roll"
    return ""


def click_show_more(page) -> None:
    while True:
        buttons = page.locator("button:has-text('Show more products'), button:has-text('Show more')")
        if buttons.count() == 0:
            return
        try:
            buttons.first.click(timeout=2500)
            page.wait_for_timeout(900)
        except PlaywrightTimeoutError:
            return


def collect_product_links(page) -> list[str]:
    links = set()
    anchors = page.locator("a[href*='/en/products-systems/']")
    for i in range(anchors.count()):
        href = anchors.nth(i).get_attribute("href")
        if not href:
            continue
        if href.startswith("/"):
            href = f"https://www.soprema.ca{href}"
        if re.search(r"/en/products-systems/[a-z0-9\-]+/?$", href):
            links.add(href.rstrip("/"))
    return sorted(links)


def parse_product_rows(page) -> list[ProductRecord]:
    text = page.inner_text("body")
    matches = re.findall(r"([A-Z0-9\-\/'\"\(\)\., ]{4,}?)\s+Product code:\s*([0-9A-Z\-]+)", text)
    rows: list[ProductRecord] = []
    seen = set()

    for raw_name, code in matches:
        name = " ".join(raw_name.split()).strip("- ")
        if len(name) < 3:
            continue
        key = (name, code)
        if key in seen:
            continue
        seen.add(key)
        rows.append(ProductRecord(name=f"{name} (Code: {code})", code=code, uom=infer_uom(name)))

    if not rows:
        h1_locator = page.locator("h1").first
        if h1_locator.count() > 0:
            h1 = h1_locator.inner_text().strip()
            if h1:
                rows.append(ProductRecord(name=h1, code=None, uom=infer_uom(h1)))

    return rows


def build_csv(template: Path, output: Path, products: list[ProductRecord]) -> None:
    with template.open(newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)

    out_rows = []
    for p in products:
        row = [""] * len(header)
        row[4] = "Soprema."
        row[5] = p.name
        row[8] = row[9] = row[10] = row[11] = "0"
        row[19] = "1"
        row[20] = "Soprema."
        row[21] = p.name
        row[27] = p.uom
        out_rows.append(row)

    with output.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(out_rows)


def scrape_products(max_pages: int, progress_cb=None) -> list[ProductRecord]:
    all_products: dict[tuple[str, str | None], ProductRecord] = {}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=120000)
        page.wait_for_timeout(2000)
        click_show_more(page)
        links = collect_product_links(page)

        total = min(len(links), max_pages)
        if progress_cb:
            progress_cb("Scanning product pages...", 0, total)

        for idx, url in enumerate(links[:max_pages], start=1):
            p = browser.new_page()
            try:
                p.goto(url, wait_until="domcontentloaded", timeout=120000)
                p.wait_for_timeout(1000)
                for rec in parse_product_rows(p):
                    all_products[(rec.name, rec.code)] = rec
            finally:
                p.close()

            if progress_cb:
                progress_cb(f"Processed {idx}/{total} pages", idx, total)

        browser.close()

    return sorted(all_products.values(), key=lambda r: r.name)


class ScraperGUI:
    def __init__(self, root: tk.Tk, template: Path, max_pages: int):
        self.root = root
        self.template = template
        self.max_pages = max_pages
        self.temp_output_path: Path | None = None

        self.queue: Queue = Queue()
        self.worker: threading.Thread | None = None

        self.root.title("Soprema to simPRO CSV Scraper")
        self.root.geometry("640x280")

        container = ttk.Frame(root, padding=16)
        container.pack(fill="both", expand=True)

        ttk.Label(
            container,
            text="Scrape Soprema products and export a simPRO-ready CSV",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor="w")

        ttk.Label(container, text=f"Template: {template}").pack(anchor="w", pady=(8, 0))

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(container, textvariable=self.status_var).pack(anchor="w", pady=(12, 8))

        self.progress = ttk.Progressbar(container, orient="horizontal", mode="determinate", maximum=100)
        self.progress.pack(fill="x")

        self.count_var = tk.StringVar(value="Products found: 0")
        ttk.Label(container, textvariable=self.count_var).pack(anchor="w", pady=(8, 12))

        button_row = ttk.Frame(container)
        button_row.pack(fill="x")

        self.start_btn = ttk.Button(button_row, text="Start Scrape", command=self.start_scrape)
        self.start_btn.pack(side="left")

        self.download_btn = ttk.Button(button_row, text="Download CSV", command=self.download_csv, state="disabled")
        self.download_btn.pack(side="left", padx=(8, 0))

        ttk.Button(button_row, text="Exit", command=self.root.destroy).pack(side="right")

        self.root.after(200, self.poll_queue)

    def start_scrape(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        self.start_btn.configure(state="disabled")
        self.download_btn.configure(state="disabled")
        self.progress.configure(value=0)
        self.count_var.set("Products found: 0")
        self.status_var.set("Starting scraper...")

        def progress_cb(message: str, current: int, total: int) -> None:
            self.queue.put(("progress", message, current, total))

        def run_worker() -> None:
            try:
                products = scrape_products(max_pages=self.max_pages, progress_cb=progress_cb)
                with tempfile.NamedTemporaryFile(prefix="soprema_simpro_", suffix=".csv", delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                build_csv(self.template, tmp_path, products)
                self.queue.put(("done", tmp_path, len(products)))
            except Exception as exc:
                self.queue.put(("error", str(exc)))

        self.worker = threading.Thread(target=run_worker, daemon=True)
        self.worker.start()

    def download_csv(self) -> None:
        if not self.temp_output_path or not self.temp_output_path.exists():
            messagebox.showwarning("No file", "No generated CSV is available yet.")
            return

        destination = filedialog.asksaveasfilename(
            title="Save generated CSV",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="Soprema-simPRO-import.csv",
        )
        if not destination:
            return

        shutil.copyfile(self.temp_output_path, destination)
        messagebox.showinfo("Saved", f"CSV saved to:\n{destination}")

    def poll_queue(self) -> None:
        try:
            while True:
                item = self.queue.get_nowait()
                kind = item[0]

                if kind == "progress":
                    _, message, current, total = item
                    pct = (current / total * 100) if total else 0
                    self.status_var.set(message)
                    self.progress.configure(value=pct)
                elif kind == "done":
                    _, output_path, count = item
                    self.temp_output_path = output_path
                    self.status_var.set("Done. Click 'Download CSV' to save the results.")
                    self.count_var.set(f"Products found: {count}")
                    self.progress.configure(value=100)
                    self.start_btn.configure(state="normal")
                    self.download_btn.configure(state="normal")
                elif kind == "error":
                    _, message = item
                    self.status_var.set("Scrape failed.")
                    self.start_btn.configure(state="normal")
                    self.download_btn.configure(state="disabled")
                    messagebox.showerror("Error", message)
        except Empty:
            pass

        self.root.after(200, self.poll_queue)


def run_gui(template: Path, max_pages: int) -> int:
    root = tk.Tk()
    ScraperGUI(root, template=template, max_pages=max_pages)
    root.mainloop()
    return 0


def run_cli(template: Path, output: Path, max_pages: int) -> int:
    products = scrape_products(max_pages=max_pages, progress_cb=None)
    build_csv(template, output, products)
    print(f"Wrote {len(products)} products to {output}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", default="Catalog-Import-Template-US.csv")
    parser.add_argument("--output", default="Catalog-Import-Template-US.csv")
    parser.add_argument("--max-pages", type=int, default=5000)
    parser.add_argument("--no-gui", action="store_true", help="Run in command-line mode")
    args = parser.parse_args()

    template = Path(args.template)
    output = Path(args.output)

    if args.no_gui:
        return run_cli(template=template, output=output, max_pages=args.max_pages)

    return run_gui(template=template, max_pages=args.max_pages)


if __name__ == "__main__":
    raise SystemExit(main())
