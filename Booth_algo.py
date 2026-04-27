import torch
import torch.nn as nn

class BoothFunction(torch.autograd.Function):
    @staticmethod
    def forward(ctx, input, weight, bits=8):
        # 1. Save inputs for the backward pass
        ctx.save_for_backward(input, weight)
        
        # 2. Convert to integers for Booth's logic
        # We scale the floats to use the full bit range (e.g., -128 to 127 for 8-bit)
        m = input.round().to(torch.int32)
        q = weight.round().to(torch.int32)
        
        mask = (1 << bits) - 1
        a = torch.zeros_like(m)
        q_prev = torch.zeros_like(m)
        
        # 3. The Booth Iteration
        for _ in range(bits):
            last_bit_q = q & 1
            
            # Decision Logic
            sub_mask = (last_bit_q == 1) & (q_prev == 0)
            add_mask = (last_bit_q == 0) & (q_prev == 1)
            
            a[sub_mask] = (a[sub_mask] - m[sub_mask]) & mask
            a[add_mask] = (a[add_mask] + m[add_mask]) & mask
            
            # Arithmetic Right Shift
            q_prev = q & 1
            q = (q >> 1) | ((a & 1) << (bits - 1))
            a = (a >> 1) | (a & (1 << (bits - 1))) 
            
        result = (a << bits) | q
        
        # Handle signed output
        is_neg = (result & (1 << (2 * bits - 1))) != 0
        result = result.to(torch.float32)
        result[is_neg] -= (1 << (2 * bits))
        
        return result

    @staticmethod
    def backward(ctx, grad_output):
        # 4. The "Straight-Through" magic
        # We return the gradient as if we did: output = input * weight
        input, weight = ctx.saved_tensors
        grad_input = grad_output * weight
        grad_weight = grad_output * input
        return grad_input, grad_weight, None

class BoothLinear(nn.Module):
    def __init__(self, in_features, out_features, bits=8):
        super().__init__()
        self.bits = bits
        self.weight = nn.Parameter(torch.randn(out_features, in_features))
        
    def forward(self, x):
        # Apply the Booth Function across the layer
        return BoothFunction.apply(x, self.weight, self.bits)
