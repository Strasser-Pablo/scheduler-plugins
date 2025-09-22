//go:build integration
// +build integration

package integration

import (
	"context"
	"testing"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/kubernetes/pkg/scheduler/framework"
	"sigs.k8s.io/scheduler-plugins/pkg/hyperai"
)

func TestHyperAIIntegration(t *testing.T) {
	// This is a placeholder for a real integration test.
	// In a real test, you would set up a scheduler with the HyperAI plugin enabled,
	// create nodes and pods, and verify scheduling behavior.
	// Here, we just check that the plugin can be constructed and returns a score.

	plugin, err := hyperai.New(context.Background(), &struct{}{}, nil)
	if err != nil {
		t.Fatalf("failed to create HyperAI plugin: %v", err)
	}

	pod := &v1.Pod{ObjectMeta: metav1.ObjectMeta{Name: "test-pod"}}
	node := &v1.Node{ObjectMeta: metav1.ObjectMeta{Name: "test-node"}}
	nodeInfo := framework.NewNodeInfo()
	nodeInfo.SetNode(node)

	score, status := plugin.(*hyperai.HyperAI).Score(context.Background(), framework.NewCycleState(), pod, nodeInfo)
	if status != nil && !status.IsSuccess() {
		t.Errorf("expected success, got %v", status)
	}
	if score != 0 {
		t.Errorf("expected score 0, got %d", score)
	}
}
