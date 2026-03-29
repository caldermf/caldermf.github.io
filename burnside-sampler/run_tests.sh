#!/bin/sh
set -eu

python -m unittest discover -s tests -v

mkdir -p /tmp/sage-home
env HOME=/tmp/sage-home sage -python -m unittest discover -s tests -v
