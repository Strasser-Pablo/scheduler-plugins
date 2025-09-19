package main

import (
	"context"
	"fmt"
	"os"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/klog/v2"
	"k8s.io/kubernetes/pkg/scheduler/framework"
	"sigs.k8s.io/scheduler-plugins/apis/config"
	"sigs.k8s.io/scheduler-plugins/pkg/hyperai"
)

func main() {
	// Test the HyperAI plugin with gRPC connection
	args := &config.HyperAIArgs{
		GRPCAddress: "localhost:50051",
		Score:       42,
	}

	plugin, err := hyperai.New(klog.NewContext(context.Background(), klog.NewKlogr()), args, nil)
	if err != nil {
		fmt.Printf("Failed to create plugin: %v\n", err)
		os.Exit(1)
	}

	hyperaiPlugin := plugin.(*hyperai.HyperAI)

	// Create test pod and node
	pod := &v1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-pod",
			Namespace: "default",
		},
	}

	node := &v1.Node{
		ObjectMeta: metav1.ObjectMeta{
			Name: "test-node",
		},
	}

	nodeInfo := framework.NewNodeInfo()
	nodeInfo.SetNode(node)

	// Test scoring
	score, status := hyperaiPlugin.Score(context.Background(), framework.NewCycleState(), pod, nodeInfo)
	if status != nil && !status.IsSuccess() {
		fmt.Printf("Error scoring: %v\n", status.Message())
		os.Exit(1)
	}

	fmt.Printf("✅ HyperAI gRPC integration test PASSED - received score: %d\n", score)
}
