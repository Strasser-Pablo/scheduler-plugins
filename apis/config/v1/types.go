/*
Copyright 2022 The Kubernetes Authors.

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

package v1

import (
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// +k8s:deepcopy-gen:interfaces=k8s.io/apimachinery/pkg/runtime.Object

// HyperAIArgs holds arguments used to configure the HyperAI plugin.
type HyperAIArgs struct {
	metav1.TypeMeta `json:",inline"`

	// gRPC server address for Python scoring service.
	GRPCAddress *string `json:"grpcAddress,omitempty"`

	// Score is the constant score value to return for all nodes (for initial version).
	// Valid range is 0-100. Default is 0.
	Score *int64 `json:"score,omitempty"`
}
