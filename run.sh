#!/bin/bash
# Wrapper script to run reflex with AMD GPU warnings suppressed

# Suppress AMD GPU warnings
export HIP_LOG_LEVEL=3
export AMD_LOG_LEVEL=3
export PYTHONWARNINGS="ignore::UserWarning"
export TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1

# Run reflex
cd "$(dirname "$0")"
exec reflex run "$@"
