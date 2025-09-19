package hyperai

import (
	"context"
	"fmt"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/klog/v2"
	"k8s.io/kubernetes/pkg/scheduler/framework"
	"sigs.k8s.io/scheduler-plugins/apis/config"
)

const Name = "HyperAI"

// HyperAI is a ScorePlugin that calls a Python gRPC server for scoring.
type HyperAI struct {
	logger klog.Logger
	handle framework.Handle
	args   *config.HyperAIArgs
}

var _ framework.ScorePlugin = &HyperAI{}

func (p *HyperAI) Name() string {
	return Name
}

func (p *HyperAI) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) (int64, *framework.Status) {
	// Connect to gRPC server
	conn, err := grpc.Dial(p.args.GRPCAddress, grpc.WithTransportCredentials(insecure.NewCredentials()), grpc.WithTimeout(5*time.Second))
	if err != nil {
		p.logger.Error(err, "Failed to connect to HyperAI gRPC server, using fallback score", "address", p.args.GRPCAddress, "fallbackScore", p.args.Score, "pod", pod.Name, "node", nodeInfo.Node().Name)
		// Fallback to constant score if gRPC fails
		return p.args.Score, nil
	}
	defer conn.Close()

	// Create gRPC client
	client := NewHyperAIClient(conn)

	// Create request
	request := &ScoreRequest{
		PodName:  pod.Name,
		NodeName: nodeInfo.Node().Name,
	}

	// Call gRPC service
	response, err := client.GetScore(ctx, request)
	if err != nil {
		p.logger.Error(err, "Failed to get score from HyperAI gRPC server, using fallback score", "fallbackScore", p.args.Score, "pod", pod.Name, "node", nodeInfo.Node().Name)
		// Fallback to constant score if gRPC call fails
		return p.args.Score, nil
	}

	p.logger.Info("✅ HyperAI gRPC SUCCESS: Received score from gRPC server", "score", response.Score, "pod", pod.Name, "node", nodeInfo.Node().Name, "grpcAddress", p.args.GRPCAddress)
	return response.Score, nil
}

// ScoreExtensions of the Score plugin.
func (p *HyperAI) ScoreExtensions() framework.ScoreExtensions {
	return nil
}

func New(ctx context.Context, args runtime.Object, h framework.Handle) (framework.Plugin, error) {
	logger := klog.FromContext(ctx)
	pluginArgs, ok := args.(*config.HyperAIArgs)
	if !ok {
		return nil, fmt.Errorf("want args to be of type HyperAIArgs, got %T", args)
	}

	// Set default values if not specified
	if pluginArgs.GRPCAddress == "" {
		pluginArgs.GRPCAddress = "localhost:50051"
	}
	if pluginArgs.Score == 0 {
		pluginArgs.Score = 42
	}

	logger.Info("Creating HyperAI plugin", "grpcAddress", pluginArgs.GRPCAddress, "fallbackScore", pluginArgs.Score)

	return &HyperAI{
		logger: logger,
		handle: h,
		args:   pluginArgs,
	}, nil
}
