#!/usr/bin/env bash
set -e

TARGET_FILE="paiv-solutions-$(date '+%s').zip"

if [ -z "$1" ]; then
    echo 'usage: dist <dir>'
    exit 1
fi

. .secrets

TARGET_DIR=$(pwd)
TARGET_FILE="$TARGET_DIR/$TARGET_FILE"
pushd "$1"

find . -type f -name '*.sol' \! -empty | zip -@ "$TARGET_FILE"

popd

SHACODE=$(shasum -a 256 "$TARGET_FILE" | cut -d ' ' -f1)
echo "SHA-256: $SHACODE"

curl -v -F "private_id=$PRIVATE_ID" -F "file=@$TARGET_FILE" 'https://monadic-lab.org/submit'
