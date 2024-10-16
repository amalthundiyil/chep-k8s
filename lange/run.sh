#!/bin/bash

set -xe

bash cleanup.sh
# bash setup.sh

pods=(bin-bash python-print root-python root-fillrandom)

for pod in "${pods[@]}"; do
    go run main.go "manifests/${pod}.yaml" >> "results/${pod}.log"
    python3 analyse.py "results/${pod}.log" >> "results/$(hostname)-$(date -Ins)"
    bash cleanup.sh
    # bash setup.sh
done

