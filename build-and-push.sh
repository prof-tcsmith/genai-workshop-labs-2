#!/usr/bin/env bash
# Facilitator only: build the workshop images and push them to Docker Hub.
# (c) Dr. Tim Smith, 2026
#
# Log in first with a Docker Hub ACCESS TOKEN (preferred over your password):
#   docker login -u proftsmith
# Then run this from the repo root:
#   ./build-and-push.sh
set -euo pipefail

NS=proftsmith

docker build -t "$NS/genai-live-demos:latest" ./live-demos
docker build -t "$NS/genai-mcp-lab:latest"   ./mcp-lab

docker push "$NS/genai-live-demos:latest"
docker push "$NS/genai-mcp-lab:latest"

echo "Pushed $NS/genai-live-demos and $NS/genai-mcp-lab.  (c) Dr. Tim Smith, 2026"
