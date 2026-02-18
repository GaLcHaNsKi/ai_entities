#!/bin/bash
# Quick GPU training launcher
# Использование: bash train_gpu.sh [agent] [steps]
# Примеры:
#   bash train_gpu.sh herbivore 200000
#   bash train_gpu.sh predator 500000
#   bash train_gpu.sh smart 1000000 --curriculum-smart

AGENT=${1:-herbivore}
STEPS=${2:-200000}
EXTRA_ARGS=${3:-}

echo "🚀 Starting GPU-optimized training..."
echo "   Agent: $AGENT"
echo "   Steps: $STEPS"
echo "   Extra: $EXTRA_ARGS"
echo ""

# Проверяем GPU
python -c "
import torch
if torch.cuda.is_available():
    print(f'✓ GPU found: {torch.cuda.get_device_name(0)}')
    print(f'  CUDA: {torch.version.cuda}')
    props = torch.cuda.get_device_properties(0)
    print(f'  Memory: {props.total_memory / 1e9:.1f} GB')
else:
    print('⚠ No GPU detected, will use CPU')
" || exit 1

echo ""
echo "Starting training..."
echo "Run: python train.py --agent $AGENT --steps $STEPS --gpu $EXTRA_ARGS"
echo ""

python train.py --agent "$AGENT" --steps "$STEPS" --gpu $EXTRA_ARGS
