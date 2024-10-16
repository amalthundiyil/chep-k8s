#!/bin/bash

POD_NAME=root-pod

kubectl get events --field-selector involvedObject.name=$POD_NAME --sort-by='.metadata.creationTimestamp'
kubectl delete events --field-selector involvedObject.name=$POD_NAME
cvmfs_config reload -c
cvmfs_config killall
crictl rmi -a
systemctl restart k3s
systemctl restart cvmfs-snapshotter

