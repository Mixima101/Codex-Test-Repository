#!/usr/bin/env python3
"""GUI tool to scrape product-line tables from URLs and export each line to CSV files."""

from __future__ import annotations

import csv
import queue
import re
import threading
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import List
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)


@dataclass
class ProductLine:
    name: str
    url: str


@dataclass
class TableData:
    source_name: str
    source_url: str
    headers: List[str]
    rows: List[List[str]]

    @property
    def is_empty(self) -> bool:
        return not self.headers and not self.rows


class HTMLTableExtractor(HTMLParser):
    """Extract visible text from all HTML tables while preserving row/column layout."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: List[TableData] = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._cell_tag: str | None = None
        self._cell_buffer: List[str] = []
        self._current_row: List[str] = []
        self._rows: List[List[str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "table":
            self._in_table = True
            self._rows = []
            return

        if not self._in_table:
            return

        if tag == "tr":
            self._in_row = True
            self._current_row = []
        elif tag in {"td", "th"} and self._in_row:
            self._in_cell = True
            self._cell_tag = tag
            self._cell_buffer = []
        elif tag == "br" and self._in_cell:
            self._cell_buffer.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self._in_table:
            return

        if tag in {"td", "th"} and self._in_cell:
            value = "".join(self._cell_buffer)
            value = re.sub(r"\s+", " ", unescape(value)).strip()
            self._current_row.append(value)
            self._in_cell = False
            self._cell_tag = None
            self._cell_buffer = []
        elif tag == "tr" and self._in_row:
            if any(cell.strip() for cell in self._current_row):
                self._rows.append(self._current_row)
            self._in_row = False
            self._current_row = []
        elif tag == "table":
            headers: List[str] = []
            body: List[List[str]] = []

            if self._rows:
                headers = self._rows[0]
                body = self._rows[1:] if len(self._rows) > 1 else []

            self.tables.append(TableData(source_name="", source_url="", headers=headers, rows=body))
            self._in_table = False
            self._rows = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell_buffer.append(data)


def load_product_lines(csv_path: Path) -> List[ProductLine]:
    lines: List[ProductLine] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("CSV has no headers.")

        normalized = {name.strip().lower(): name for name in reader.fieldnames}
        if "name" not in normalized or "url" not in normalized:
            raise ValueError("CSV must include 'name' and 'url' columns.")

        name_key = normalized["name"]
        url_key = normalized["url"]

        for row in reader:
            name = (row.get(name_key) or "").strip()
            url = (row.get(url_key) or "").strip()
            if not name or not url:
                continue
            lines.append(ProductLine(name=name, url=url))

    if not lines:
        raise ValueError("No valid rows found in CSV.")

    return lines


def fetch_html(url: str, timeout: int = 25) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def extract_tables_from_html(name: str, url: str, html: str) -> List[TableData]:
    parser = HTMLTableExtractor()
    parser.feed(html)
    tables: List[TableData] = []

    for table in parser.tables:
        if table.is_empty:
            continue

        row_width = max([len(table.headers)] + [len(row) for row in table.rows], default=0)
        if row_width == 0:
            continue

        headers = table.headers[:] if table.headers else [f"column_{i+1}" for i in range(row_width)]
        if len(headers) < row_width:
            headers += [f"column_{i+1}" for i in range(len(headers), row_width)]

        normalized_rows = [row + [""] * (row_width - len(row)) for row in table.rows]

        tables.append(
            TableData(
                source_name=name,
                source_url=url,
                headers=headers,
                rows=normalized_rows,
            )
        )

    return tables


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r'[\\/:*?"<>|]+', "_", name)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned or "product_line"


def write_tables_to_csv(output_dir: Path, table_sets: List[TableData]) -> List[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    created: List[Path] = []
    name_counter: dict[str, int] = {}

    for table in table_sets:
        base = sanitize_filename(table.source_name)
        name_counter[base] = name_counter.get(base, 0) + 1
        suffix = f"_{name_counter[base]}" if name_counter[base] > 1 else ""
        file_path = output_dir / f"{base}{suffix}.csv"

        with file_path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["source_name", table.source_name])
            writer.writerow(["source_url", table.source_url])
            writer.writerow([])
            writer.writerow(table.headers)
            writer.writerows(table.rows)

        created.append(file_path)

    return created


class ScraperApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Product Line Table Scraper")
        self.root.geometry("900x600")

        self.csv_path = tk.StringVar(value=str(Path("soprema_product_line_urls.csv").resolve()))
        self.output_dir = tk.StringVar(value=str((Path.cwd() / "output_tables").resolve()))
        self.progress = tk.DoubleVar(value=0)
        self.progress_label = tk.StringVar(value="Ready")

        self.messages: queue.Queue[tuple[str, object]] = queue.Queue()
        self.scraped_tables: List[TableData] = []
        self.total_lines = 0
        self.processed_lines = 0
        self.worker: threading.Thread | None = None

        self._build_ui()
        self._poll_messages()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)

        csv_row = ttk.Frame(frame)
        csv_row.pack(fill="x", pady=(0, 8))
        ttk.Label(csv_row, text="URL CSV:").pack(side="left")
        ttk.Entry(csv_row, textvariable=self.csv_path).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(csv_row, text="Browse", command=self.choose_csv).pack(side="left")

        out_row = ttk.Frame(frame)
        out_row.pack(fill="x", pady=(0, 10))
        ttk.Label(out_row, text="Output Folder:").pack(side="left")
        ttk.Entry(out_row, textvariable=self.output_dir).pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(out_row, text="Browse", command=self.choose_output_dir).pack(side="left")

        action_row = ttk.Frame(frame)
        action_row.pack(fill="x", pady=(0, 8))
        self.find_btn = ttk.Button(action_row, text="Find Products", command=self.start_scrape)
        self.find_btn.pack(side="left")
        self.download_btn = ttk.Button(action_row, text="Download Tables", command=self.download_tables, state="disabled")
        self.download_btn.pack(side="left", padx=(8, 0))

        progress_row = ttk.Frame(frame)
        progress_row.pack(fill="x", pady=(6, 10))
        self.progress_bar = ttk.Progressbar(progress_row, maximum=100, variable=self.progress)
        self.progress_bar.pack(fill="x", expand=True, side="left")
        ttk.Label(progress_row, textvariable=self.progress_label, width=24).pack(side="left", padx=(10, 0))

        ttk.Label(frame, text="Logs").pack(anchor="w")
        self.log_text = tk.Text(frame, wrap="word", height=25)
        self.log_text.pack(fill="both", expand=True)
        scrollbar = ttk.Scrollbar(self.log_text, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def choose_csv(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select URL CSV",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        )
        if file_path:
            self.csv_path.set(file_path)

    def choose_output_dir(self) -> None:
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_dir.set(folder)

    def log(self, message: str) -> None:
        self.log_text.insert("end", message + "\n")
        self.log_text.see("end")

    def set_controls_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.find_btn.configure(state=state)
        self.download_btn.configure(state="normal" if enabled and bool(self.scraped_tables) else "disabled")

    def start_scrape(self) -> None:
        if self.worker and self.worker.is_alive():
            return

        csv_file = Path(self.csv_path.get()).expanduser()
        if not csv_file.exists():
            messagebox.showerror("Missing CSV", f"Could not find CSV file:\n{csv_file}")
            return

        self.scraped_tables = []
        self.total_lines = 0
        self.processed_lines = 0
        self.progress.set(0)
        self.progress_label.set("Starting...")
        self.set_controls_enabled(False)
        self.log("=" * 70)
        self.log(f"Starting scrape from {csv_file}")

        self.worker = threading.Thread(target=self._scrape_worker, args=(csv_file,), daemon=True)
        self.worker.start()

    def _scrape_worker(self, csv_file: Path) -> None:
        try:
            product_lines = load_product_lines(csv_file)
            self.messages.put(("init", len(product_lines)))

            for line in product_lines:
                try:
                    html = fetch_html(line.url)
                    tables = extract_tables_from_html(line.name, line.url, html)
                    if not tables:
                        self.messages.put(("log", f"No table found: {line.name} ({line.url})"))
                    else:
                        self.messages.put(("tables", tables))
                        self.messages.put(("log", f"Found {len(tables)} table(s): {line.name}"))
                except (HTTPError, URLError, TimeoutError) as err:
                    self.messages.put(("log", f"Request failed: {line.name} -> {err}"))
                except Exception as err:  # noqa: BLE001
                    self.messages.put(("log", f"Parse failed: {line.name} -> {err}"))

                self.messages.put(("advance", line.name))

            self.messages.put(("done", None))
        except Exception as err:  # noqa: BLE001
            self.messages.put(("fatal", str(err)))

    def download_tables(self) -> None:
        if not self.scraped_tables:
            messagebox.showinfo("No Data", "No scraped tables to save.")
            return

        out_dir = Path(self.output_dir.get()).expanduser()
        created_files = write_tables_to_csv(out_dir, self.scraped_tables)
        self.log(f"Saved {len(created_files)} CSV file(s) to {out_dir}")
        messagebox.showinfo("Done", f"Saved {len(created_files)} CSV file(s) to:\n{out_dir}")

    def _poll_messages(self) -> None:
        try:
            while True:
                msg_type, payload = self.messages.get_nowait()
                self._handle_message(msg_type, payload)
        except queue.Empty:
            pass

        self.root.after(150, self._poll_messages)

    def _handle_message(self, msg_type: str, payload: object) -> None:
        if msg_type == "init":
            self.total_lines = int(payload)
            self.processed_lines = 0
            self.progress_label.set(f"0 / {self.total_lines}")
            self.log(f"Loaded {self.total_lines} URLs.")
        elif msg_type == "tables":
            self.scraped_tables.extend(payload)  # type: ignore[arg-type]
        elif msg_type == "log":
            self.log(str(payload))
        elif msg_type == "advance":
            self.processed_lines += 1
            percent = (self.processed_lines / max(self.total_lines, 1)) * 100
            self.progress.set(percent)
            self.progress_label.set(f"{self.processed_lines} / {self.total_lines}")
        elif msg_type == "done":
            self.log(f"Scrape complete. Extracted {len(self.scraped_tables)} table(s).")
            self.set_controls_enabled(True)
            if self.scraped_tables:
                self.download_btn.configure(state="normal")
        elif msg_type == "fatal":
            self.log(f"Fatal error: {payload}")
            self.set_controls_enabled(True)
            messagebox.showerror("Scrape Error", str(payload))


def main() -> None:
    root = tk.Tk()
    app = ScraperApp(root)
    # Keep variable alive for type checkers and debuggers.
    _ = app
    root.mainloop()


if __name__ == "__main__":
    main()
