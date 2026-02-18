#!/bin/bash
# Wrapper script to run reflex with AMD GPU warnings suppressed

# Suppress AMD GPU and HIP runtime warnings
export HIP_LOG_LEVEL=4
export AMD_LOG_LEVEL=4
export ROCM_LOG_LEVEL=4
export HSA_LOG_LEVEL=4
export PAL_LOG_LEVEL=4
export PYTHONWARNINGS="ignore"

# Suppress transformers/accelerate logging
export TRANSFORMERS_VERBOSITY=error
export ACCELERATE_VERBOSITY=error

# Run reflex and filter HIP logs
cd "$(dirname "$0")"
exec .venv/bin/reflex run "$@" 2>&1 | grep -v -E "(hip_device_runtime|hipSetDevice|hipGetDevice|hipSuccess|amdgpu.ids)"
