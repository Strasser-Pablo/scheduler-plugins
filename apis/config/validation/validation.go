package validation

import (
	"k8s.io/apimachinery/pkg/util/validation/field"
	"sigs.k8s.io/scheduler-plugins/apis/config"
)

// ValidateHyperAIArgs validates HyperAI plugin configuration.
func ValidateHyperAIArgs(args *config.HyperAIArgs, fldPath *field.Path) error {
	var allErrs field.ErrorList
	if args.Score < 0 || args.Score > 100 {
		allErrs = append(allErrs, field.Invalid(fldPath.Child("score"), args.Score, "must be between 0 and 100"))
	}
	if args.GRPCAddress == "" {
		allErrs = append(allErrs, field.Required(fldPath.Child("grpcAddress"), "gRPC address is required"))
	}
	if len(allErrs) == 0 {
		return nil
	}
	return allErrs.ToAggregate()
}
