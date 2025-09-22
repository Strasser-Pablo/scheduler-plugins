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

var (
	// Defaults for HyperAI
	// DefaultHyperAIGRPCAddress is the default gRPC server address
	DefaultHyperAIGRPCAddress = "localhost:50051"
	// DefaultHyperAIScore is the default fallback score returned by the HyperAI plugin
	DefaultHyperAIScore int64 = 0
)

// SetDefaults_HyperAIArgs sets the default parameters for HyperAI plugin.
func SetDefaults_HyperAIArgs(obj *HyperAIArgs) {
	if obj.GRPCAddress == nil {
		obj.GRPCAddress = &DefaultHyperAIGRPCAddress
	}
	if obj.Score == nil {
		obj.Score = &DefaultHyperAIScore
	}
}
