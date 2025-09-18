/*
Copyright 2024 The Kubernetes Authors.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package constantscore

import (
	"context"
	"fmt"

	v1 "k8s.io/api/core/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/klog/v2"
	"k8s.io/kubernetes/pkg/scheduler/framework"

	"sigs.k8s.io/scheduler-plugins/apis/config"
	"sigs.k8s.io/scheduler-plugins/apis/config/validation"
)

// ConstantScore is a score plugin that returns a constant score for all nodes.
// This plugin is useful as a baseline or for testing purposes.
type ConstantScore struct {
	logger klog.Logger
	handle framework.Handle
	score  int64
}

var _ = framework.ScorePlugin(&ConstantScore{})

// Name is the name of the plugin used in the Registry and configurations.
const Name = "ConstantScore"

// Name returns name of the plugin. It is used in logs, etc.
func (cs *ConstantScore) Name() string {
	return Name
}

// Score invoked at the score extension point.
// This plugin always returns the configured constant score for every node.
func (cs *ConstantScore) Score(ctx context.Context, state *framework.CycleState, pod *v1.Pod, nodeInfo *framework.NodeInfo) (int64, *framework.Status) {
	logger := klog.FromContext(klog.NewContext(ctx, cs.logger)).WithValues("ExtensionPoint", "Score")

	node := nodeInfo.Node()
	if node == nil {
		return 0, framework.NewStatus(framework.Error, "node not found")
	}

	logger.V(10).Info("Returning constant score",
		"podName", pod.Name,
		"podNamespace", pod.Namespace,
		"nodeName", node.Name,
		"score", cs.score)

	return cs.score, nil
}

// ScoreExtensions of the Score plugin.
func (cs *ConstantScore) ScoreExtensions() framework.ScoreExtensions {
	return nil
}

// New initializes a new plugin and returns it.
func New(ctx context.Context, args runtime.Object, h framework.Handle) (framework.Plugin, error) {
	logger := klog.FromContext(ctx).WithValues("plugin", Name)

	// Default score value
	score := int64(50) // Default to middle score

	// Update values from args, if specified.
	if args != nil {
		pluginArgs, ok := args.(*config.ConstantScoreArgs)
		if !ok {
			return nil, fmt.Errorf("want args to be of type ConstantScoreArgs, got %T", args)
		}

		if err := validation.ValidateConstantScoreArgs(pluginArgs, nil); err != nil {
			return nil, err
		}

		score = pluginArgs.Score
	}

	logger.Info("ConstantScore plugin initialized", "score", score)

	return &ConstantScore{
		logger: logger,
		handle: h,
		score:  score,
	}, nil
}
