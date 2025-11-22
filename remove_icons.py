#!/usr/bin/env python3
"""
Утилита для удаления иконок Bootstrap Icons из card-header и других элементов
"""
import re
from pathlib import Path

def remove_icons_from_file(file_path):
    """Удаляет иконки из HTML файла"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Удаляем иконки из card-headers (например: <i class="bi bi-stars"></i> Текст)
    # Заменяем на просто: Текст
    content = re.sub(
        r'(<div class="card-header"[^>]*>)\s*<i class="bi bi-[^"]+"></i>\s+',
        r'\1\n                ',
        content
    )

    # Удаляем иконки из заголовков h5 (например: <h5><i class="bi bi-journal-text"></i> Текст:</h5>)
    content = re.sub(
        r'(<h[1-6][^>]*>)\s*<i class="bi bi-[^"]+"></i>\s+',
        r'\1',
        content
    )

    # Удаляем иконки из list-item (галочки)
    content = re.sub(
        r'<i class="bi bi-check2-circle[^"]*"></i>\s+',
        '',
        content
    )

    # Удаляем иконки из alert
    content = re.sub(
        r'(<div class="alert[^>]*>)\s*<i class="bi bi-exclamation-triangle"></i>\s+',
        r'\1\n            ',
        content
    )

    # Удаляем иконки из сегментов
    content = re.sub(
        r'(<i class="bi bi-bookmark"></i>\s+)',
        '',
        content
    )

    # Сохраняем
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Обработан: {file_path}")

if __name__ == '__main__':
    # Обрабатываем session.html
    session_file = Path('templates/session.html')
    if session_file.exists():
        remove_icons_from_file(session_file)

    print("Готово!")
