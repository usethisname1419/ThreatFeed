import requests
import csv
import time
import os
from datetime import datetime, timedelta
from termcolor import colored

# Configuration
DATA_DIR = "threat_data"
FETCH_INTERVAL = timedelta(days=1)  # Fetch data once a day
SCROLL_DELAY = 2  # Time (seconds) to wait before displaying the next threat
DISPLAY_LIMIT = 1000  # Max number of threats to display in one session

# Example threat feed URLs
feeds = {
    "URLHaus Malicious URLs": "https://urlhaus.abuse.ch/downloads/csv_online/",
}

def fetch_feed(feed_name, url):
    """Fetches data from a threat feed URL."""
    try:
        print(f"\nFetching {feed_name} data...")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        print(f"Data fetched successfully for {feed_name}.")
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching {feed_name}: {e}")
        return None

def save_data(feed_name, data):
    """Saves feed data locally."""
    os.makedirs(DATA_DIR, exist_ok=True)
    file_path = os.path.join(DATA_DIR, f"{feed_name.replace(' ', '_')}.csv")
    with open(file_path, "w") as file:
        file.write(data)
    print(f"Data saved for {feed_name} at {file_path}.")
    return file_path

def load_data(feed_name):
    """Loads locally saved feed data."""
    file_path = os.path.join(DATA_DIR, f"{feed_name.replace(' ', '_')}.csv")
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return file.read()
    return None

def get_last_fetch_time():
    """Returns the timestamp of the last fetch."""
    timestamp_file = os.path.join(DATA_DIR, "last_fetch.txt")
    if os.path.exists(timestamp_file):
        with open(timestamp_file, "r") as file:
            return datetime.fromisoformat(file.read().strip())
    return None

def update_last_fetch_time():
    """Updates the timestamp of the last fetch."""
    timestamp_file = os.path.join(DATA_DIR, "last_fetch.txt")
    with open(timestamp_file, "w") as file:
        file.write(datetime.now().isoformat())

def display_threats(feed_name, data):
    """Parses and displays threats with enhanced formatting."""
    print(f"\nDisplaying threats from {feed_name}:\n{'=' * 50}")
    rows = csv.reader(data.splitlines(), delimiter=",")
    headers = next(rows, None)

    print(f"{colored('Headers:', 'cyan')} {', '.join(headers)}\n{'-' * 50}")

    for idx, row in enumerate(rows):
        if row[0].startswith("#") or len(row) <= 1:
            # Skip comments or invalid rows
            continue
        if idx < DISPLAY_LIMIT:
            print('################################################################################\n')
            print(f"{colored(f'Threat {idx + 1}:', 'cyan')}")
            print(f"  {colored('ID:', 'yellow')} {row[0]}")
            print(f"  {colored('Date Added:', 'yellow')} {row[1]}")
            print(f"  {colored('URL:', 'yellow')} {row[2]}")
            print(f"  {colored('Status:', 'yellow')} {row[3]}")
            print(f"  {colored('Last Online:', 'yellow')} {row[4]}")
            print(f"  {colored('Threat:', 'yellow')} {row[5]}")
            print(f"  {colored('Tags:', 'yellow')} {row[6]}")
            print(f"  {colored('Details:', 'yellow')} {row[7]}")
            print(f"  {colored('Reporter:', 'yellow')} {row[8]}\n")
            time.sleep(SCROLL_DELAY)
        else:
            print("... (stopping for this session, restart tomorrow)")
            break

def main():
    """Main function to fetch, save, and display threat feeds."""
    try:
        last_fetch = get_last_fetch_time()
        if last_fetch is None or datetime.now() - last_fetch > FETCH_INTERVAL:
            print("Fetching new data...")
            for feed_name, url in feeds.items():
                data = fetch_feed(feed_name, url)
                if data:
                    file_path = save_data(feed_name, data)
                    print(f"Fetched data saved at: {colored(file_path, 'green')}")
            update_last_fetch_time()
        else:
            print(f"Last fetch was at {last_fetch}. Using cached data.")

        for feed_name in feeds:
            data = load_data(feed_name)
            if data:
                display_threats(feed_name, data)

    except KeyboardInterrupt:
        print("\nExiting... Data saved at:")
        for feed_name in feeds:
            file_path = os.path.join(DATA_DIR, f"{feed_name.replace(' ', '_')}.csv")
            print(f"- {colored(file_path, 'green')}")
        exit(0)

if __name__ == "__main__":
    print("Starting threat feed viewer...")
    main()
