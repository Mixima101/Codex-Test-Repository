#!/usr/bin/env python3
"""Desktop UI tool for extracting SOPREMA product URLs and names from saved HTML."""

from __future__ import annotations

import csv
import threading
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Button, DISABLED, NORMAL, StringVar, Tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText
from urllib.parse import urlparse


HTML_FILE = Path("All Roofs Products - Roofs - Building components _ SOPREMA.html")


@dataclass
class ProductRecord:
    name: str
    url: str


class ProductHTMLParser(HTMLParser):
    """Extract product links (<a class='result'>) and product names (<h3 class='result-title'>)."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[ProductRecord] = []
        self._current_url: str | None = None
        self._capturing_name = False
        self._name_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key: value for key, value in attrs}

        if tag == "a":
            class_value = attrs_dict.get("class") or ""
            href = attrs_dict.get("href")
            if href and "result" in class_value.split():
                self._current_url = href.strip()

        if tag == "h3" and self._current_url:
            class_value = attrs_dict.get("class") or ""
            if "result-title" in class_value.split():
                self._capturing_name = True
                self._name_parts = []

    def handle_data(self, data: str) -> None:
        if self._capturing_name:
            self._name_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "h3" and self._capturing_name:
            raw_name = "".join(self._name_parts).strip()
            if raw_name and self._current_url:
                self.records.append(ProductRecord(name=raw_name, url=self._current_url))
            self._capturing_name = False
            self._name_parts = []

        if tag == "a":
            self._current_url = None
            self._capturing_name = False
            self._name_parts = []


def extract_products(html_text: str) -> list[ProductRecord]:
    parser = ProductHTMLParser()
    parser.feed(html_text)

    unique: list[ProductRecord] = []
    seen: set[tuple[str, str]] = set()
    for item in parser.records:
        key = (item.name, item.url)
        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


class App:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("SOPREMA URL Extractor")
        self.root.geometry("920x640")

        self.status = StringVar(value="Ready.")
        self.products: list[ProductRecord] = []

        self._build_ui()

    def _build_ui(self) -> None:
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=X)

        ttk.Label(top_frame, text="HTML file:").pack(side=LEFT)
        self.path_var = StringVar(value=str(HTML_FILE.resolve()))
        self.path_entry = ttk.Entry(top_frame, textvariable=self.path_var)
        self.path_entry.pack(side=LEFT, fill=X, expand=True, padx=8)

        ttk.Button(top_frame, text="Browse", command=self.browse_file).pack(side=RIGHT)

        button_frame = ttk.Frame(self.root, padding=(10, 0, 10, 10))
        button_frame.pack(fill=X)

        self.find_button = Button(button_frame, text="Find URLs", command=self.find_urls, width=14)
        self.find_button.pack(side=LEFT, padx=(0, 8))

        self.download_button = Button(
            button_frame,
            text="Download URLs",
            command=self.download_urls,
            width=14,
            state=DISABLED,
        )
        self.download_button.pack(side=LEFT, padx=(0, 8))

        Button(button_frame, text="Exit", command=self.root.destroy, width=10).pack(side=LEFT)

        self.progress = ttk.Progressbar(self.root, orient="horizontal", mode="determinate", maximum=100)
        self.progress.pack(fill=X, padx=10)

        ttk.Label(self.root, textvariable=self.status, padding=(10, 6)).pack(fill=X)

        self.log_widget = ScrolledText(self.root, wrap="word", height=28)
        self.log_widget.pack(fill=BOTH, expand=True, padx=10, pady=(0, 10))
        self.log_widget.configure(state=DISABLED)

    def browse_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select SOPREMA HTML file",
            filetypes=[("HTML Files", "*.html;*.htm"), ("All Files", "*.*")],
        )
        if selected:
            self.path_var.set(selected)

    def append_log(self, text: str) -> None:
        self.log_widget.configure(state=NORMAL)
        self.log_widget.insert(END, text + "\n")
        self.log_widget.see(END)
        self.log_widget.configure(state=DISABLED)

    def set_busy(self, busy: bool) -> None:
        self.find_button.configure(state=DISABLED if busy else NORMAL)

    def find_urls(self) -> None:
        path = Path(self.path_var.get())
        if not path.exists():
            messagebox.showerror("File not found", f"Could not find file:\n{path}")
            return

        self.set_busy(True)
        self.download_button.configure(state=DISABLED)
        self.progress["value"] = 0
        self.status.set("Reading file...")
        self.append_log(f"[INFO] Reading {path}")

        thread = threading.Thread(target=self._extract_worker, args=(path,), daemon=True)
        thread.start()

    def _extract_worker(self, path: Path) -> None:
        try:
            html_text = path.read_text(encoding="utf-8", errors="ignore")
            self.root.after(0, lambda: self.progress.configure(value=25))
            products = extract_products(html_text)
            self.root.after(0, lambda: self._on_extract_done(products))
        except Exception as exc:
            self.root.after(0, lambda: self._on_extract_failed(exc))

    def _on_extract_done(self, products: list[ProductRecord]) -> None:
        self.products = products
        self.progress["value"] = 100
        self.set_busy(False)

        self.append_log(f"[INFO] Found {len(products)} product URLs.")
        for product in products:
            clean_url = self._clean_url(product.url)
            self.append_log(f"[URL] {product.name} -> {clean_url}")

        if products:
            self.download_button.configure(state=NORMAL)
            self.status.set(f"Done. Found {len(products)} URLs.")
        else:
            self.status.set("No product URLs found.")
            messagebox.showwarning("No results", "No product links were found in the file.")

    def _on_extract_failed(self, exc: Exception) -> None:
        self.set_busy(False)
        self.progress["value"] = 0
        self.status.set("Extraction failed.")
        self.append_log(f"[ERROR] {exc}")
        messagebox.showerror("Error", f"Failed to extract URLs:\n{exc}")

    def _clean_url(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" if parsed.scheme and parsed.netloc else url

    def download_urls(self) -> None:
        if not self.products:
            messagebox.showwarning("No data", "Please click 'Find URLs' first.")
            return

        out_file = filedialog.asksaveasfilename(
            title="Save URL spreadsheet",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile="soprema_product_urls.csv",
        )

        if not out_file:
            return

        output_path = Path(out_file)
        with output_path.open("w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["name", "url"])
            for product in self.products:
                writer.writerow([product.name, self._clean_url(product.url)])

        self.append_log(f"[INFO] CSV saved to {output_path}")
        self.status.set(f"Saved CSV: {output_path.name}")
        messagebox.showinfo("Saved", f"CSV file created:\n{output_path}")


def main() -> None:
    root = Tk()
    app = App(root)
    app.append_log("[INFO] Click 'Find URLs' to parse the HTML and list product links.")
    root.mainloop()


if __name__ == "__main__":
    main()
