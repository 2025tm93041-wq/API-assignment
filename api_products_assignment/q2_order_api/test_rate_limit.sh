#!/usr/bin/env bash
# Sends 8 requests through Kong; requests 6-8 should return 429.
for i in $(seq 1 8); do
  code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/orders)
  echo "Request $i -> HTTP $code"
done
echo; echo "Headers of one more call:"
curl -i -s http://localhost:8000/api/orders | head -15
