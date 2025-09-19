#!/usr/bin/env python3
"""
Test client for the scheduler ONNX model
"""
import numpy as np
import requests
import json

def test_triton_model(triton_url="http://localhost:8000"):
    """Test the model via Triton HTTP API"""
    
    # Example input: CPU=500m, Memory=512MB
    cpu_millicores = 500.0
    memory_mb = 512.0
    
    # Prepare input data
    inputs = [
        {
            "name": "features",
            "shape": [1, 2],
            "datatype": "FP32",
            "data": [cpu_millicores, memory_mb]
        }
    ]
    
    outputs = [
        {
            "name": "score"
        }
    ]
    
    payload = {
        "inputs": inputs,
        "outputs": outputs
    }
    
    # Make inference request
    url = f"{triton_url}/v2/models/scheduler_model/infer"
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        result = response.json()
        score_normalized = result["outputs"][0]["data"][0]
        score_0_100 = int(score_normalized * 100)
        
        print(f"✅ Triton inference successful!")
        print(f"   Input: CPU={cpu_millicores}m, Memory={memory_mb}MB")
        print(f"   Output: {score_normalized:.3f} (normalized)")
        print(f"   Score: {score_0_100}/100")
        
        return score_0_100
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Triton inference failed: {e}")
        return None

if __name__ == "__main__":
    test_triton_model()
