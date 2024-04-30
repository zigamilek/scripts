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
    timestamp_regex = re.compile(r"\((\d{2}:\d{2})\) (?:<([^>]+)>|\(([^)]+)\)) (.+)")    

    with open(file_path, 'r', encoding='cp1250', errors='replace') as file:
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
            time_str, user1, user2, msg = match.groups()
            user = user1 if user1 else user2
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
    session_html_dir = os.path.join(output_dir, 'session_htmls')
    if not os.path.exists(session_html_dir):
        os.makedirs(session_html_dir)

    session_files = []

    for i, (log_file, session_date, session_messages) in enumerate(sessions):
        # Get the nickname from the log file's filename
        nickname = os.path.splitext(os.path.basename(log_file))[0]

        session_filename = f"{session_html_dir}/{session_date.strftime('%Y-%m-%d')}_{i}.html"
        session_files.append((session_date, session_filename, nickname))

        with open(session_filename, 'w', encoding='utf-8') as file:
            file.write(f"<html><head><title>IRC Session {session_date.strftime('%Y-%m-%d')}</title></head><body>")
            file.write(f"<h2>IRC Session - {session_date.strftime('%Y-%m-%d %H:%M')}</h2><ul>")

            for timestamp, user, msg in session_messages:
                # Escape angle brackets in user and msg
                user_escaped = user.replace("<", "&lt;").replace(">", "&gt;")
                msg_escaped = msg.replace("<", "&lt;").replace(">", "&gt;")
                file.write(f"<li>{timestamp.strftime('%H:%M')} <strong>{user_escaped}:</strong> {msg_escaped}</li>")

            file.write("</ul></body></html>")

    return session_files

# Helper function to generate index HTML page
def generate_index_html(session_files, output_file):
    # Group sessions by month-year and then by day
    grouped_sessions = defaultdict(lambda: defaultdict(list))

    for date, filename, nickname in session_files:
        month_year_key = date.strftime("%Y-%m")
        day_key = date.strftime("%d")
        grouped_sessions[month_year_key][day_key].append((date, filename, nickname))

    # Write index HTML page
    with open(output_file, 'w', encoding='utf-8') as file:
        file.write("<html><head><title>IRC Sessions Index</title></head><body>")
        file.write("<h1>IRC Sessions Index</h1>\n")

        for month_year, days in grouped_sessions.items():
            file.write(f"<h2>{month_year}</h2>\n")
            for day, sessions in sorted(days.items()):
                day_number_name = datetime.strptime(day, "%d").strftime("%d (%A)")
                file.write(f"<h3>{day_number_name}</h3>\n<ul>\n")

                for date, filename, nickname in sorted(sessions):
                    # Extract relative path from filename
                    relative_path = os.path.relpath(filename, os.path.dirname(output_file))
                    file.write(f"  <li><a href=\"{relative_path}\" target=\"_blank\">{date.strftime('%Y-%m-%d')} ({nickname})</a> - {date.strftime('%H:%M')}</li>\n")

                file.write("</ul>\n")

        file.write("</body></html>")

# Main function
def main():
    import sys

    # Check for directory arguments
    if len(sys.argv) < 3:
        print("Usage: python merge_logs.py <log_directory> <output_directory>")
        return

    log_directory = sys.argv[1]
    output_directory = sys.argv[2]

    # List all .log files in the directory and subdirectories, case-insensitive
    log_files = []
    for root, dirs, files in os.walk(log_directory):
        for file in files:
            if file.lower().endswith('.log'):
                log_files.append(os.path.join(root, file))

    # Combine and sort sessions
    sessions = combine_sessions(log_files)

    # Output sessions to individual HTML files
    session_files = output_session_html(sessions, output_directory)

    # Generate index HTML
    index_file = os.path.join(output_directory, "index.html")
    generate_index_html(session_files, index_file)

if __name__ == "__main__":
    main()
