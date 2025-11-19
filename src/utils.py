# src/utils.py
"""
Вспомогательные функции для Video Intelligence System
"""
import torch
from typing import Literal


def resolve_device(device: str) -> str:
    """
    Конвертирует device параметр в реальное устройство

    Args:
        device: 'auto', 'cuda', 'cpu'

    Returns:
        'cuda' или 'cpu'

    Examples:
        >>> resolve_device('auto')
        'cuda'  # если GPU доступен
        >>> resolve_device('cpu')
        'cpu'
    """
    if device == 'auto':
        if torch.cuda.is_available():
            device = 'cuda'
            print(f"[INFO] Auto-detected device: cuda (GPU available)")
        else:
            device = 'cpu'
            print(f"[INFO] Auto-detected device: cpu (no GPU available)")

    # Валидация
    valid_devices = ['cpu', 'cuda']
    if device not in valid_devices:
        print(f"[WARN] Invalid device '{device}', falling back to 'cpu'")
        device = 'cpu'

    return device


def get_device_info() -> dict:
    """
    Получить информацию об устройстве

    Returns:
        dict с информацией о GPU/CPU
    """
    info = {
        'cuda_available': torch.cuda.is_available(),
        'device_count': 0,
        'device_name': 'CPU',
        'cuda_version': None
    }

    if torch.cuda.is_available():
        info['device_count'] = torch.cuda.device_count()
        info['device_name'] = torch.cuda.get_device_name(0)
        info['cuda_version'] = torch.version.cuda

        # Дополнительная информация о памяти
        info['total_memory_mb'] = torch.cuda.get_device_properties(0).total_memory / (1024**2)
        info['allocated_memory_mb'] = torch.cuda.memory_allocated(0) / (1024**2)

    return info


def print_device_info():
    """Вывести информацию об устройстве"""
    info = get_device_info()

    print("\n" + "=" * 60)
    print("DEVICE INFORMATION")
    print("=" * 60)

    if info['cuda_available']:
        print(f"✓ CUDA available: YES")
        print(f"  GPU count: {info['device_count']}")
        print(f"  GPU name: {info['device_name']}")
        print(f"  CUDA version: {info['cuda_version']}")
        print(f"  Total memory: {info['total_memory_mb']:.0f} MB")
        print(f"  Allocated memory: {info['allocated_memory_mb']:.0f} MB")
    else:
        print(f"✗ CUDA available: NO")
        print(f"  Using CPU only")

    print("=" * 60 + "\n")


if __name__ == "__main__":
    # Тестирование
    print("Testing device resolution:")

    print("\n1. Test 'auto':")
    result = resolve_device('auto')
    print(f"   Result: {result}")

    print("\n2. Test 'cpu':")
    result = resolve_device('cpu')
    print(f"   Result: {result}")

    print("\n3. Test 'cuda':")
    result = resolve_device('cuda')
    print(f"   Result: {result}")

    print("\n4. Test invalid 'gpu':")
    result = resolve_device('gpu')
    print(f"   Result: {result}")

    print("\n5. Device info:")
    print_device_info()
