import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import requests
import csv
import threading
import time
import json
from termcolor import colored
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
start_idx = 0  # Keeps track of where to resume from
SCROLL_DELAY = 1
stop_flag = False
processed_rows = 0
skipped_rows = 0
url_counter = Counter()  # To store URL counts
report_counter = Counter()  # To store report counts
flag_counter = Counter()  # To store flag counts
# Functions
def fetch_feed(feed):
    headers = {"Authorization": f"Bearer {feed['api_key']}"} if feed.get("api_key") else {}
    try:
        response = requests.get(feed["url"], headers=headers, timeout=10)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        return None


def parse_csv_data(data):
    reader = csv.reader(data.splitlines())
    return list(reader)

def parse_json_data(data):
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return []


def start_feed(feed, text_widget, status_label):
    global is_running, current_feed_data, start_idx, is_paused, stop_flag
    stop_flag = False  # Reset stop flag when starting a new feed
    is_running = True
    current_feed_data = []
    processed_rows = 0  # Reset processed rows
    skipped_rows = 0  # Reset skipped rows
    if not is_paused:  # Reset start index only when starting fresh, not when resuming
        start_idx = 0  
    is_paused = False  # Reset paused state when starting fresh
    text_widget.delete("1.0", tk.END)
    text_widget.tag_configure("cyan", foreground="red")
    text_widget.tag_configure("yellow", foreground="blue")
    
    

    def process_feed():
        global is_running, start_idx, is_paused, stop_flag, processed_rows, skipped_rows
        data = fetch_feed(feed)
    
        if data:
            rows = []
            if feed["format"] == "csv":
                rows = parse_csv_data(data)
            elif feed["format"] == "json":
                rows = parse_json_data(data)
        
            if rows:
                headers = rows[0] if feed["format"] == "csv" else list(rows[0].keys())  # Fetch headers dynamically
                current_feed_data.extend(rows[1:])
            
                for idx, row in enumerate(rows[1:][start_idx:]):
                    if stop_flag:  # Check if stop is requested
                        return  # Stop processing the feed

                    if is_paused:
                        return  # Pause the feed by returning early
                    if len(row) < 9:
                        print(f"Skipping row {idx + 1} due to insufficient data: {row}")
                        continue  # Skip rows with insufficient data
                    processed_rows += 1  # Increment processed rows counter

                    url = row[2]  # Extract the URL from the row
                    parsed_url = urlparse(url)  # Parse the URL to separate components
                    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"  # Combine scheme and netloc for the base URL


                    url_counter[base_url] += 1
                    report_counter[row[8]] += 1  # Assuming row[2] is the report field
                    flag_counter[row[6]] += 1  # Assuming row[3] is the flag field

             
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
                
                    text_widget.see(tk.END)
                
               
                    start_idx += 1
                    time.sleep(SCROLL_DELAY)  # Delay of 1 second per threat

                status_label.config(text=f"Status: Finished - {feed['name']}")
            else:
                status_label.config(text=f"Status: Error fetching {feed['name']}")
            is_running = False

    status_label.config(text=f"Status: Running - {feed['name']}")
    threading.Thread(target=process_feed, daemon=True).start()


def stop_feed(status_label):
    global is_running, stop_flag
    if is_running:
        stop_flag = True  # Set the stop flag to True
        status_label.config(text="Status: Stopped")


def pause_feed(status_label):
    global is_paused
    is_paused = True
    status_label.config(text="Status: Paused")

def resume_feed(feed, text_widget, status_label):
    global is_paused, start_idx
    if not current_feed_data:
        messagebox.showwarning("Resume", "No data to resume from.")
        return
    if is_paused:
        is_paused = False  # Unpause
        status_label.config(text=f"Status: Resumed - {feed['name']}")
        start_feed(feed, text_widget, status_label)  # Just call start_feed to continue from where we left off

def load_metrics_button(root):
    # Create and place the button to show the metrics
    metrics_button = ttk.Button(root, text="Show Metrics", command=show_metrics)
    metrics_button.pack(side=tk.left, padx=5, pady=5)

def find_in_feed(query):
    global current_feed_data
    results = []
    query = query.lower()
    
    # Search across the rows and columns (including nested structures for JSON)
    for idx, row in enumerate(current_feed_data):
        if isinstance(row, dict):  # JSON format
            # Search through all key-value pairs in the JSON object
            for key, value in row.items():
                if query in str(value).lower():
                    results.append(row)  # Add full row to results
                    break  # Stop searching other fields once a match is found
        else:  # CSV format
            # Check if query matches any cell in the row
            if any(query in str(cell).lower() for cell in row):
                results.append(row)  # Add full row to results

    # If results found, return them. Otherwise, inform the user that no matches were found
    if results:
        return results
    else:
        return None

def display_search_results(results, text_widget):
    if results:
        text_widget.delete("1.0", tk.END)  # Clear current text
        for row in results:
            text_widget.insert(tk.END, "################################################################################\n")
            text_widget.insert(tk.END, f"Threat information:", "cyan")
            text_widget.insert(tk.END, "\n")

            # If the row is a tuple/list, display it fully
            for col in row:
                text_widget.insert(tk.END, f"{col}\n", "yellow")

            text_widget.insert(tk.END, "\n")
    else:
        text_widget.insert(tk.END, "No matching threats found.\n")



def export_to_csv():
    global current_feed_data
    if not current_feed_data:
        messagebox.showwarning("Export", "No data to export.")
        return
    filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
    if filename:
        with open(filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            headers = current_feed_data[0] if current_feed_data else []
            writer.writerow(headers)
            for row in current_feed_data[1:]:
                writer.writerow(row)
        messagebox.showinfo("Export", "Data exported successfully!")


class ThreatFeedApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Threat Feed Viewer - LTH Cybersecurity")
        self.root.geometry("800x600")

        # Toolbar
        menubar = tk.Menu(self.root)
        feed_menu = tk.Menu(menubar, tearoff=0)
        feed_menu.add_command(label="Add Feed", command=lambda: self.add_feed())
        feed_menu.add_command(label="Export Data", command=export_to_csv)
        menubar.add_cascade(label="Sources", menu=feed_menu)
        menubar.add_command(label="Show Metrics", command=self.calculate_and_display_metrics)
        self.root.config(menu=menubar)

        # Feed Display
        global feed_label_var
        feed_label_var = tk.StringVar(value=f"Current Feed: {current_feed['name']}")
        feed_label = tk.Label(self.root, textvariable=feed_label_var, anchor="w", font=("Arial", 14))
        feed_label.pack(fill=tk.X, pady=5)

        # Search Bar
        search_frame = tk.Frame(self.root)
        search_frame.pack(fill=tk.X, pady=5)

        tk.Label(search_frame, text="Search:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, font=("Arial", 12))
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        search_button = ttk.Button(search_frame, text="Find", command=self.search_feed)
        search_button.pack(side=tk.LEFT, padx=5)

        # Feed Content
        self.text_widget = ScrolledText(self.root, wrap=tk.WORD, state=tk.NORMAL, font=("Courier", 10))
        self.text_widget.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(pady=5)

        ttk.Button(button_frame, text="Start", command=self.start_feed).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Stop", command=lambda: stop_feed(self.status_label)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Pause", command=lambda: pause_feed(self.status_label)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Resume", command=self.resume_feed).pack(side=tk.LEFT, padx=5)

        # Status
        self.status_label = tk.Label(self.root, text="Status: Idle", anchor="w", font=("Arial", 12))
        self.status_label.pack(fill=tk.X, padx=10, pady=5)

    def add_feed(self):
        def save_feed():
            name = name_var.get().strip()
            url = url_var.get().strip()
            format_type = format_var.get()
            api_key = api_key_var.get().strip() if api_key_var.get().strip() else None

            if not name or not url:
                messagebox.showerror("Error", "Name and URL are required!")
                return

            # Test API Key if needed
            if api_key and not self.test_api_key(url, api_key):
                messagebox.showerror("Error", "Invalid API Key!")
                return

            feeds.append({"name": name, "url": url, "format": format_type, "api_key": api_key})
            self.update_feed_menu()
            feed_label_var.set(f"Current Feed: {name}")
            add_window.destroy()

        add_window = tk.Toplevel()
        add_window.title("Add New Feed")
        add_window.geometry("400x350")

        tk.Label(add_window, text="Feed Name:").pack(pady=5)
        name_var = tk.StringVar()
        tk.Entry(add_window, textvariable=name_var).pack(pady=5)

        tk.Label(add_window, text="Feed URL:").pack(pady=5)
        url_var = tk.StringVar()
        tk.Entry(add_window, textvariable=url_var).pack(pady=5)

        tk.Label(add_window, text="Format:").pack(pady=5)
        format_var = tk.StringVar(value="csv")
        tk.OptionMenu(add_window, format_var, "csv", "json").pack(pady=5)

        tk.Label(add_window, text="API Key (Optional):").pack(pady=5)
        api_key_var = tk.StringVar()
        tk.Entry(add_window, textvariable=api_key_var).pack(pady=5)

        tk.Button(add_window, text="OK", command=save_feed).pack(pady=10)

    def update_feed_menu(self):
        menu = self.root.nametowidget("Sources")
        menu.delete(0, tk.END)
        menu.add_command(label="Add Feed", command=lambda: self.add_feed())
        for feed in feeds:
            menu.add_command(label=feed["name"], command=lambda f=feed: self.set_feed(f))

    def set_feed(self, feed):
        global current_feed
        current_feed = feed
        feed_label_var.set(f"Current Feed: {feed['name']}")

    def start_feed(self):
        start_feed(current_feed, self.text_widget, self.status_label)

    def resume_feed(self):
        resume_feed(current_feed, self.text_widget, self.status_label)

    def search_feed(self):
        query = self.search_var.get()
        if not query:
            messagebox.showwarning("Search", "Please enter a search term.")
            return
        results = find_in_feed(query)
    
        if results:
            self.text_widget.delete("1.0", tk.END)
            for idx, row in enumerate(results):  # Iterate over results with index
                threat_number = row[0]
                self.text_widget.insert(tk.END, f"Found Threat {threat_number}:\n")
            # Adjust if row is not a dictionary but a list/tuple
                if isinstance(row, dict):
                    for header, value in row.items():
                        label = f"{header.strip()}:"
                        self.text_widget.insert(tk.END, f"  {label} {value}\n")
                else:
                    for i, value in enumerate(row):
                        label = f"Field {i+1}:"
                        self.text_widget.insert(tk.END, f"  {label} {value}\n")
                self.text_widget.insert(tk.END, "\n")
            self.text_widget.see(tk.END)
        else:
            messagebox.showinfo("Search", "No results found.")
        
    def test_api_key(self, url, api_key):
        # Example function to test API key (e.g., sending a request to a test endpoint)
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return True
        except requests.RequestException:
            return False
            
    def calculate_and_display_metrics(self):
        global url_counter, report_counter, flag_counter
    
    # Calculate top 5 for each category
        top_urls = url_counter.most_common(5)
        top_reporters = report_counter.most_common(5)
        top_flags = flag_counter.most_common(5)
    
    # Display metrics in a pop-up window
        metrics_window = tk.Toplevel()
        metrics_window.title("Top Metrics")
        metrics_window.geometry("400x300")
    
        metrics_text = ScrolledText(metrics_window, wrap=tk.WORD, state=tk.NORMAL, font=("Courier", 10))
        metrics_text.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
    
        metrics_text.insert(tk.END, "Top 5 URLs:\n")
        for url, count in top_urls:
            metrics_text.insert(tk.END, f"{url}: {count}\n")
    
        metrics_text.insert(tk.END, "\nTop 5 Reporters:\n")
        for reporter, count in top_reporters:
            metrics_text.insert(tk.END, f"{reporter}: {count}\n")
    
        metrics_text.insert(tk.END, "\nTop 5 Tags:\n")
        for flag, count in top_flags:
            metrics_text.insert(tk.END, f"{flag}: {count}\n")
    
        metrics_text.config(state=tk.DISABLED)  # Make text read-only

    def show_metrics(self):
        calculate_and_display_metrics()




if __name__ == "__main__":
    root = tk.Tk()
    app = ThreatFeedApp(root)
    root.mainloop()
