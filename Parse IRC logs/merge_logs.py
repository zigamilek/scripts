import re
import os
from datetime import datetime
from collections import defaultdict

# Helper function to parse a single log file
def parse_log_file(file_path):
    print(f"Working on {file_path}")
    sessions = []
    session_date = None
    session_messages = []
    timestamp_regex = re.compile(r"\((\d{2}:\d{2})\) \(([^)]+)\) (.+)")

    with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
        lines = file.readlines()

    for line in lines:
        # Check for session start date
        if line.startswith("Session Start:"):
            if session_messages:
                sessions.append((session_date, session_messages))
            date_str = line.split("Session Start: ")[1].strip()
            session_date = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y")
            session_messages = []
            continue

        # Extract messages with timestamps
        match = timestamp_regex.match(line)
        if match:
            time_str, user, msg = match.groups()
            full_timestamp = datetime.combine(session_date.date(), datetime.strptime(time_str, "%H:%M").time())
            session_messages.append((full_timestamp, user, msg))

    # Add last session if exists
    if session_messages:
        sessions.append((session_date, session_messages))

    return sessions

# Helper function to combine sessions from all logs
def combine_sessions(file_paths):
    all_sessions = []

    # Parse each file and collect all sessions
    for path in file_paths:
        sessions = parse_log_file(path)
        all_sessions.extend((path, session_date, session_messages) for session_date, session_messages in sessions)

    # Sort sessions by date
    all_sessions.sort(key=lambda s: s[1])

    return all_sessions

# Helper function to write individual session HTML files
def output_session_html(sessions, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    session_files = []

    for i, (log_file, session_date, session_messages) in enumerate(sessions):
        # Get the nickname from the log file's filename
        nickname = os.path.splitext(os.path.basename(log_file))[0]

        session_filename = f"{output_dir}/{session_date.strftime('%Y-%m-%d')}_{i}.html"
        session_files.append((session_date, session_filename, nickname))

        with open(session_filename, 'w', encoding='utf-8') as file:
            file.write(f"<html><head><title>IRC Session {session_date.strftime('%Y-%m-%d')}</title></head><body>")
            file.write(f"<h2>IRC Session - {session_date.strftime('%Y-%m-%d %H:%M')}</h2><ul>")

            for timestamp, user, msg in session_messages:
                file.write(f"<li>{timestamp.strftime('%H:%M')} <strong>{user}:</strong> {msg}</li>")

            file.write("</ul></body></html>")

    return session_files

# Helper function to generate index HTML page
def generate_index_html(session_files, output_file):
    # Group sessions by month-year
    grouped_sessions = defaultdict(list)

    for date, filename, nickname in session_files:
        key = date.strftime("%Y-%m")
        grouped_sessions[key].append((date, filename, nickname))

    # Write index HTML page
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write("<html><head><title>IRC Sessions Index</title></head><body>")
        file.write("<h1>IRC Sessions Index</h1>")

        for month_year, sessions in grouped_sessions.items():
            file.write(f"<h2>{month_year}</h2><ul>")

            for date, filename, nickname in sessions:
                day_name = date.strftime("%A")
                # Extract relative path from filename
                relative_path = os.path.relpath(filename, os.path.dirname(output_file))
                file.write(f"<li><a href=\"{relative_path}\" target=\"_blank\">{date.strftime('%Y-%m-%d')} ({day_name}) ({nickname})</a> - {date.strftime('%H:%M')}</li>")

            file.write("</ul>")

        file.write("</body></html>")

# Main function
def main():
    import sys

    # Check for directory argument
    if len(sys.argv) < 2:
        print("Usage: python merge_logs.py <log_directory>")
        return

    log_directory = sys.argv[1]

    # List all .log files in the directory, case-insensitive
    log_files = [os.path.join(log_directory, f) for f in os.listdir(log_directory) if f.lower().endswith('.log')]
    print(log_files)

    # Combine and sort sessions
    sessions = combine_sessions(log_files)

    # Output sessions to individual HTML files
    output_dir = os.path.join(log_directory, "sessions_html")
    session_files = output_session_html(sessions, output_dir)

    # Generate index HTML
    index_file = os.path.join(log_directory, "index.html")
    generate_index_html(session_files, index_file)

if __name__ == "__main__":
    main()
