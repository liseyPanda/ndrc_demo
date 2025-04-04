#!/bin/bash

echo "🔄 Waiting for Elasticsearch to be available..."
until curl -s http://elasticsearch:9200 > /dev/null; do
  sleep 5
  echo "⏳ Still waiting for Elasticsearch..."
done

echo "✅ Elasticsearch is up! Starting Kibana..."
exec /usr/share/kibana/bin/kibana