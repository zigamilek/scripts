import requests
import json
import time

# primer osebe, ki nima samo advanced guide eventov
# https://eu.posthog.com/project/13712/person/018d3a8f-61ad-7766-a1d4-e000fda54ac8#activeTab=events
# takih se ne sme izbrisati

output_file_path = '/Users/zigamilek/Desktop/distinct_ids.txt'

# Set the number of pages (= API calls) and the starting page (each page has 10.000 distinct ids)
NUM_PAGES = 400
STARTING_PAGE = 0

def send_request(offset):
	headers = {
		"Content-Type": "application/json",
		"Authorization": "Bearer REMOVED_POSTHOG_API_TOKEN"
	}

	# take only those that have only events from AI Guides
	# and only those that have 10 or less events from AI Guides
	query_template = """
		SELECT
			distinct_id
		FROM
			events
		GROUP BY
			distinct_id
		HAVING 
			COUNT(DISTINCT uuid) = SUM(CASE
				WHEN ilike(properties.$current_url, '%/advanced-guide/%') OR
					ilike(properties.$current_url, '%/guide/%') THEN 1
				ELSE 0
			END)
		    AND COUNT(DISTINCT uuid) <= 10
		LIMIT 10000
		OFFSET {offset}
	"""

	data = {
		"query": {
			"kind": "HogQLQuery",
			"query": query_template.format(offset=offset)
		}
	}

	try:
		while True:
			response = requests.post(
				url="https://eu.posthog.com/api/projects/13712/query",
				headers=headers, 
				json=data
			)

			if response.status_code == 429:
				retry_after = int(response.headers.get('retry-after', 600))  # Default to 600 seconds if header is missing
				print(f'Rate limit exceeded. Retrying after {retry_after} seconds.')
				time.sleep(retry_after)
				continue  # Retry the request
			else:
				break  # Exit loop if response is not 429
			
		#print('Response HTTP Status Code: {status_code}'.format(status_code=response.status_code))
		
		#print(response.headers)
		
		#print(response.json()['hogql'])

		#print('Response HTTP Response Body: ')
		
		#print(json.dumps(response.json(), indent=4))

		results = response.json()['results']
		return results
    
	except requests.exceptions.RequestException:
		print('HTTP Request failed')
		return None

def main():
	with open(output_file_path, 'w') as file:
		for i in range(NUM_PAGES):
			offset = (STARTING_PAGE + i) * 10000

			results = send_request(offset)

			if results is not None:
				for id_list in results:
					distinct_id = id_list[0]
					file.write(distinct_id + '\n')
			
			print(f'Batch {i+1} done.')

if __name__ == "__main__":
	main()