import sys
import statistics
import pathlib
import json

def convertToSeconds(timeString):
    if timeString.endswith("ms"):
        return float(timeString[:-2])*0.001
    timeSplit = timeString.split("m")
    minutes = 0
    if len(timeSplit) > 1:
        minutes = int(timeSplit[0])
    seconds = float(timeSplit[-1].strip("s"))
    timeInSeconds = minutes*60 + seconds
    return timeInSeconds


def getMeanAndError(valueList):
    if len(valueList) == 0:
        return 0, 0
    mean = sum(valueList) / len(valueList)
    res = statistics.pstdev(valueList)
    return mean, res


def main():
    if len(sys.argv) < 2:
        print("Please provide log file name for analysis.")
        return
    logfileName = sys.argv[1]
    kubernetesPullTimeList = []
    measuredPullTimeList = []
    runTimeList = []
    bytesTransferredList = []
    nodeName = ""
    jobName = ""
    with open(logfileName) as logfile:
        for line in logfile.readlines():
            # print(line.strip())
            if not nodeName and line.find("Pod scheduled on") >= 0:
                nodeName = line.split()[3]
            if not jobName and line.find("with container") >= 0:
                jobName = line.split("\"")[1]
            if line.find("Overall pull time") >= 0:
                measuredPullTime = line.strip().split(" ")[-3]
                measuredPullTimeList.append(float(measuredPullTime)*0.001)
                print("--->", measuredPullTimeList[-1])
            if line.find("Overall run time") >= 0:
                runTime = line.strip().split(" ")[-3]
                runTimeList.append(float(runTime)*0.001)
                # print("--->", runTimeList[-1])
            if line.find("Official pull time") >= 0:
                kubernetesPull = line.strip().split("\"")[-2].split(" ")[0][:-1]
                kubernetesPullTimeList.append(convertToSeconds(kubernetesPull))
                # print("--->", kubernetesPullTimeList[-1])
            if line.find("download.sz_transferred_bytes") >= 0:
                bytesTransferred = line.split("|")[-2]
                bytesTransferredList.append(float(bytesTransferred)*1e-6)
                # print("--->", bytesTransferredList[-1])
            if line.find("Size:") >= 0:
                bytesTransferred = line.split()[-1]
                bytesTransferredList.append(float(bytesTransferred)*1e-6)
                # print("--->", bytesTransferredList[-1])
    createTimeList = []
    workTimeList = []
    for i in range(len(kubernetesPullTimeList)):
        createTimeList.append(measuredPullTimeList[i]-kubernetesPullTimeList[i])
        workTimeList.append(runTimeList[i]-measuredPullTimeList[i])
    filePath = pathlib.Path("data.json")
    data = {}
    if not filePath.exists():
        with open(filePath, "w") as jsonFile:
            json.dump(data, jsonFile)
    with open(filePath, "r") as jsonFile:
        data = json.load(jsonFile)
    if not jobName in data:
        data[jobName] = {}
    if nodeName in data[jobName]:
        print(f"Warning: {nodeName} for {jobName} already exists. Overwriting")
    data[jobName][nodeName] = {}
    print(jobName)
    print(nodeName)
    mean, res = getMeanAndError(measuredPullTimeList)
    print(f"MeasuredPullTime: {mean} +/- {res}")
    data[jobName][nodeName]["MeasuredPullTime"] = [mean, res]
    mean, res = getMeanAndError(runTimeList)
    print(f"RunTime: {mean} +/- {res}")
    data[jobName][nodeName]["RunTime"] = [mean, res]
    mean, res = getMeanAndError(kubernetesPullTimeList)
    print(f"KubernetesPullTime: {mean} +/- {res}")
    data[jobName][nodeName]["KubernetesPullTime"] = [mean, res]
    mean, res = getMeanAndError(createTimeList)
    print(f"CreateTime: {mean} +/- {res}")
    data[jobName][nodeName]["CreateTime"] = [mean, res]
    mean, res = getMeanAndError(workTimeList)
    print(f"WorkTime: {mean} +/- {res}")
    data[jobName][nodeName]["WorkTime"] = [mean, res]
    mean, res = getMeanAndError(bytesTransferredList)
    print(f"BytesTransferred: {mean} +/- {res}")
    data[jobName][nodeName]["BytesTransferred"] = [mean, res]
    with open(filePath, "w") as jsonFile:
        json.dump(data, jsonFile)

main()
