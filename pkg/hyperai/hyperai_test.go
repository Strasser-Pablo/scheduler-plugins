package hyperai

import (
	"context"
	"testing"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/klog/v2"
	"k8s.io/kubernetes/pkg/scheduler/framework"
	"sigs.k8s.io/scheduler-plugins/apis/config"
)

func TestHyperAIScore(t *testing.T) {
	args := &config.HyperAIArgs{
		GRPCAddress: "localhost:50051",
		Score:       42,
	}
	plugin, err := New(klog.NewContext(context.Background(), klog.NewKlogr()), args, nil)
	if err != nil {
		t.Fatalf("failed to create plugin: %v", err)
	}
	hyperai := plugin.(*HyperAI)
	pod := &v1.Pod{}
	node := &v1.Node{ObjectMeta: metav1.ObjectMeta{Name: "node1"}}
	nodeInfo := framework.NewNodeInfo()
	nodeInfo.SetNode(node)
	score, status := hyperai.Score(context.Background(), framework.NewCycleState(), pod, nodeInfo)
	if status != nil && !status.IsSuccess() {
		t.Errorf("expected success, got %v", status)
	}
	if score != 42 {
		t.Errorf("expected score 42, got %d", score)
	}
}
