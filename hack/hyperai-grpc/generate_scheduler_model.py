#!/usr/bin/env python3

import torch
import torch.nn as nn
import numpy as np

class SchedulerModel(nn.Module):
    def __init__(self, input_size=2, hidden_size=64):
        super(SchedulerModel, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, 1)  # Output 1 feature
        
    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        x = self.relu(x)
        x = self.fc3(x)
        return x  # Keep as [batch, 1]

# Create and export model using your exact pattern
model = SchedulerModel()
model.eval()

# Create input data
input_data = torch.randn(1, 2)

print(f"Input shape: {input_data.shape}")
output = model(input_data)
print(f"Output shape: {output.shape}")

# Export using your exact call pattern
torch.onnx.export(
    model,
    input_data,
    "triton_models/scheduler_model/1/model.onnx",
    export_params=True,
    input_names=['features'],  # Using our name but your pattern
    output_names=['score'],    # Using our name but your pattern
    dynamic_axes={"features": {0: 'batch_size'}, "score": {0: 'batch_size'}}
)

print("ONNX model exported successfully using your pattern!")

# Verify the exported model
import onnx
onnx_model = onnx.load('triton_models/scheduler_model/1/model.onnx')
onnx.checker.check_model(onnx_model)

print("\nONNX model verification:")
print("Inputs:")
for input in onnx_model.graph.input:
    shape_info = [d.dim_value if d.dim_value > 0 else d.dim_param for d in input.type.tensor_type.shape.dim]
    print(f"  {input.name}: {shape_info}")
print("Outputs:")
for output in onnx_model.graph.output:
    shape_info = [d.dim_value if d.dim_value > 0 else d.dim_param for d in output.type.tensor_type.shape.dim]
    print(f"  {output.name}: {shape_info}")