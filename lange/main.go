package main

import (
	"context"
	"flag"
	"fmt"
	"io/ioutil"
	"os"
	"regexp"
	"time"

	v1batch "k8s.io/api/batch/v1"
	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/fields"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/kubernetes/scheme"
	"k8s.io/client-go/tools/cache"
	"k8s.io/client-go/tools/clientcmd"
)

func check(e error) {
	if e != nil {
		panic(e)
	}
}

func main() {

	if len(os.Args) < 2 {
		fmt.Println("Please provide manifest")
		os.Exit(1)
	}
	manifestFile := os.Args[1]

	var kubeconfig *string = new(string)
	*kubeconfig = "/etc/rancher/k3s/k3s.yaml"
	flag.Parse()

	namespace := "default"

	config, err := clientcmd.BuildConfigFromFlags("", *kubeconfig)
	if err != nil {
		panic(err)
	}

	clientset, err := kubernetes.NewForConfig(config)
	if err != nil {
		panic(err.Error())
	}

	// Read YAML file
	batchDat, err := ioutil.ReadFile(manifestFile)
	check(err)
	// fmt.Print(string(dat))
	batchDecode := scheme.Codecs.UniversalDeserializer().Decode

	batchObj, _, err := batchDecode([]byte(batchDat), nil, nil)
	if err != nil {
		fmt.Printf("%#v", err)
	}

	job := batchObj.(*v1batch.Job)
	jobName := job.GetName()
	containerName := job.Spec.Template.Spec.Containers[0].Name
	fmt.Printf("Job %q with container %q\n", jobName, containerName)

	// Watch resources
	var creationTimestamp time.Time
	var duration time.Duration
	var pullTime string
	var podName string
	succeeded := false
	watchlist := cache.NewListWatchFromClient(clientset.CoreV1().RESTClient(), "pods", namespace,
		fields.Everything())
	_, controller := cache.NewInformer(
		watchlist,
		&v1.Pod{},
		time.Second*0,
		cache.ResourceEventHandlerFuncs{
			AddFunc: func(obj interface{}) {
				podObj := obj.(*v1.Pod)
				podName = podObj.ObjectMeta.GetName()
				fmt.Printf("New pod added: %s \n", podName)
			},
			DeleteFunc: func(obj interface{}) {
				fmt.Printf("delete: %s \n", obj)
			},
			UpdateFunc: func(oldObj, newObj interface{}) {
				// fmt.Printf("old: %s\nnew: %s \n", oldObj, newObj)
				// fmt.Println("New pod update")
				podObj := newObj.(*v1.Pod)
				if len(podObj.Status.Conditions) == 1 {
					if podObj.Status.Conditions[0].Type == v1.PodScheduled && v1.PodConditionType(podObj.Status.Conditions[0].Status) == v1.PodConditionType(v1.ConditionTrue) {
						creationTimestamp = time.Now()
						fmt.Println("Pod scheduled on", podObj.Spec.NodeName, creationTimestamp.UnixNano(), "lastTransition:", podObj.Status.Conditions[0].LastTransitionTime.Time)
						return
					}
				}
				if creationTimestamp.IsZero() {
					return
				}
				if !succeeded && podObj.Status.Phase == v1.PodSucceeded {
					fmt.Println("Pod succeeded")
					succeeded = true
					for container := range podObj.Status.ContainerStatuses {
						statuses := podObj.Status.ContainerStatuses[container]
						if statuses.Name == containerName {
							startTime := time.Now()
							duration = time.Since(creationTimestamp)
							fmt.Println(startTime.UnixNano(), "official start time:", statuses.State.Terminated.StartedAt.Time, statuses.State.Terminated.FinishedAt)
							fmt.Println(creationTimestamp, startTime, "Overall run time:", startTime.Sub(creationTimestamp).Milliseconds(), "ms", duration)
						}
					}
					// Get official pull time
					options := metav1.ListOptions{
						FieldSelector: fmt.Sprintf("involvedObject.kind==Pod,reason==Pulled,involvedObject.name==%s", podName),
					}
					var outputLine string
					events, err := clientset.CoreV1().Events(namespace).List(context.TODO(), options)
					check(err)
					for i := range events.Items {
						outputLine = events.Items[i].Message
					}
					re := regexp.MustCompile(`.*Successfully pulled image \".*\" in (.*)`)
					match := re.FindStringSubmatch(outputLine)
					if match != nil {
						pullTime = match[1]
					}
					fmt.Printf("Official pull time: %q\n", pullTime)
					// Delete job
					fmt.Println("Deleting Job", jobName)
					clientset.BatchV1().Jobs(namespace).Delete(context.TODO(), jobName, metav1.DeleteOptions{})
					// Delete pod
					fmt.Println("Deleting Pod", podName)
					clientset.CoreV1().Pods(namespace).Delete(context.TODO(), podName, metav1.DeleteOptions{})
					os.Exit(0)
				}
				if podObj.Status.Phase == v1.PodRunning {
					fmt.Println("Pod is running")
					for container := range podObj.Status.ContainerStatuses {
						// fmt.Println(podObj.Status.ContainerStatuses[container].Name, podObj.Status.ContainerStatuses[container].Ready)
						if podObj.Status.ContainerStatuses[container].Name == containerName && podObj.Status.ContainerStatuses[container].Ready {
							startTime := time.Now()
							duration = time.Since(creationTimestamp)
							fmt.Println(startTime.UnixNano(), "official start time:", podObj.Status.ContainerStatuses[container].State.Running.StartedAt.Time)
							fmt.Println(creationTimestamp, startTime, "Overall pull time:", startTime.Sub(creationTimestamp).Milliseconds(), "ms", duration)
						}
					}
				}
			},
		},
	)
	stop := make(chan struct{})
	go controller.Run(stop)

	// Schedule job
	result, err := clientset.BatchV1().Jobs(namespace).Create(context.TODO(), job, metav1.CreateOptions{})
	check(err)
	fmt.Printf("Created job %q.\n", result.GetName())

	// Wait forever
	select {}
}

