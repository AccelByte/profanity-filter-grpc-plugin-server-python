#!/usr/bin/env bash

# profanity filter demo script

# Requires: bash curl jq

set -e
set -o pipefail

test -n "$AB_CLIENT_ID" || (echo "AB_CLIENT_ID is not set"; exit 1)
test -n "$AB_CLIENT_SECRET" || (echo "AB_CLIENT_SECRET is not set"; exit 1)
test -n "$AB_NAMESPACE" || (echo "AB_NAMESPACE is not set"; exit 1)

if [ -z "$GRPC_SERVER_URL" ] && [ -z "$EXTEND_APP_NAME" ]; then
  echo "GRPC_SERVER_URL or EXTEND_APP_NAME is not set"
  exit 1
fi

FILTER_NAME="pf_grpc_demo-$(echo $RANDOM | sha1sum | head -c 8)"

api_curl()
{
  curl -s -D api_curl_http_header.out -o api_curl_http_response.out -w '%{http_code}' "$@" > api_curl_http_code.out
  echo >> api_curl_http_response.out
  cat api_curl_http_response.out
}

clean_up()
{
  echo Deleting profanity filter ...
  curl -X DELETE "${AB_BASE_URL}/profanity-filter/v1/admin/namespaces/$AB_NAMESPACE/filters/${FILTER_NAME}" -H "Authorization: Bearer $ACCESS_TOKEN"
}

ACCESS_TOKEN="$(api_curl ${AB_BASE_URL}/iam/v3/oauth/token \
    -H 'Content-Type: application/x-www-form-urlencoded' \
    -u "$AB_CLIENT_ID:$AB_CLIENT_SECRET" \
    -d "grant_type=client_credentials" | jq --raw-output .access_token)"

if [ "$(cat api_curl_http_code.out)" -ge "400" ]; then
  cat api_curl_http_response.out
  exit 1
fi

trap clean_up EXIT

if [ -n "$GRPC_SERVER_URL" ]; then
  echo Creating custom profanity filter URL: $GRPC_SERVER_URL
  api_curl  -X PUT -s "${AB_BASE_URL}/profanity-filter/v1/admin/namespaces/$AB_NAMESPACE/filters/${FILTER_NAME}" -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d "{\"description\":\"test\",\"filterConfig\":{\"customServerConfig\":{\"gRPCServerAddress\":\"${GRPC_SERVER_URL}\"},\"type\":\"EXTEND_CUSTOM_SERVER\"}}" >/dev/null
  echo 

  if [ "$(cat api_curl_http_code.out)" -ge "400" ]; then
    exit 1
  fi
elif [ -n "$EXTEND_APP_NAME" ]; then
  echo Creating custom profanity filter app name: $EXTEND_APP_NAME
  api_curl  -X PUT -s "${AB_BASE_URL}/profanity-filter/v1/admin/namespaces/$AB_NAMESPACE/filters/${FILTER_NAME}" -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d "{\"description\":\"test\",\"filterConfig\":{\"appConfig\":{\"appName\":\"${EXTEND_APP_NAME}\"},\"type\":\"EXTEND_APP\"}}" >/dev/null
  echo 

  if [ "$(cat api_curl_http_code.out)" -ge "400" ]; then
    exit 1
  fi
else
  echo "GRPC_SERVER_URL or EXTEND_APP_NAME is not set"
  exit 1
fi

echo Test with bad word ...
api_curl -X POST -s "${AB_BASE_URL}/profanity-filter/v1/admin/namespaces/$AB_NAMESPACE/filters/${FILTER_NAME}/profane" -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d "{\"value\":\"bad\"}"
echo

if [ "$(cat api_curl_http_code.out)" -ge "400" ]; then
  exit 1
fi

if [ "$(jq .isProfane api_curl_http_response.out)" != 'true' ]; then
  exit 1
fi

echo Test with normal word ...
api_curl -X POST -s "${AB_BASE_URL}/profanity-filter/v1/admin/namespaces/$AB_NAMESPACE/filters/${FILTER_NAME}/profane" -H "Authorization: Bearer $ACCESS_TOKEN" -H 'Content-Type: application/json' -d "{\"value\":\"hello\"}"
echo

if [ "$(cat api_curl_http_code.out)" -ge "400" ]; then
  exit 1
fi

if [ "$(jq .isProfane api_curl_http_response.out)" != 'false' ]; then
  exit 1
fi
