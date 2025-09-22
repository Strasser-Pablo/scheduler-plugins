/*
Copyright 2021 The Kubernetes Authors.

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

package scheme

import (
"testing"

"k8s.io/apimachinery/pkg/runtime"
"k8s.io/apimachinery/pkg/runtime/schema"

"sigs.k8s.io/scheduler-plugins/apis/config"
v1 "sigs.k8s.io/scheduler-plugins/apis/config/v1"
)

func TestSchemeRegistration(t *testing.T) {
scheme := runtime.NewScheme()
if err := config.AddToScheme(scheme); err != nil {
t.Fatalf("Failed to register config scheme: %v", err)
}
if err := v1.AddToScheme(scheme); err != nil {
t.Fatalf("Failed to register v1 scheme: %v", err)
}

// Test that HyperAIArgs is registered
gvk := schema.GroupVersionKind{
Group:   "kubescheduler.config.k8s.io",
Version: "v1",
Kind:    "HyperAIArgs",
}

obj, err := scheme.New(gvk)
if err != nil {
t.Fatalf("Failed to create HyperAIArgs object: %v", err)
}

if _, ok := obj.(*v1.HyperAIArgs); !ok {
t.Fatalf("Expected *v1.HyperAIArgs, got %T", obj)
}
}
