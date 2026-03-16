import requests
import datetime
import time

# Constants
CLIENT_ID = 'YOUR_CLIENT_ID'
ACCESS_TOKEN = 'YOUR_ACCESS_TOKEN'
API_URL = 'https://api.trakt.tv'

# Headers for authentication
headers = {
    'Content-Type': 'application/json',
    'trakt-api-version': '2',
    'trakt-api-key': CLIENT_ID,
    'Authorization': f'Bearer {ACCESS_TOKEN}'
}

# Date threshold
threshold_date = datetime.datetime(2017, 3, 1)

def get_history(page=1, limit=100):
    """Fetch the viewing history."""
    response = requests.get(
        f'{API_URL}/users/me/history',
        headers=headers,
        params={'page': page, 'limit': limit}
    )
    response.raise_for_status()
    return response.json()

def delete_history_item(item_id):
    """Delete a specific history item by its ID."""
    response = requests.delete(
        f'{API_URL}/users/me/history/{item_id}',
        headers=headers
    )
    response.raise_for_status()

def main():
    page = 1
    while True:
        history_items = get_history(page=page)
        if not history_items:
            break  # No more history items

        for item in history_items:
            watched_at = datetime.datetime.fromisoformat(item['watched_at'].replace('Z', '+00:00'))
            if watched_at < threshold_date:
                print(f"Deleting item {item['id']} watched at {watched_at}")
                delete_history_item(item['id'])
                time.sleep(1)  # Be polite and avoid hitting rate limits

        page += 1

if __name__ == '__main__':
    main()