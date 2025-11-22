#!/usr/bin/env python3
"""
Тестовый скрипт для проверки генерации вопросов
"""
import os
import sys

# Добавляем путь к src
sys.path.insert(0, os.path.dirname(__file__))

from src.llm_provider import LLMProvider, LLMConfig

def main():
    print("=" * 60)
    print("ТЕСТ ГЕНЕРАЦИИ ВОПРОСОВ")
    print("=" * 60)

    # Проверяем наличие credentials
    credentials = os.getenv("GIGACHAT_CREDENTIALS")
    if not credentials:
        print("[ERROR] GIGACHAT_CREDENTIALS не установлен!")
        print("[INFO] Установите переменную окружения:")
        print("export GIGACHAT_CREDENTIALS='your_credentials_here'")
        return

    print(f"[OK] GIGACHAT_CREDENTIALS найден (длина: {len(credentials)} символов)")

    # Инициализация LLM
    try:
        config = LLMConfig(
            provider="gigachat",
            model="GigaChat",
            temperature=0.5,
            max_tokens=2000,
            use_cache=False  # Отключаем кэш для теста
        )

        llm = LLMProvider(config)
        print("[OK] LLMProvider инициализирован")
    except Exception as e:
        print(f"[ERROR] Не удалось инициализировать LLMProvider: {e}")
        import traceback
        traceback.print_exc()
        return

    # Тестовые суммаризации
    test_summaries = [
        "В начале лекции рассматриваются основные принципы машинного обучения. Обсуждаются методы обучения с учителем и без учителя.",
        "Далее объясняется концепция нейронных сетей. Рассматривается архитектура многослойного перцептрона.",
        "В заключение обсуждаются современные методы оптимизации нейронных сетей, включая Adam и RMSprop."
    ]

    print("\n[INFO] Тестовые суммаризации:")
    for i, s in enumerate(test_summaries, 1):
        print(f"  {i}. {s[:60]}...")

    # Генерация вопросов
    print("\n" + "=" * 60)
    print("ГЕНЕРАЦИЯ ВОПРОСОВ С ОТВЕТАМИ")
    print("=" * 60)

    try:
        questions = llm.generate_questions(
            test_summaries,
            num_questions=5,
            difficulty_mix=True,
            with_answers=True
        )

        print("\n" + "=" * 60)
        print(f"РЕЗУЛЬТАТ: Получено {len(questions)} вопросов")
        print("=" * 60)

        # Проверяем вопросы
        empty_count = 0
        for i, q in enumerate(questions, 1):
            question_text = q.get('question', '')
            is_empty = not question_text or question_text.strip() == ''

            if is_empty:
                empty_count += 1
                print(f"\n[ERROR] Вопрос {i}: ПУСТОЙ!")
                print(f"  Полный объект: {q}")
            else:
                print(f"\n[OK] Вопрос {i}:")
                print(f"  Текст: {question_text}")
                print(f"  Сложность: {q.get('difficulty', 'unknown')}")
                print(f"  Есть ответ: {bool(q.get('answer'))}")
                print(f"  Есть объяснение: {bool(q.get('explanation'))}")

                if q.get('answer'):
                    print(f"  Ответ: {q['answer'][:80]}...")

        if empty_count > 0:
            print(f"\n[WARNING] Найдено {empty_count} пустых вопросов из {len(questions)}")
        else:
            print(f"\n[SUCCESS] Все {len(questions)} вопросов заполнены корректно!")

    except Exception as e:
        print(f"\n[ERROR] Ошибка при генерации вопросов: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
