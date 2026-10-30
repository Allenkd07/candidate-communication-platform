#!/usr/bin/env bash
# Deploys the committed HEAD to the VM: GCP_PROJECT=... GCP_ZONE=... GCP_VM=... ./deploy.sh
set -euo pipefail

: "${GCP_PROJECT:?set GCP_PROJECT}" "${GCP_ZONE:?set GCP_ZONE}" "${GCP_VM:?set GCP_VM}"
APP_DIR=/opt/ccp

if [ -n "$(git status --porcelain)" ]; then
  echo "Uncommitted changes are not deployed; commit or stash them first." >&2
fi

git archive --format=tar.gz HEAD | gcloud compute ssh "$GCP_VM" --project "$GCP_PROJECT" --zone "$GCP_ZONE" \
  --command "sudo mkdir -p $APP_DIR && sudo tar -xzf - -C $APP_DIR && cd $APP_DIR && \
    sudo docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build --remove-orphans && \
    sudo docker image prune -f"
