#!/bin/bash
# Wrapper script to run reflex with AMD GPU warnings suppressed

# Suppress AMD GPU warnings
export HIP_LOG_LEVEL=4  # Only fatal errors (0=debug, 1=info, 2=warn, 3=error, 4=fatal)
export AMD_LOG_LEVEL=4
export PYTHONWARNINGS="ignore"
export TORCH_ROCM_AOTRITON_ENABLE_EXPERIMENTAL=1

# Suppress HIP runtime logs
export ROCM_LOG_LEVEL=4
export HSA_LOG_LEVEL=4
export PAL_LOG_LEVEL=4

# Run reflex
cd "$(dirname "$0")"
exec reflex run "$@"
