# src/extract_terms.py
"""
Извлечение терминов и именованных сущностей
"""
import json
import spacy
from pathlib import Path
from typing import List, Dict, Set, Tuple
from collections import Counter
import re


class TermExtractor:
    """Извлечение терминов и NER"""

    def __init__(
            self,
            model_name: str = "ru_core_news_lg",
            use_llm: bool = True,
            llm_provider: 'LLMProvider' = None
    ):
        """
        Args:
            model_name: название SpaCy модели (для fallback)
            use_llm: использовать LLM (GigaChat) для извлечения ключевых терминов
            llm_provider: провайдер LLM (если None, создаётся автоматически)
        """
        self.use_llm = use_llm
        self.llm = llm_provider

        # Инициализация LLM
        if use_llm and llm_provider is None:
            try:
                print("[INFO] Initializing GigaChat for key term extraction...")
                from src.llm_provider import LLMProvider, LLMConfig

                config = LLMConfig(
                    provider="gigachat",
                    model="GigaChat",
                    temperature=0.3,
                    max_tokens=1000,
                    use_cache=True
                )

                self.llm = LLMProvider(config)
                print("[✓] GigaChat initialized for term extraction")
            except Exception as e:
                print(f"[WARN] Failed to initialize GigaChat: {e}")
                print("[WARN] Falling back to SpaCy-based extraction")
                self.use_llm = False
                self.llm = None

        # Загрузка SpaCy (для NER и fallback)
        print(f"[INFO] Loading SpaCy model: {model_name}")

        try:
            self.nlp = spacy.load(model_name)
            print(f"[✓] Model loaded successfully")
        except OSError:
            print(f"[✗] Model not found. Downloading...")
            import subprocess
            subprocess.run(["python", "-m", "spacy", "download", model_name])
            self.nlp = spacy.load(model_name)
            print(f"[✓] Model loaded successfully")

        # Стоп-слова для фильтрации
        self.stop_words = self.nlp.Defaults.stop_words

    def extract_entities(self, text: str) -> Dict[str, List[Dict]]:
        """
        Извлечение именованных сущностей

        Returns:
            Dict с категориями сущностей
        """
        doc = self.nlp(text)

        entities = {
            "PERSON": [],  # Персоны
            "ORG": [],  # Организации
            "LOC": [],  # Локации
            "GPE": [],  # Географические/политические сущности
            "DATE": [],  # Даты
            "MONEY": [],  # Деньги
            "PERCENT": [],  # Проценты
            "MISC": []  # Прочее
        }

        for ent in doc.ents:
            label = ent.label_
            if label in entities:
                entities[label].append({
                    "text": ent.text,
                    "label": label,
                    "start": ent.start_char,
                    "end": ent.end_char
                })
            else:
                entities["MISC"].append({
                    "text": ent.text,
                    "label": label,
                    "start": ent.start_char,
                    "end": ent.end_char
                })

        return entities

    def extract_noun_phrases(self, text: str, min_length: int = 2) -> List[str]:
        """
        Извлечение именных групп (потенциальные термины)
        """
        doc = self.nlp(text)

        noun_phrases = []
        for chunk in doc.noun_chunks:
            # Фильтруем короткие и стоп-слова
            text = chunk.text.strip()
            if len(text.split()) >= min_length and text.lower() not in self.stop_words:
                noun_phrases.append(text)

        return noun_phrases

    def extract_technical_terms(
            self,
            text: str,
            min_frequency: int = 2,
            min_word_length: int = 5
    ) -> List[Tuple[str, int]]:
        """
        Извлечение технических терминов через частотный анализ
        """
        doc = self.nlp(text)

        # Собираем существительные и прилагательные
        candidates = []
        for token in doc:
            if token.pos_ in ["NOUN", "ADJ", "PROPN"]:
                # Лемматизация
                lemma = token.lemma_.lower()
                # Фильтрация
                if (len(lemma) >= min_word_length and
                        lemma not in self.stop_words and
                        lemma.isalpha()):
                    candidates.append(lemma)

        # Подсчёт частоты
        term_freq = Counter(candidates)

        # Фильтруем по минимальной частоте
        terms = [
            (term, freq)
            for term, freq in term_freq.most_common()
            if freq >= min_frequency
        ]

        return terms

    def extract_multi_word_terms(
            self,
            text: str,
            min_frequency: int = 2
    ) -> List[Tuple[str, int]]:
        """
        Извлечение многословных терминов (биграммы, триграммы)
        """
        doc = self.nlp(text)

        # Извлечение биграмм
        bigrams = []
        tokens = [token for token in doc if token.pos_ in ["NOUN", "ADJ", "PROPN"]]

        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i].lemma_} {tokens[i + 1].lemma_}"
            bigrams.append(bigram.lower())

        # Извлечение триграмм
        trigrams = []
        for i in range(len(tokens) - 2):
            trigram = f"{tokens[i].lemma_} {tokens[i + 1].lemma_} {tokens[i + 2].lemma_}"
            trigrams.append(trigram.lower())

        # Подсчёт частоты
        all_terms = bigrams + trigrams
        term_freq = Counter(all_terms)

        # Фильтруем
        terms = [
            (term, freq)
            for term, freq in term_freq.most_common()
            if freq >= min_frequency
        ]

        return terms

    def create_glossary(
            self,
            terms: List[Tuple[str, int]],
            entities: Dict[str, List[Dict]],
            max_terms: int = 50
    ) -> Dict:
        """
        Создание глоссария терминов
        """
        print(f"[INFO] Creating glossary with up to {max_terms} terms")

        # Сортируем термины по частоте
        sorted_terms = sorted(terms, key=lambda x: x[1], reverse=True)[:max_terms]

        glossary = {
            "technical_terms": [
                {"term": term, "frequency": freq, "definition": ""}
                for term, freq in sorted_terms
            ],
            "named_entities": {
                "persons": list(set(e["text"] for e in entities.get("PERSON", []))),
                "organizations": list(set(e["text"] for e in entities.get("ORG", []))),
                "locations": list(set(e["text"] for e in entities.get("LOC", []) + entities.get("GPE", []))),
                "dates": list(set(e["text"] for e in entities.get("DATE", []))),
            }
        }

        return glossary

    def extract_key_terms_from_summaries(
            self,
            summaries: List[str],
            num_terms: int = 15
    ) -> List[Dict[str, str]]:
        """
        Извлечение ключевых терминов через LLM из суммаризаций

        Args:
            summaries: список суммаризаций сегментов
            num_terms: количество терминов

        Returns:
            Список терминов с метаданными
        """
        if not self.use_llm or not self.llm:
            print("[WARN] LLM not available, using fallback term extraction")
            # Fallback: объединяем суммаризации и используем SpaCy
            combined_text = " ".join(summaries)
            single_terms = self.extract_technical_terms(combined_text, min_frequency=1)
            return [
                {"term": term, "frequency": freq, "type": "spacy_extracted"}
                for term, freq in single_terms[:num_terms]
            ]

        # Используем LLM для извлечения терминов
        print("[INFO] Using LLM for intelligent term extraction...")
        llm_terms = self.llm.extract_key_terms(summaries, num_terms=num_terms)

        return llm_terms

    def process_summaries(
            self,
            summaries_path: Path,
            output_dir: Path = None
    ) -> Dict:
        """
        Извлечение терминов из суммаризаций (новый подход с LLM)

        Args:
            summaries_path: путь к summaries_per_segment.json
            output_dir: директория для сохранения

        Returns:
            Dict с результатами
        """
        print(f"\n{'=' * 60}")
        print("[INFO] Starting LLM-based term extraction")
        print(f"{'=' * 60}\n")

        # Загрузка суммаризаций
        with open(summaries_path, 'r', encoding='utf-8') as f:
            summaries_data = json.load(f)

        segments = summaries_data.get("segments", [])
        summaries = [seg["summary"] for seg in segments if "summary" in seg]

        print(f"[INFO] Loaded {len(summaries)} summaries")

        # Извлечение ключевых терминов через LLM
        key_terms = self.extract_key_terms_from_summaries(summaries, num_terms=20)

        print(f"[INFO] Extracted {len(key_terms)} key terms via LLM")

        # Также извлекаем NER из полного текста (для дополнительной информации)
        print("[INFO] Extracting named entities from full transcript...")
        full_text = " ".join([seg.get("text", "") for seg in segments])
        entities = self.extract_entities(full_text[:50000])  # Ограничиваем для производительности

        # Формируем глоссарий в новом формате
        glossary = {
            "key_terms": [
                {
                    "term": t["term"],
                    "frequency": 1,  # LLM не даёт частоту
                    "type": t.get("type", "general"),
                    "relevance": t.get("relevance", "medium")
                }
                for t in key_terms
            ],
            "named_entities": {
                "persons": list(set(e["text"] for e in entities.get("PERSON", []))),
                "organizations": list(set(e["text"] for e in entities.get("ORG", []))),
                "locations": list(set(e["text"] for e in entities.get("LOC", []) + entities.get("GPE", []))),
            }
        }

        # Статистика
        stats = {
            "total_key_terms": len(key_terms),
            "total_entities": sum(len(entities[k]) for k in entities),
            "extraction_method": "llm" if self.use_llm else "spacy"
        }

        result = {
            "glossary": glossary,
            "entities_detailed": entities,
            "key_terms_detailed": key_terms,
            "statistics": stats
        }

        print(f"\n[✓] LLM-based term extraction complete!")
        print(f"[INFO] Key terms extracted: {stats['total_key_terms']}")
        print(f"[INFO] Entities found: {stats['total_entities']}")

        # Сохранение
        if output_dir is None:
            output_dir = summaries_path.parent

        self.save_results(result, output_dir)

        return result

    def process_transcript(
            self,
            transcript_path: Path,
            output_dir: Path = None
    ) -> Dict:
        """
        Полный процесс извлечения терминов (старый подход SpaCy)
        """
        print(f"\n{'=' * 60}")
        print("[INFO] Starting term extraction")
        print(f"{'=' * 60}\n")

        # Загрузка транскрипции
        with open(transcript_path, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)

        full_text = transcript_data["full_text"]

        # Извлечение сущностей
        print("[INFO] Extracting named entities...")
        entities = self.extract_entities(full_text)

        # Извлечение терминов
        print("[INFO] Extracting technical terms...")
        single_terms = self.extract_technical_terms(full_text)
        multi_terms = self.extract_multi_word_terms(full_text)

        all_terms = single_terms + multi_terms

        # Создание глоссария
        glossary = self.create_glossary(all_terms, entities)

        # Статистика
        stats = {
            "total_entities": sum(len(entities[k]) for k in entities),
            "total_terms": len(all_terms),
            "unique_persons": len(glossary["named_entities"]["persons"]),
            "unique_orgs": len(glossary["named_entities"]["organizations"]),
            "unique_locations": len(glossary["named_entities"]["locations"])
        }

        result = {
            "glossary": glossary,
            "entities_detailed": entities,
            "all_terms": [{"term": t, "frequency": f} for t, f in all_terms[:100]],
            "statistics": stats
        }

        print(f"\n[✓] Term extraction complete!")
        print(f"[INFO] Entities found: {stats['total_entities']}")
        print(f"[INFO] Terms extracted: {stats['total_terms']}")

        # Сохранение
        if output_dir is None:
            output_dir = transcript_path.parent

        self.save_results(result, output_dir)

        return result

    def save_results(self, results: Dict, output_dir: Path):
        """Сохранение результатов"""

        # JSON формат
        json_path = output_dir / "terms_and_entities.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"[✓] Saved: {json_path}")

        # TXT формат (глоссарий)
        txt_path = output_dir / "glossary.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("ГЛОССАРИЙ ТЕРМИНОВ И СУЩНОСТЕЙ\n")
            f.write("=" * 70 + "\n\n")

            # Статистика (поддержка обоих форматов)
            stats = results["statistics"]
            glossary = results["glossary"]

            f.write("СТАТИСТИКА:\n")
            f.write("-" * 70 + "\n")
            f.write(f"Всего сущностей: {stats.get('total_entities', 0)}\n")

            # Поддержка обоих форматов
            if 'total_key_terms' in stats:
                # Новый формат (LLM)
                f.write(f"Всего ключевых терминов: {stats['total_key_terms']}\n")
                f.write(f"Метод извлечения: {stats.get('extraction_method', 'llm')}\n")
            elif 'total_terms' in stats:
                # Старый формат (SpaCy)
                f.write(f"Всего терминов: {stats['total_terms']}\n")
                f.write(f"Уникальных персон: {stats.get('unique_persons', 0)}\n")
                f.write(f"Уникальных организаций: {stats.get('unique_orgs', 0)}\n")
                f.write(f"Уникальных локаций: {stats.get('unique_locations', 0)}\n")

            f.write("\n")

            # Ключевые термины (новый формат LLM)
            if "key_terms" in glossary:
                f.write("КЛЮЧЕВЫЕ ТЕРМИНЫ (извлечены через GigaChat):\n")
                f.write("-" * 70 + "\n")
                for i, term_data in enumerate(glossary["key_terms"], 1):
                    term_type = term_data.get('type', 'general')
                    relevance = term_data.get('relevance', 'medium')
                    f.write(f"{i}. {term_data['term']} [{term_type.upper()}] (релевантность: {relevance})\n")
                f.write("\n")
            # Технические термины (старый формат SpaCy)
            elif "technical_terms" in glossary:
                f.write("ТЕХНИЧЕСКИЕ ТЕРМИНЫ:\n")
                f.write("-" * 70 + "\n")
                for i, term_data in enumerate(glossary["technical_terms"], 1):
                    f.write(f"{i}. {term_data['term']} (встречается {term_data['frequency']} раз)\n")
                f.write("\n")

            # Персоны
            persons = results["glossary"]["named_entities"]["persons"]
            if persons:
                f.write("ПЕРСОНЫ:\n")
                f.write("-" * 70 + "\n")
                for person in persons:
                    f.write(f"• {person}\n")
                f.write("\n")

            # Организации
            orgs = results["glossary"]["named_entities"]["organizations"]
            if orgs:
                f.write("ОРГАНИЗАЦИИ:\n")
                f.write("-" * 70 + "\n")
                for org in orgs:
                    f.write(f"• {org}\n")
                f.write("\n")

            # Локации
            locs = results["glossary"]["named_entities"]["locations"]
            if locs:
                f.write("ЛОКАЦИИ:\n")
                f.write("-" * 70 + "\n")
                for loc in locs:
                    f.write(f"• {loc}\n")
                f.write("\n")

        print(f"[✓] Saved: {txt_path}")


def main():
    """Пример использования"""
    import argparse

    parser = argparse.ArgumentParser(description="Extract terms and named entities")
    parser.add_argument("transcript", help="Path to transcript_raw.json")
    parser.add_argument("--model", default="ru_core_news_lg", help="SpaCy model")

    args = parser.parse_args()

    transcript_path = Path(args.transcript)
    output_dir = transcript_path.parent

    # Создание экстрактора
    extractor = TermExtractor(model_name=args.model)

    # Извлечение терминов
    results = extractor.process_transcript(transcript_path, output_dir)

    # Обновление checkpoint
    checkpoint_path = output_dir / "checkpoint.json"
    if checkpoint_path.exists():
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)

        checkpoint["stage"] = "term_extraction_complete"
        checkpoint["files"]["terms_json"] = str(output_dir / "terms_and_entities.json")
        checkpoint["files"]["glossary"] = str(output_dir / "glossary.txt")

        with open(checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)

    print(f"\n[SUCCESS] Term extraction complete!")


if __name__ == "__main__":
    main()