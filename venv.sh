#!/bin/bash

sudo apt install -y python3.8-venv python3-pip
python3 -m venv ./myvenv
. ./myvenv/bin/activate
python3 -m pip install "enoslib>=8.0.0,<9.0.0"
