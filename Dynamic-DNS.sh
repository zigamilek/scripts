#!/bin/bash

# Cloudflare API credentials
CF_API_TOKEN="uBsTSdgcD2DbA2Cozfi752qvrnj2s__XatNY9BLL"
CF_ZONE_NAME="milek.org"
#CF_ZONE_NAME="zigamilek.com"

# Subdomain to update (default to "linhartova" if not specified)
SUBDOMAIN=${1:-linhartova}

# Get current public IP address
#IP=$(curl -s https://api.ipify.org)
#IP=$(curl -s https://ifconfig.co)
#IP=$(curl -s https://ifconfig.me)
#IP=$(curl -s https://ifconfig.io)
IP=$(curl -s https://ipv4.icanhazip.com)


# Check if IP file exists and compare the old IP with the current one
IP_FILE="/tmp/current_ip.txt"
if [ -f $IP_FILE ]; then
    OLD_IP=$(cat $IP_FILE)
    if [ "$IP" == "$OLD_IP" ]; then
        echo "IP address has not changed ($IP). Exiting."
        exit 0
    fi
fi

# Save the current IP to file
echo $IP > $IP_FILE

# Get the Zone ID for the domain
CF_ZONE_ID=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones?name=$CF_ZONE_NAME" \
     -H "Authorization: Bearer $CF_API_TOKEN" \
     -H "Content-Type: application/json" | jq -r '.result[0].id')

if [ -z "$CF_ZONE_ID" ] || [ "$CF_ZONE_ID" == "null" ]; then
    echo "Failed to get Zone ID for $CF_ZONE_NAME"
    exit 1
fi

# Get the DNS Record ID
DNS_RECORD=$(curl -s -X GET "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records?type=A&name=$SUBDOMAIN.$CF_ZONE_NAME" \
     -H "Authorization: Bearer $CF_API_TOKEN" \
     -H "Content-Type: application/json")

RECORD_ID=$(echo $DNS_RECORD | jq -r '.result[0].id')

if [ -z "$RECORD_ID" ] || [ "$RECORD_ID" == "null" ]; then
    echo "DNS record for $SUBDOMAIN.$CF_ZONE_NAME not found. Creating a new one."
    # Create new DNS record
    CREATE_RECORD=$(curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records" \
         -H "Authorization: Bearer $CF_API_TOKEN" \
         -H "Content-Type: application/json" \
         --data "{\"type\":\"A\",\"name\":\"$SUBDOMAIN.$CF_ZONE_NAME\",\"content\":\"$IP\",\"ttl\":1,\"proxied\":false}")

    SUCCESS=$(echo $CREATE_RECORD | jq -r '.success')
    if [ "$SUCCESS" != "true" ]; then
        echo "Failed to create DNS record: $CREATE_RECORD"
        exit 1
    fi
    echo "DNS record created for $SUBDOMAIN.$CF_ZONE_NAME with IP $IP."
else
    # Update existing DNS record
    UPDATE_RECORD=$(curl -s -X PUT "https://api.cloudflare.com/client/v4/zones/$CF_ZONE_ID/dns_records/$RECORD_ID" \
         -H "Authorization: Bearer $CF_API_TOKEN" \
         -H "Content-Type: application/json" \
         --data "{\"type\":\"A\",\"name\":\"$SUBDOMAIN.$CF_ZONE_NAME\",\"content\":\"$IP\",\"ttl\":1,\"proxied\":false}")

    SUCCESS=$(echo $UPDATE_RECORD | jq -r '.success')
    if [ "$SUCCESS" != "true" ]; then
        echo "Failed to update DNS record: $UPDATE_RECORD"
        exit 1
    fi
    echo "DNS record updated for $SUBDOMAIN.$CF_ZONE_NAME with IP $IP"
fi

exit 0
