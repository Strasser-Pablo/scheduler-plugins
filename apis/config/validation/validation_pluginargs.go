/*
Copyright 2023 The Kubernetes Authors.

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

package validation

import (
"k8s.io/apimachinery/pkg/util/validation/field"

"sigs.k8s.io/scheduler-plugins/apis/config"
)

// ValidateHyperAIArgs validates HyperAI arguments.
func ValidateHyperAIArgs(path *field.Path, args *config.HyperAIArgs) error {
var allErrs field.ErrorList

scorePath := path.Child("score")
if args.Score < 0 || args.Score > 100 {
allErrs = append(allErrs, field.Invalid(scorePath, args.Score, "score must be between 0 and 100"))
}

grpcAddressPath := path.Child("grpcAddress")
if args.GRPCAddress == "" {
allErrs = append(allErrs, field.Required(grpcAddressPath, "grpcAddress is required"))
}

return allErrs.ToAggregate()
}
