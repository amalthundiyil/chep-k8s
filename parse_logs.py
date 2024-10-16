import json
import subprocess
from datetime import datetime

def get_kubernetes_events(pod_name, namespace="default"):
    try:
        result = subprocess.run(
            ["kubectl", "get", "events",
             f"--field-selector=involvedObject.name={pod_name}",
             "-n", namespace,
             "--sort-by=.metadata.creationTimestamp",
             "-o", "json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        events = json.loads(result.stdout)
        return events
    except subprocess.CalledProcessError as e:
        print(f"Error fetching events: {e.stderr}")
        return None

def get_event_timestamp(event):
    if "lastTimestamp" in event and event["lastTimestamp"]:
        return event["lastTimestamp"]
    elif "eventTime" in event and event["eventTime"]:
        return event["eventTime"]
    else:
        return None

def parse_event_times(events):
    pull_time = None
    creation_time = None
    start_time_exec = None
    end_time_exec = None

    for event in events['items']:
        reason = event['reason']
        timestamp = get_event_timestamp(event)
        if not timestamp:
            continue  

        event_time = parse_timestamp(timestamp)

        if reason == "Pulling" and pull_time is None:
            pull_time = event_time
            print(f"Image pulling started at: {pull_time}")
        elif reason == "Pulled" and creation_time is None:
            creation_time = event_time
            print(f"Image successfully pulled at: {creation_time}")
        elif reason == "Started" and start_time_exec is None:
            start_time_exec = event_time
            print(f"Container started at: {start_time_exec}")
        elif (reason == "Succeeded" or reason == "Failed") and end_time_exec is None:
            end_time_exec = event_time
            print(f"Container finished at: {end_time_exec}")

    return pull_time, creation_time, start_time_exec, end_time_exec

def parse_timestamp(timestamp):
    try:
        return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")

def calculate_durations(pull_time, creation_time, start_time_exec, end_time_exec):
    if pull_time and creation_time:
        pull_duration = creation_time - pull_time
        print(f"Image Pull Duration: {pull_duration.total_seconds()} seconds")

    if creation_time and start_time_exec:
        creation_to_start_duration = start_time_exec - creation_time
        print(f"Creation to Start Duration: {creation_to_start_duration.total_seconds()} seconds")

    if start_time_exec and end_time_exec:
        task_run_time = end_time_exec - start_time_exec
        print(f"Task Run Time: {task_run_time.total_seconds()} seconds")

if __name__ == "__main__":
    pod_name = "root-pod"
    namespace = "default"

    events = get_kubernetes_events(pod_name, namespace)
    if events:
        pull_time, creation_time, start_time_exec, end_time_exec = parse_event_times(events)
        calculate_durations(pull_time, creation_time, start_time_exec, end_time_exec)

