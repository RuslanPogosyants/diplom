"""
Суммаризация сегментов транскрипции с улучшенным алгоритмом и логированием
"""
import json
import torch
from pathlib import Path
from typing import List, Dict
from transformers import T5ForConditionalGeneration, T5Tokenizer
from tqdm import tqdm

# Импорт системы логирования
from src.logger import get_logger

logger = get_logger("ai_models")


class SegmentSummarizer:
    """Суммаризация текстовых сегментов"""

    def __init__(
            self,
            model_name: str = "cointegrated/rut5-base-absum",
            device: str = "auto",
            max_input_length: int = 600,
            max_output_length: int = 150,
            cache_dir: str = "models/summarization",
            use_llm: bool = False
    ):
        """
        Args:
            model_name: название модели (rut5-base-absum, FRED-T5-large, etc.)
            device: cuda, cpu, auto
            max_input_length: максимальная длина входа в токенах
            max_output_length: максимальная длина суммаризации
            cache_dir: директория для кэширования моделей
            use_llm: использовать LLM (GigaChat) вместо T5 для суммаризации
        """
        self.use_llm = use_llm
        self.llm = None

        # Инициализация LLM если требуется
        if use_llm:
            logger.info("=" * 60)
            logger.info("ИНИЦИАЛИЗАЦИЯ LLM (GigaChat) ДЛЯ СУММАРИЗАЦИИ")
            logger.info("=" * 60)
            try:
                from src.llm_provider import LLMProvider, LLMConfig

                config = LLMConfig(
                    provider="gigachat",
                    model="GigaChat",
                    temperature=0.3,
                    max_tokens=2000,
                    use_cache=True
                )

                self.llm = LLMProvider(config)
                logger.info("✅ GigaChat успешно инициализирован!")

                # Проверка соединения
                logger.info("🔍 Проверка соединения с GigaChat API...")
                try:
                    test_response = self.llm._chat_with_cache(
                        prompt="Привет! Это тестовое сообщение.",
                        system_prompt="Ответь одним словом: 'готов'",
                        temperature=0.1
                    )
                    logger.info(f"✅ Соединение установлено! Ответ: {test_response[:50]}")
                except Exception as test_e:
                    logger.error(f"❌ Не удалось подключиться к GigaChat: {test_e}")
                    logger.warning("⚠️ Переключаюсь на локальную T5 модель...")
                    self.use_llm = False
                    self.llm = None

            except Exception as e:
                logger.error(f"❌ Ошибка инициализации GigaChat: {e}")
                logger.warning("⚠️ Переключаюсь на локальную T5 модель...")
                self.use_llm = False
                self.llm = None

        # Загрузка T5 модели (fallback или если LLM не используется)
        if not self.use_llm:
            logger.info(f"Загрузка модели суммаризации: {model_name}")

            # Определение устройства
            if device == "auto":
                self.device = "cuda" if torch.cuda.is_available() else "cpu"
            else:
                self.device = device

            logger.info(f"Использование устройства: {self.device}")

            # Загрузка модели и токенизатора
            try:
                logger.info("Загрузка токенизатора...")
                self.tokenizer = T5Tokenizer.from_pretrained(
                    model_name,
                    cache_dir=cache_dir
                )

                logger.info("Загрузка модели T5...")
                self.model = T5ForConditionalGeneration.from_pretrained(
                    model_name,
                    cache_dir=cache_dir
                ).to(self.device)

                logger.info("Модель успешно загружена")

                # Проверка VRAM
                if self.device == "cuda":
                    memory_allocated = torch.cuda.memory_allocated(0) / 1024 ** 3
                    logger.info(f"VRAM выделено: {memory_allocated:.2f} ГБ")

            except Exception as e:
                logger.error(f"Не удалось загрузить модель: {e}", exc_info=True)
                raise

            self.max_input_length = max_input_length
            self.max_output_length = max_output_length

            # Перевод модели в режим eval
            self.model.eval()
            logger.info("Модель переведена в режим eval")
        else:
            # Для LLM эти параметры не так критичны, но сохраняем для совместимости
            self.device = "llm"
            self.model = None
            self.tokenizer = None
            self.max_input_length = max_input_length
            self.max_output_length = max_output_length

    @staticmethod
    def preprocess_text(text: str) -> str:
        """
        Предобработка текста: очистка от мусора в разговорной речи

        Args:
            text: исходный текст из транскрипции

        Returns:
            Очищенный текст
        """
        import re

        # 1. Удаление звуков-заполнителей (filler sounds)
        filler_patterns = [
            r'\b(?:ммм|эээ|ааа|эмм|хмм|угу|ага)\b',  # Основные звуки
            r'\b(?:ну|вот|как бы|типа|короче|значит)\b',  # Слова-паразиты (частые)
            r'\b(?:понимаете|знаете|смотрите|слушайте)\b',  # Обращения без смысла
        ]

        for pattern in filler_patterns:
            text = re.sub(pattern, ' ', text, flags=re.IGNORECASE)

        # 2. Удаление повторяющихся слов (это это это -> это)
        text = re.sub(r'\b(\w+)( \1\b)+', r'\1', text)

        # 3. Удаление множественных знаков препинания (...... -> .)
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r',{2,}', ',', text)
        text = re.sub(r'\?{2,}', '?', text)
        text = re.sub(r'!{2,}', '!', text)

        # 4. Удаление неполных предложений (заканчивающихся на "...", но оставляем если это середина)
        text = re.sub(r'\.{3,}\s*$', '.', text)

        # 5. Очистка множественных пробелов
        text = re.sub(r'\s+', ' ', text)

        # 6. Удаление пробелов перед знаками препинания
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)

        # 7. Добавление пробела после знаков препинания (если его нет)
        text = re.sub(r'([.,!?;:])(\w)', r'\1 \2', text)

        # 8. Удаление пробелов в начале и конце
        text = text.strip()

        return text

    def summarize_text(
            self,
            text: str,
            num_beams: int = 4,
            length_penalty: float = 1.0,
            no_repeat_ngram_size: int = 3
    ) -> str:
        """
        Суммаризация одного текста

        Args:
            text: входной текст
            num_beams: количество лучей для beam search (только для T5)
            length_penalty: штраф за длину (только для T5)
            no_repeat_ngram_size: предотвращение повторов n-грамм (только для T5)

        Returns:
            Суммаризированный текст
        """
        # Если используем LLM - вызываем GigaChat
        if self.use_llm and self.llm:
            system_prompt = """Ты — эксперт по суммаризации образовательного контента.
Твоя задача — создать краткую, но информативную суммаризацию текста.

Требования:
- Объём: 2-3 предложения
- Сохрани ключевые идеи и факты
- Стиль: академический, чёткий
- Язык: русский
- Без вводных слов типа "в тексте говорится о..."
- Пиши прямо о содержании"""

            user_prompt = f"""Суммаризируй следующий текст:

{text}

Суммаризация:"""

            try:
                summary = self.llm._chat_with_cache(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.3
                )
                return summary.strip()
            except Exception as e:
                logger.error(f"Ошибка при суммаризации через GigaChat: {e}")
                # Fallback на простую стратегию
                sentences = text.split('.')
                return '. '.join(sentences[:3]).strip() + '.'

        # Иначе используем T5
        # Токенизация
        inputs = self.tokenizer(
            text,
            max_length=self.max_input_length,
            truncation=True,
            padding="max_length",
            return_tensors="pt"
        ).to(self.device)

        # Генерация
        with torch.no_grad():
            outputs = self.model.generate(
                inputs.input_ids,
                max_length=self.max_output_length,
                num_beams=num_beams,
                length_penalty=length_penalty,
                no_repeat_ngram_size=no_repeat_ngram_size,
                early_stopping=True,
                do_sample=False
            )

        # Декодирование
        summary = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return summary.strip()

    def summarize_segments(
            self,
            segments: List[Dict],
            min_text_length: int = 100,
            show_progress: bool = True
    ) -> List[Dict]:
        """
        Суммаризация списка сегментов с улучшенной обработкой ошибок

        Args:
            segments: список сегментов с полем 'text'
            min_text_length: минимальная длина текста для суммаризации
            show_progress: показывать прогресс-бар

        Returns:
            Список сегментов с добавленным полем 'summary'
        """
        logger.info(f"Начало суммаризации {len(segments)} сегментов")

        summarized_segments = []
        iterator = tqdm(segments, desc="Суммаризация") if show_progress else segments

        errors_count = 0
        skipped_count = 0

        for segment in iterator:
            text = segment["text"]
            summary = ""

            # Предобработка текста (очистка от мусора)
            try:
                text_cleaned = self.preprocess_text(text)
            except Exception as e:
                logger.warning(f"Ошибка предобработки сегмента {segment.get('id', '?')}: {e}")
                text_cleaned = text  # Fallback на оригинал

            # Пропускаем слишком короткие тексты
            if len(text_cleaned) < min_text_length:
                summary = text_cleaned if text_cleaned else text
                skipped_count += 1
                logger.debug(f"Сегмент {segment.get('id', '?')} пропущен: слишком короткий ({len(text_cleaned)} симв.)")
            else:
                try:
                    summary = self.summarize_text(text_cleaned)
                except Exception as e:
                    logger.error(f"Ошибка суммаризации сегмента {segment.get('id', '?')}: {e}")
                    errors_count += 1
                    # Fallback: первые 200 символов или весь текст
                    summary = text_cleaned[:200] + "..." if len(text_cleaned) > 200 else text_cleaned

            # Добавляем суммаризацию к сегменту
            segment_with_summary = segment.copy()
            segment_with_summary["summary"] = summary
            segment_with_summary["original_length"] = len(text)
            segment_with_summary["summary_length"] = len(summary)
            segment_with_summary["compression_ratio"] = len(text) / len(summary) if summary and len(summary) > 0 else 1.0

            summarized_segments.append(segment_with_summary)

        logger.info("Суммаризация завершена!")

        # Статистика
        total_original = sum(s["original_length"] for s in summarized_segments)
        total_summary = sum(s["summary_length"] for s in summarized_segments)
        avg_compression = total_original / total_summary if total_summary > 0 else 0

        logger.info(f"Исходный объем: {total_original} симв.")
        logger.info(f"Суммаризированный объем: {total_summary} симв.")
        logger.info(f"Коэффициент сжатия: {avg_compression:.2f}x")
        logger.info(f"Пропущено коротких сегментов: {skipped_count}")
        if errors_count > 0:
            logger.warning(f"Ошибок при суммаризации: {errors_count}")

        return summarized_segments

    def create_meta_summary(
            self,
            segment_summaries: List[str],
            max_length: int = 300
    ) -> str:
        """
        Создание мета-суммаризации (суммаризация всех суммаризаций)

        Args:
            segment_summaries: список суммаризаций сегментов
            max_length: максимальная длина мета-суммаризации

        Returns:
            Мета-суммаризация
        """
        logger.info(f"Создание мета-суммаризации из {len(segment_summaries)} суммаризаций")

        # Объединяем все суммаризации
        combined = " ".join(segment_summaries)

        # Если объединённый текст слишком длинный, разбиваем на части
        max_chunk = self.max_input_length * 4  # Примерно 2400 символов

        if len(combined) <= max_chunk:
            # Суммаризируем напрямую
            logger.debug("Прямая суммаризация (текст помещается в один chunk)")
            meta_summary = self.summarize_text(combined)
        else:
            # Разбиваем на части и суммаризируем каждую
            chunks = []
            words = combined.split()
            current_chunk = []
            current_length = 0

            for word in words:
                current_length += len(word) + 1
                if current_length > max_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = [word]
                    current_length = len(word)
                else:
                    current_chunk.append(word)

            if current_chunk:
                chunks.append(" ".join(current_chunk))

            logger.info(f"Разбито на {len(chunks)} частей для мета-суммаризации")

            # Суммаризируем каждую часть
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                logger.debug(f"Суммаризация части {i + 1}/{len(chunks)}")
                summary = self.summarize_text(chunk)
                chunk_summaries.append(summary)

            # Финальная суммаризация
            combined_summaries = " ".join(chunk_summaries)
            meta_summary = self.summarize_text(combined_summaries)

        logger.info(f"Мета-суммаризация создана ({len(meta_summary)} симв.)")
        return meta_summary

    def extract_key_points(
            self,
            segments: List[Dict],
            num_points: int = 5
    ) -> List[str]:
        """
        Извлечение ключевых тезисов из сегментов с улучшенным алгоритмом

        Использует комбинацию факторов:
        - Длина оригинального сегмента (важность)
        - Коэффициент сжатия (информационная плотность)
        - Длина суммаризации (содержательность)

        Args:
            segments: список сегментов с суммаризациями
            num_points: количество ключевых тезисов

        Returns:
            Список ключевых тезисов
        """
        logger.info(f"Извлечение {num_points} ключевых тезисов")

        # Вычисляем score для каждого сегмента
        scored_segments = []
        for seg in segments:
            original_len = seg.get("original_length", 0)
            summary_len = seg.get("summary_length", 1)
            compression_ratio = seg.get("compression_ratio", 1.0)

            # Score = взвешенная комбинация факторов
            # Длинные сегменты важнее, высокий коэффициент сжатия = больше информации
            # Длинная суммаризация = более содержательна
            score = (
                original_len * 0.4 +           # Важность сегмента
                compression_ratio * 100 * 0.3 +  # Информационная плотность
                summary_len * 0.3               # Содержательность
            )

            scored_segments.append({
                'segment': seg,
                'score': score
            })

        # Сортируем по score
        sorted_segments = sorted(
            scored_segments,
            key=lambda x: x['score'],
            reverse=True
        )

        top_scores = [f"{s['score']:.1f}" for s in sorted_segments[:3]]
        logger.debug(f"Топ-3 сегмента по score: {top_scores}")

        key_points = []
        for item in sorted_segments[:num_points]:
            seg = item['segment']
            summary = seg.get("summary", "")

            # Берём первое предложение суммаризации
            sentences = summary.split(".")
            first_sentence = sentences[0].strip() + "." if sentences else summary

            # Убираем слишком короткие тезисы
            if len(first_sentence) > 20:
                key_points.append(first_sentence)

        logger.info(f"Извлечено {len(key_points)} ключевых тезисов")

        return key_points

    def process_segments_file(
            self,
            segments_path: Path,
            output_dir: Path = None
    ) -> Dict:
        """
        Полный процесс суммаризации из файла сегментов с логированием

        Args:
            segments_path: путь к segments_semantic.json
            output_dir: директория для сохранения (по умолчанию та же)

        Returns:
            Dict с результатами суммаризации
        """
        logger.info("=" * 60)
        logger.info("НАЧАЛО ПРОЦЕССА СУММАРИЗАЦИИ")
        logger.info("=" * 60)

        # Загрузка сегментов
        logger.info(f"Загрузка сегментов из: {segments_path}")
        try:
            with open(segments_path, 'r', encoding='utf-8') as f:
                segments_data = json.load(f)

            segments = segments_data["segments"]
            logger.info(f"Загружено сегментов: {len(segments)}")
        except Exception as e:
            logger.error(f"Ошибка загрузки файла сегментов: {e}", exc_info=True)
            raise

        # Суммаризация сегментов
        summarized_segments = self.summarize_segments(segments)

        # Создание мета-суммаризации
        segment_summaries = [s["summary"] for s in summarized_segments]
        meta_summary = self.create_meta_summary(segment_summaries)

        # Извлечение ключевых тезисов
        key_points = self.extract_key_points(summarized_segments)

        # Формирование результата
        result = {
            "num_segments": len(summarized_segments),
            "meta_summary": meta_summary,
            "key_points": key_points,
            "segments": summarized_segments
        }

        # Сохранение
        if output_dir is None:
            output_dir = segments_path.parent

        self.save_summaries(result, output_dir)

        logger.info("=" * 60)
        logger.info("СУММАРИЗАЦИЯ ЗАВЕРШЕНА")
        logger.info("=" * 60)

        return result

    def save_summaries(self, summaries: Dict, output_dir: Path):
        """Сохранение суммаризаций с логированием"""
        # JSON формат
        json_path = output_dir / "summaries_per_segment.json"
        try:
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(summaries, f, ensure_ascii=False, indent=2)
            logger.info(f"Сохранено: {json_path}")
        except Exception as e:
            logger.error(f"Ошибка сохранения JSON: {e}", exc_info=True)
            raise

        # Читаемый формат
        txt_path = output_dir / "summaries_readable.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("СУММАРИЗАЦИЯ ВИДЕО\n")
            f.write(f"{'=' * 60}\n\n")

            # Мета-суммаризация
            f.write("ОБЩАЯ СУММАРИЗАЦИЯ:\n")
            f.write(f"{'-' * 60}\n")
            f.write(f"{summaries['meta_summary']}\n\n")

            # Ключевые тезисы
            f.write("КЛЮЧЕВЫЕ ТЕЗИСЫ:\n")
            f.write(f"{'-' * 60}\n")
            for i, point in enumerate(summaries['key_points'], 1):
                f.write(f"{i}. {point}\n")
            f.write(f"\n{'=' * 60}\n\n")

            # Суммаризации по сегментам
            f.write("СУММАРИЗАЦИЯ ПО СЕГМЕНТАМ:\n")
            f.write(f"{'=' * 60}\n\n")

            for seg in summaries["segments"]:
                f.write(f"Сегмент {seg['id'] + 1}\n")
                f.write(f"Время: {self._format_time(seg['start'])} - {self._format_time(seg['end'])}\n")
                f.write(f"Compression: {seg['compression_ratio']:.1f}x\n")
                f.write(f"{'-' * 60}\n")
                f.write(f"СУММАРИЗАЦИЯ:\n{seg['summary']}\n\n")
                f.write(f"ОРИГИНАЛЬНЫЙ ТЕКСТ:\n{seg['text'][:300]}...\n")
                f.write(f"\n{'=' * 60}\n\n")

        print(f"[✓] Saved: {txt_path}")

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Форматирование времени"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def main():
    """Пример использования"""
    import argparse

    parser = argparse.ArgumentParser(description="Summarize transcript segments")
    parser.add_argument("segments", help="Path to segments_semantic.json")
    parser.add_argument("--model", default="cointegrated/rut5-base-absum",
                        help="Model name")
    parser.add_argument("--device", default="auto", help="Device (cuda/cpu/auto)")
    parser.add_argument("--max-input", type=int, default=600, help="Max input length")
    parser.add_argument("--max-output", type=int, default=150, help="Max output length")

    args = parser.parse_args()

    segments_path = Path(args.segments)
    output_dir = segments_path.parent

    # Создание суммаризатора
    summarizer = SegmentSummarizer(
        model_name=args.model,
        device=args.device,
        max_input_length=args.max_input,
        max_output_length=args.max_output
    )

    # Суммаризация
    summaries = summarizer.process_segments_file(segments_path, output_dir)

    # Обновление checkpoint
    checkpoint_path = output_dir / "checkpoint.json"
    if checkpoint_path.exists():
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)

        checkpoint["stage"] = "summarization_complete"
        checkpoint["files"]["summaries_json"] = str(output_dir / "summaries_per_segment.json")
        checkpoint["files"]["summaries_txt"] = str(output_dir / "summaries_readable.txt")

        with open(checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)

    print(f"\n[SUCCESS] Summarization complete!")
    print(f"[INFO] Meta-summary: {summaries['meta_summary'][:100]}...")


if __name__ == "__main__":
    main()