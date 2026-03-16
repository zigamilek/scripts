import requests
import urllib
import json

def send_request():
    # all events with properties
    # GET https://eu.posthog.com/api/projects/13712/events/
    
    data = {
        "properties": [
            {
                "key": "$current_url",
                "value": "advanced-guide",
                "operator": "contains",
                "type": "event"
            }
        ]
        
        #"distinct_id": "018f157a-4a9d-74a9-b261-d088535f2b56"
    }

    properties = [
        {
            "key": "$current_url",
            "value": "https://zebrabi.com/guide/how-to-create-calculation-groups-in-power-bi/",
            "operator": "exact",
            "type": "event"
        }
    ]

    properties2 = [
        {
            "key":"$current_url",
            "value":"guide",
            "operator":"contains",
            "type":"event"
        }
    ]
    data2 = {
        "properties": properties2
    }

    properties3 = {
        "key": "$current_url",
        "value": "advanced-guide",
        "operator": "contains",
        "type": "event"
    }

    properties = urllib.parse.quote(
        '[{"key":"$current_url","value":"advanced-guide","operator":"contains","type":"event"}]'
    )
    properties = json.dumps(properties2)
    print(f"https://eu.posthog.com/api/projects/13712/events/?properties={properties}")
    print(urllib.parse.urlencode(properties3))

    properties_string = urllib.parse.quote(json.dumps(properties))
    
    
    json_data = json.dumps(data)

    #query_parameters = urllib.parse.quote(data)
    #query_parameters = urllib.parse.urlencode(data)
    query_parameters = f"properties={properties}"
    query_parameters = urllib.parse.urlencode(properties3)
    
    ##print(query_parameters)
    ##print(f"properties={urllib.parse.quote(properties_string)}")
    #print(properties_string)

    try:
        response = requests.get(
            url="https://eu.posthog.com/api/projects/13712/events/values/",
            #url="https://eu.posthog.com/api/projects/13712/events/?distinct_id=018f157a-4a9d-74a9-b261-d088535f2b56",
            #url=f"https://eu.posthog.com/api/projects/13712/events/?properties={urllib.parse.quote(properties_string)}",
            #url=f"https://eu.posthog.com/api/projects/13712/events/?properties={properties}",
            params=query_parameters,
            headers={
                "Authorization": "Bearer REMOVED_POSTHOG_API_TOKEN",
            },
        )
        
        print('Response HTTP Status Code: {status_code}'.format(
            status_code=response.status_code))
        
        print('Response HTTP Response Body: ')
        
        print(json.dumps(response.json(), indent=4))
    
    except requests.exceptions.RequestException:
        print('HTTP Request failed')

send_request()