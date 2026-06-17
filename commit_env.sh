#!/bin/bash

# Ensure an environment target and description are provided
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "❌ Usage: ./commit_env.sh [dev|test|stage|prod] \"Commit message details\""
    exit 1
fi

TARGET_ENV=$1
COMMIT_MSG=$2
TARGET_FILE="environments/${TARGET_ENV}/verified_script.py"

# Verify the script exists before tracking
if [ ! -f "$TARGET_FILE" ]; then
    echo "❌ Error: Deployment file not found at ${TARGET_FILE}"
    exit 1
fi

echo "📦 [Jarvis Git Sync]: Scanning workspace for deployment updates..."

# Stage only the specific environment code changes and the ledger metrics
git add "$TARGET_FILE" cluster_logs/performance_ledger.json config/environments.json

# Commit the changes with an automated tracking prefix
git commit -m "jarvis[${TARGET_ENV}]: ${COMMIT_MSG}"

echo "🚀 [Jarvis Git Sync]: Workspace successfully committed! Ready for deployment push."
