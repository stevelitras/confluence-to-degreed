#!/bin/bash

: '
Loop through directory structure and pip install all function and layer libraries as
specified in their respective requirements.txt
TODO: change this for the new "sam build" command.
'

for dir in sam/functions/*; do
  echo "$dir"
  if [ -f "$dir"/requirements.txt ]; then
    rm -rf "$dir"/vendored  # clean it up to start fresh just in case
    (pip install --no-cache-dir --disable-pip-version-check -t "$dir"/vendored/ -r "$dir"/requirements.txt)
  fi
done

for dir in sam/layers/*; do
  echo "$dir"
  if [ -f "$dir"/requirements.txt ]; then
    rm -rf "$dir"/vendored  # clean it up to start fresh just in case
    (pip install --no-cache-dir --disable-pip-version-check -t "$dir"/vendored/ -r "$dir"/requirements.txt)
  fi
done
