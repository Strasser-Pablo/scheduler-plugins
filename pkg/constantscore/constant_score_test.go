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
	"testing"

	v1 "k8s.io/api/core/v1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/runtime"
	"k8s.io/kubernetes/pkg/scheduler/framework"

	"sigs.k8s.io/scheduler-plugins/apis/config"
)

func TestConstantScoreBasic(t *testing.T) {
	tests := []struct {
		name          string
		args          runtime.Object
		expectedScore int64
		expectError   bool
	}{
		{
			name:          "default score",
			args:          nil,
			expectedScore: 50,
			expectError:   false,
		},
		{
			name: "custom score",
			args: &config.ConstantScoreArgs{
				Score: 75,
			},
			expectedScore: 75,
			expectError:   false,
		},
		{
			name: "invalid negative score",
			args: &config.ConstantScoreArgs{
				Score: -1,
			},
			expectedScore: 0,
			expectError:   true,
		},
		{
			name: "invalid high score",
			args: &config.ConstantScoreArgs{
				Score: 101,
			},
			expectedScore: 0,
			expectError:   true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			ctx := context.Background()

			// Create the plugin with nil handle for basic testing
			plugin, err := New(ctx, tt.args, nil)

			if tt.expectError {
				if err == nil {
					t.Errorf("Expected error but got none")
				}
				return
			}

			if err != nil {
				t.Fatalf("Failed to create plugin: %v", err)
			}

			constantScore, ok := plugin.(*ConstantScore)
			if !ok {
				t.Fatalf("Plugin is not ConstantScore type")
			}

			// Verify the plugin name
			if constantScore.Name() != Name {
				t.Errorf("Expected plugin name %q, got %q", Name, constantScore.Name())
			}

			// Verify the configured score
			if constantScore.score != tt.expectedScore {
				t.Errorf("Expected internal score %d, got %d", tt.expectedScore, constantScore.score)
			}

			// Test ScoreExtensions (should return nil)
			if constantScore.ScoreExtensions() != nil {
				t.Error("ScoreExtensions should return nil")
			}
		})
	}
}

func TestConstantScoreScoring(t *testing.T) {
	ctx := context.Background()

	// Create the plugin with nil handle
	plugin, err := New(ctx, &config.ConstantScoreArgs{Score: 42}, nil)
	if err != nil {
		t.Fatalf("Failed to create plugin: %v", err)
	}

	constantScore := plugin.(*ConstantScore)

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
	score, status := constantScore.Score(ctx, nil, pod, nodeInfo)
	if !status.IsSuccess() {
		t.Fatalf("Score failed: %v", status)
	}

	if score != 42 {
		t.Errorf("Expected score 42, got %d", score)
	}
}

func TestConstantScoreNilNode(t *testing.T) {
	ctx := context.Background()

	// Create the plugin with nil handle
	plugin, err := New(ctx, nil, nil)
	if err != nil {
		t.Fatalf("Failed to create plugin: %v", err)
	}

	constantScore := plugin.(*ConstantScore)

	// Create test pod and nil node info
	pod := &v1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      "test-pod",
			Namespace: "default",
		},
	}

	nodeInfo := framework.NewNodeInfo()
	// Don't set a node, leaving it nil

	// Test scoring with nil node
	score, status := constantScore.Score(ctx, nil, pod, nodeInfo)
	if status.IsSuccess() {
		t.Error("Expected error for nil node, got success")
	}

	if score != 0 {
		t.Errorf("Expected score 0 for error case, got %d", score)
	}
}
