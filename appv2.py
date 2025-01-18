import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import requests
import csv
import threading
import time
import json
from urllib.parse import urlparse
from collections import Counter

# Configuration
DEFAULT_FEED = {
    "name": "URLHaus",
    "url": "https://urlhaus.abuse.ch/downloads/csv_online/",
    "format": "csv",
    "api_key": None,
}

# Globals
feeds = [DEFAULT_FEED]
is_running = False
is_paused = False
current_feed = DEFAULT_FEED
current_feed_data = []
start_idx = 0
SCROLL_DELAY = 1
stop_flag = False
processed_rows = 0
skipped_rows = 0
url_counter = Counter()
report_counter = Counter()
flag_counter = Counter()

def fetch_feed(feed):
    """Fetch data from feed URL"""
    headers = {"Authorization": f"Bearer {feed['api_key']}"} if feed.get("api_key") else {}
    try:
        response = requests.get(feed["url"], headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching feed: {e}")
        return None

def parse_csv_data(data):
    """Parse CSV data and return list of rows"""
    try:
        lines = data.splitlines()
        start_idx = 0
        for i, line in enumerate(lines):
            if line and not line.startswith('#'):
                start_idx = i
                break
       
        reader = csv.reader(lines[start_idx:])
        rows = list(reader)
       
        if not rows:
            print("No data found in CSV")
            return None
           
        rows = [row for row in rows if any(cell.strip() for cell in row)]
        return rows
       
    except Exception as e:
        print(f"Error parsing CSV data: {e}")
        return None

def parse_json_data(data):
    """Parse JSON data and return structured data"""
    try:
        json_data = json.loads(data)
       
        if isinstance(json_data, dict):
            for field in ['data', 'items', 'results', 'threats']:
                if field in json_data and isinstance(json_data[field], list):
                    return json_data[field]
            return [json_data]
           
        elif isinstance(json_data, list):
            return json_data
           
        else:
            print("Unexpected JSON structure")
            return None
           
    except Exception as e:
        print(f"Error parsing JSON data: {e}")
        return None

def process_feed(feed, text_widget, status_label):
    """Process and display feed data"""
    global is_running, start_idx, is_paused, stop_flag, processed_rows, skipped_rows
   
    data = fetch_feed(feed)
    if not data:
        status_label.config(text=f"Status: Error fetching {feed['name']}")
        is_running = False
        return

    rows = []
    if feed["format"] == "csv":
        rows = parse_csv_data(data)
    elif feed["format"] == "json":
        rows = parse_json_data(data)

    if not rows:
        status_label.config(text=f"Status: No data in {feed['name']}")
        is_running = False
        return

    current_feed_data.extend(rows[1:] if feed["format"] == "csv" else rows)

    for idx, row in enumerate(rows[1:] if feed["format"] == "csv" else rows):
        if stop_flag:
            is_running = False
            return

        if is_paused:
            status_label.config(text=f"Status: Paused at {start_idx + 1}")
            return

        try:
            if feed["format"] == "csv":
                if len(row) < 9:
                    skipped_rows += 1
                    continue

                processed_rows += 1
               
                url = row[2]
                parsed_url = urlparse(url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

                url_counter[base_url] += 1
                report_counter[row[8]] += 1
                flag_counter[row[6]] += 1

                text_widget.insert(tk.END, "################################################################################\n")
                text_widget.insert(tk.END, f"Threat {start_idx + 1}:", "cyan")
                text_widget.insert(tk.END, "\n")

                text_widget.insert(tk.END, f"ID: {row[0]}\n", "yellow")
                text_widget.insert(tk.END, f"Date Added: {row[1]}\n", "yellow")
                text_widget.insert(tk.END, f"URL: {row[2]}\n", "yellow")
                text_widget.insert(tk.END, f"Status: {row[3]}\n", "yellow")
                text_widget.insert(tk.END, f"Last Online: {row[4]}\n", "yellow")
                text_widget.insert(tk.END, f"Threat: {row[5]}\n", "yellow")
                text_widget.insert(tk.END, f"Tags: {row[6]}\n", "yellow")
                text_widget.insert(tk.END, f"Details: {row[7]}\n", "yellow")
                text_widget.insert(tk.END, f"Reporter: {row[8]}\n", "yellow")
                text_widget.insert(tk.END, "\n")

            else:  # JSON format
                processed_rows += 1
               
                text_widget.insert(tk.END, "################################################################################\n")
                text_widget.insert(tk.END, f"Threat {start_idx + 1}:", "cyan")
                text_widget.insert(tk.END, "\n")

                for key, value in row.items():
                    text_widget.insert(tk.END, f"{key}: {value}\n", "yellow")
               
                text_widget.insert(tk.END, "\n")

                # Update counters for JSON format
                if 'url' in row:
                    try:
                        parsed_url = urlparse(row['url'])
                        base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
                        url_counter[base_url] += 1
                    except:
                        pass
               
                if 'reporter' in row:
                    report_counter[row['reporter']] += 1
               
                if 'tags' in row:
                    tags = row['tags']
                    if isinstance(tags, str):
                        tags = tags.split(',')
                    for tag in tags:
                        flag_counter[tag.strip()] += 1

            text_widget.see(tk.END)
            start_idx += 1
            time.sleep(SCROLL_DELAY)

        except Exception as e:
            print(f"Error processing row {start_idx}: {e}")
            skipped_rows += 1
            continue

    status_label.config(text=f"Status: Finished - {feed['name']} - Processed: {processed_rows}, Skipped: {skipped_rows}")
    is_running = False

def start_feed(feed, text_widget, status_label):
    """Start processing the feed"""
    global is_running, current_feed_data, start_idx, is_paused, stop_flag, processed_rows, skipped_rows
   
    if is_running and not is_paused:
        messagebox.showinfo("Info", "Feed is already running")
        return
       
    stop_flag = False
    is_running = True
   
    if not is_paused:
        current_feed_data = []
        processed_rows = 0
        skipped_rows = 0
        start_idx = 0
        text_widget.delete("1.0", tk.END)
       
    is_paused = False
   
    text_widget.tag_configure("cyan", foreground="red")
    text_widget.tag_configure("yellow", foreground="blue")
   
    status_label.config(text=f"Status: Running - {feed['name']}")
    threading.Thread(target=lambda: process_feed(feed, text_widget, status_label), daemon=True).start()

def stop_feed(status_label):
    """Stop feed processing"""
    global is_running, stop_flag
    if is_running:
        stop_flag = True
        status_label.config(text="Status: Stopped")

def pause_feed(status_label):
    """Pause feed processing"""
    global is_paused, is_running
    if is_running:
        is_paused = True
        status_label.config(text="Status: Paused")
    else:
        messagebox.showinfo("Info", "No feed is currently running")

def resume_feed(feed, text_widget, status_label):
    """Resume paused feed"""
    global is_paused, is_running
    if not is_paused:
        messagebox.showinfo("Info", "Feed is not paused")
        return
    if not current_feed_data:
        messagebox.showwarning("Resume", "No data to resume from")
        return
   
    start_feed(feed, text_widget, status_label)

class ThreatFeedApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Threat Feed Viewer")
        self.root.geometry("800x600")

        # Menu
        menubar = tk.Menu(self.root)
        feed_menu = tk.Menu(menubar, tearoff=0)
        feed_menu.add_command(label="Add Feed", command=self.add_feed)
        feed_menu.add_command(label="Export Data", command=self.export_data)
        menubar.add_cascade(label="Sources", menu=feed_menu)
        menubar.add_command(label="Show Metrics", command=self.show_metrics)
        self.root.config(menu=menubar)

        # Feed label
        self.feed_label = tk.Label(root, text=f"Current Feed: {current_feed['name']}",
                                 anchor="w", font=("Arial", 14))
        self.feed_label.pack(fill=tk.X, pady=5)

        # Search
        search_frame = tk.Frame(root)
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        tk.Entry(search_frame, textvariable=self.search_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(search_frame, text="Search", command=self.search_feed).pack(side=tk.LEFT, padx=5)

        # Feed display
        self.text_widget = ScrolledText(root, wrap=tk.WORD, font=("Courier", 10))
        self.text_widget.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Control buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Start", command=self.start_feed).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Stop", command=self.stop_feed).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Pause", command=self.pause_feed).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Resume", command=self.resume_feed).pack(side=tk.LEFT, padx=5)

        # Status
        self.status_label = tk.Label(root, text="Status: Ready", anchor="w", font=("Arial", 12))
        self.status_label.pack(fill=tk.X, padx=10, pady=5)

    def add_feed(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Feed")
        dialog.geometry("400x300")

        tk.Label(dialog, text="Name:").pack(pady=5)
        name_var = tk.StringVar()
        tk.Entry(dialog, textvariable=name_var).pack(fill=tk.X, padx=5)

        tk.Label(dialog, text="URL:").pack(pady=5)
        url_var = tk.StringVar()
        tk.Entry(dialog, textvariable=url_var).pack(fill=tk.X, padx=5)

        tk.Label(dialog, text="Format:").pack(pady=5)
        format_var = tk.StringVar(value="csv")
        tk.OptionMenu(dialog, format_var, "csv", "json").pack(fill=tk.X, padx=5)

        tk.Label(dialog, text="API Key (optional):").pack(pady=5)
        api_key_var = tk.StringVar()
        tk.Entry(dialog, textvariable=api_key_var).pack(fill=tk.X, padx=5)

        def save():
            feeds.append({
                "name": name_var.get(),
                "url": url_var.get(),
                "format": format_var.get(),
                "api_key": api_key_var.get() if api_key_var.get() else None
            })
            dialog.destroy()
            self.update_feed_label()

        ttk.Button(dialog, text="Save", command=save).pack(pady=10)

    def update_feed_label(self):
        self.feed_label.config(text=f"Current Feed: {current_feed['name']}")

    def export_data(self):
        if not current_feed_data:
            messagebox.showwarning("Export", "No data to export")
            return
           
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for row in current_feed_data:
                    if isinstance(row, dict):
                        writer.writerow(row.values())
                    else:
                        writer.writerow(row)

    def show_metrics(self):
        metrics_window = tk.Toplevel(self.root)
        metrics_window.title("Metrics")
        metrics_window.geometry("400x300")

        text = ScrolledText(metrics_window)
        text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        text.insert(tk.END, "Top URLs:\n")
        for url, count in url_counter.most_common(5):
            text.insert(tk.END, f"{url}: {count}\n")

        text.insert(tk.END, "\nTop Reporters:\n")
        for reporter, count in report_counter.most_common(5):
            text.insert(tk.END, f"{reporter}: {count}\n")

        text.insert(tk.END, "\nTop Tags:\n")
        for tag, count in flag_counter.most_common(5):
            text.insert(tk.END, f"{tag}: {count}\n")

    def search_feed(self):
        query = self.search_var.get().lower()
        if not query:
            return
           
        results = []
        for row in current_feed_data:
            if isinstance(row, dict):
                if any(query in str(v).lower() for v in row.values()):
                    results.append(row)
            else:
                if any(query in str(cell).lower() for cell in row):
                    results.append(row)

        self.text_widget.delete("1.0", tk.END)
        if results:
            for row in results:
                if isinstance(row, dict):
                    for key, value in row.items():
                        self.text_widget.insert(tk.END, f"{key}: {value}\n")
                else:
                    for cell in row:
                        self.text_widget.insert(tk.END, f"{cell}\n")
                self.text_widget.insert(tk.END, "\n")
        else:
            self.text_widget.insert(tk.END, "No results found")

    def start_feed(self):
        start_feed(current_feed, self.text_widget, self.status_label)

    def stop_feed(self):
        stop_feed(self.status_label)

    def pause_feed(self):
        pause_feed(self.status_label)

    def resume_feed(self):
        resume_feed(current_feed, self.text_widget, self.status_label)

def main():
    root = tk.Tk()
    app = ThreatFeedApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

