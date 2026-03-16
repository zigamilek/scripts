import requests
import urllib
import json

def send_request():
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer REMOVED_POSTHOG_API_TOKEN"
    }

    data = {
        "query": {
            "kind": "HogQLQuery",
            "query": """
                    SELECT
                        distinct_id
                    FROM
                        events
                    WHERE
                        ilike(properties.$current_url, '%/advanced-guide/%') OR
                        ilike(properties.$current_url, '%/guide/%')
                    GROUP BY
                        distinct_id
                    HAVING
                        COUNT(DISTINCT uuid) = SUM(CASE
                            WHEN ilike(properties.$current_url, '%/advanced-guide/%') OR
                                ilike(properties.$current_url, '%/guide/%') THEN 1
                            ELSE 0
                        END)
                    LIMIT 10000
                    OFFSET 10000
                """
        }
    }

    try:
        response = requests.post(
            url="https://eu.posthog.com/api/projects/13712/query",
            headers=headers, 
            json=data
        )
        
        print('Response HTTP Status Code: {status_code}'.format(
            status_code=response.status_code))
        
        #print('Response HTTP Response Body: ')
        
        #print(json.dumps(response.json(), indent=4))

        results = response.json()['results']

        for id_list in results:
            distinct_id = id_list[0]
            print(distinct_id)  
    
    except requests.exceptions.RequestException:
        print('HTTP Request failed')

send_request()