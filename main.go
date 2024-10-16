package main

import (
        "context"
        "fmt"
        "log"
        "time"

        v1 "k8s.io/api/core/v1"
        metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
        "k8s.io/client-go/kubernetes"
        "k8s.io/client-go/tools/clientcmd"
)

func createPod(clientset *kubernetes.Clientset, podName, image string, command []string) error {
        pod := &v1.Pod{
                ObjectMeta: metav1.ObjectMeta{
                        Name: podName,
                },
                Spec: v1.PodSpec{
                        Containers: []v1.Container{
                                {
                                        Name:    podName,
                                        Image:   image,
                                        Command: command,
                                },
                        },
                        RestartPolicy: v1.RestartPolicyNever,
                },
        }

        _, err := clientset.CoreV1().Pods("default").Create(context.TODO(), pod, metav1.CreateOptions{})
        if err != nil {
                return fmt.Errorf("failed to create pod %s: %v", podName, err)
        }
        fmt.Printf("Created pod %s successfully.\n", podName)
        return nil
}

func main() {
        kubeconfig := "/etc/rancher/k3s/k3s.yaml"

        // kubeconfig := filepath.Join(homedir.HomeDir(), ".kube", "config")

        config, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
        if err != nil {
                log.Fatalf("Error building kubeconfig: %s", err.Error())
        }

        clientset, err := kubernetes.NewForConfig(config)
        if err != nil {
                log.Fatalf("Error creating Kubernetes client: %s", err.Error())
        }

        pods := []struct {
                name    string
                image   string
                command []string
        }{
                {"bin-bash", "rootproject/root:6.32.02-ubuntu24.04", []string{"/bin/bash"}},
                {"python-print", "rootproject/root:6.32.02-ubuntu24.04", []string{"python", "-c", "print('Hello World')"}},
                {"root-python", "rootproject/root:6.32.02-ubuntu24.04", []string{"python", "-c", "import ROOT"}},
                {"root-fillrandom", "rootproject/root:6.32.02-ubuntu24.04", []string{"python", "/opt/root/tutorials/pyroot/fillrandom.py"}},
        }

        // Create the pods
        for _, pod := range pods {
                err := createPod(clientset, pod.name, pod.image, pod.command)
                if err != nil {
                        log.Fatalf("Error creating pod: %s", err.Error())
                }
        }

        // Wait a few seconds before monitoring the pods
        time.Sleep(5 * time.Second)

        // Monitor the pods
        for _, pod := range pods {
                fmt.Printf("Monitoring pod: %s\n", pod.name)

                // Create a context for API calls
                ctx := context.TODO()

                // Record start time
                startTime := time.Now()

                // Loop until the pod is running or has finished
                for {
                        // Retrieve the pod object
                        podStatus, err := clientset.CoreV1().Pods("default").Get(ctx, pod.name, metav1.GetOptions{})
                        if err != nil {
                                log.Fatalf("Error retrieving pod: %s", err.Error())
                        }

                        // Check if the pod has reached a terminal state
                        if podStatus.Status.Phase == v1.PodRunning || podStatus.Status.Phase == v1.PodSucceeded || podStatus.Status.Phase == v1.PodFailed {
                                break
                        }

                        // Monitor container statuses
                        for _, containerStatus := range podStatus.Status.ContainerStatuses {
                                if containerStatus.State.Running != nil {
                                        // Calculate pull and run time
                                        pullTime := containerStatus.State.Running.StartedAt.Time.Sub(podStatus.CreationTimestamp.Time)
                                        runTime := time.Since(startTime)

                                        // Print results
                                        fmt.Printf("Pod: %s - Image pull time: %s, Total run time: %s\n", pod.name, pullTime, runTime)
                                }
                        }

                        // Wait for a few seconds before checking again
                        time.Sleep(2 * time.Second)
                }
        }

        fmt.Println("All pods created and monitored successfully.")
}


