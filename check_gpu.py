#!/usr/bin/env python3
"""
GPU и CUDA diagnostics для AI Entities training
"""

import sys

def check_gpu():
    """Проверить GPU и CUDA доступность"""
    print("=" * 70)
    print("  🔍 GPU & CUDA Diagnostics")
    print("=" * 70)
    
    try:
        import torch
        print(f"\n✓ PyTorch версия: {torch.__version__}")
        
        cuda_available = torch.cuda.is_available()
        print(f"  CUDA доступен: {cuda_available}")
        
        if cuda_available:
            print(f"  CUDA версия: {torch.version.cuda}")
            print(f"  cuDNN версия: {torch.backends.cudnn.version()}")
            
            device_count = torch.cuda.device_count()
            print(f"\n  Найдено GPU: {device_count}")
            
            for i in range(device_count):
                print(f"\n  └─ GPU {i}: {torch.cuda.get_device_name(i)}")
                props = torch.cuda.get_device_properties(i)
                print(f"     Вычислительная способность: {props.major}.{props.minor}")
                print(f"     Всего памяти: {props.total_memory / 1e9:.2f} GB")
                print(f"     Max потоков на блок: {props.max_threads_per_block}")
                print(f"     Max блокой размер: {props.max_block_dim}")
            
            # Проверить текущее использование памяти
            print(f"\n  Текущее использование памяти GPU 0:")
            allocated = torch.cuda.memory_allocated(0) / 1e9
            reserved = torch.cuda.memory_reserved(0) / 1e9
            print(f"     Выделено: {allocated:.2f} GB")
            print(f"     Зарезервировано: {reserved:.2f} GB")
            
            # Подсказки для обучения
            print(f"\n  📊 Рекомендации для обучения:")
            total_mem = props.total_memory / 1e9
            if total_mem >= 16:
                print(f"     ✓ Достаточно памяти для batch_size=512+")
                print(f"     ✓ Рекомендуемая конфигурация: --batch-size 512 --n-steps 8192 --n-envs 16")
            elif total_mem >= 8:
                print(f"     ✓ Достаточно памяти для batch_size=256")
                print(f"     ✓ Рекомендуемая конфигурация: --batch-size 256 --n-steps 4096 --n-envs 12")
            else:
                print(f"     ⚠ Ограниченная память")
                print(f"     ⚠ Рекомендуемая конфигурация: --batch-size 128 --n-steps 2048 --n-envs 8")
        else:
            print(f"\n  ⚠ CUDA не доступен - будет использован CPU")
            print(f"    Для использования GPU:")
            print(f"    1. Убедитесь что GPU установлена (nvidia-smi)")
            print(f"    2. Переустановите PyTorch с CUDA поддержкой:")
            print(f"       pip install torch --index-url https://download.pytorch.org/whl/cu118")
        
        print("\n" + "=" * 70)
        print("  Training Optimization Info")
        print("=" * 70)
        
        if cuda_available:
            print("\n✅ GPU обучение доступно!")
            print("\nДля запуска обучения на GPU используйте:")
            print("  python train.py --agent herbivore --steps 200000 --gpu")
            print("\nОбщие команды:")
            print("  python train.py --agent herbivore --steps 200000 --device cuda")
            print("  python train.py --agent predator --steps 500000 --gpu")
            print("  python train.py --agent smart --steps 1000000 --gpu --curriculum-smart")
            print("\nMonirotoring во время обучения:")
            print("  watch -n 1 nvidia-smi  # Мониторить GPU")
            print("  tensorboard --logdir logs  # Смотреть метрики")
        else:
            print("\n⚠️ GPU недоступна - обучение будет на CPU")
            print("\nДля обучения на CPU используйте:")
            print("  python train.py --agent herbivore --steps 200000")
        
        print("\n" + "=" * 70)
        
        return cuda_available
        
    except ImportError:
        print("✗ PyTorch не установлена!")
        print("  Установите: pip install torch")
        return False
    except Exception as e:
        print(f"✗ Ошибка при проверке: {e}")
        return False


if __name__ == "__main__":
    cuda_ok = check_gpu()
    sys.exit(0 if cuda_ok else 1)
