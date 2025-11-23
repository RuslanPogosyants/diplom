# src/search_articles.py
"""
Поиск релевантных статей и материалов
"""
import json
import time
import requests
from pathlib import Path
from typing import List, Dict
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer
import numpy as np


class ArticleSearcher:
    """Поиск релевантных статей по темам видео"""

    def __init__(
            self,
            enable_scraping: bool = True,
            rate_limit_delay: int = 2,
            max_articles: int = 10,
            use_llm: bool = True
    ):
        """
        Args:
            enable_scraping: разрешить веб-скрейпинг
            rate_limit_delay: задержка между запросами (сек)
            max_articles: максимальное количество статей
            use_llm: использовать GigaChat для генерации запросов
        """
        self.enable_scraping = enable_scraping
        self.rate_limit_delay = rate_limit_delay
        self.max_articles = max_articles
        self.use_llm = use_llm
        self.llm = None

        # Инициализация LLM для генерации запросов
        if use_llm:
            try:
                print("[INFO] Initializing GigaChat for search query generation...")
                from src.llm_provider import LLMProvider, LLMConfig

                config = LLMConfig(
                    provider="gigachat",
                    model="GigaChat",
                    temperature=0.5,
                    max_tokens=500,
                    use_cache=True
                )

                self.llm = LLMProvider(config)
                print("[✓] GigaChat initialized for search queries")
            except Exception as e:
                print(f"[WARN] Failed to initialize GigaChat: {e}")
                print("[WARN] Falling back to simple term-based search")
                self.use_llm = False

        if enable_scraping:
            print("[INFO] Web scraping enabled")
            print(f"[INFO] Rate limit: {rate_limit_delay}s between requests")
        else:
            print("[WARN] Web scraping disabled (use --enable-scraping to enable)")

        # Загрузка модели для семантического ранжирования
        print("[INFO] Loading sentence transformer for ranking...")
        self.model = SentenceTransformer(
            "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            cache_folder="models/sentence_transformers"
        )
        print("[✓] Model loaded")

    def generate_search_queries(
            self,
            terms: List[str],
            context: str = "",
            num_queries: int = 5
    ) -> List[str]:
        """
        Генерация качественных поисковых запросов через GigaChat

        Args:
            terms: список ключевых терминов из видео
            context: контекст (краткое описание темы видео)
            num_queries: количество запросов для генерации

        Returns:
            Список поисковых запросов
        """
        if not self.use_llm or not self.llm:
            # Fallback: просто используем термины
            return terms[:num_queries]

        print(f"\n[LLM] Generating {num_queries} search queries...")

        system_prompt = """Ты — эксперт по информационному поиску научных и технических материалов.
Твоя задача — сгенерировать оптимальные поисковые запросы для академических баз данных (Google Scholar, РИНЦ, Habr).

Требования к запросам:
- Формулировка должна быть точной и научной
- Использовать русские и английские термины
- Запросы должны находить РЕЛЕВАНТНЫЕ материалы, а не общую информацию
- Ориентация на обучающие и исследовательские статьи
- Избегать слишком широких или слишком узких запросов

Формат ответа:
Один запрос на строку, без нумерации"""

        terms_str = ", ".join(terms[:10])
        user_prompt = f"""На основе следующих ключевых терминов из образовательного видео создай {num_queries} поисковых запросов:

Термины: {terms_str}

{f"Контекст видео: {context}" if context else ""}

Создай запросы, которые помогут найти:
1. Научные статьи и исследования по теме
2. Технические обзоры и руководства
3. Образовательные материалы для углубленного изучения

Поисковые запросы:"""

        try:
            response = self.llm._chat_with_cache(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.5
            )

            # Парсим запросы (по одному на строку)
            queries = []
            for line in response.strip().split('\n'):
                line = line.strip()
                # Убираем нумерацию если есть
                line = line.lstrip('0123456789.-) ')
                if line and len(line) > 10:
                    queries.append(line)

            if queries:
                print(f"[LLM] ✅ Generated {len(queries)} queries:")
                for q in queries[:num_queries]:
                    print(f"  - {q}")
                return queries[:num_queries]
            else:
                print(f"[LLM] ⚠️ No queries generated, using fallback")
                return terms[:num_queries]

        except Exception as e:
            print(f"[LLM] ❌ Error generating queries: {e}")
            print(f"[LLM] Using fallback (terms as queries)")
            return terms[:num_queries]

    def search_google_scholar(
            self,
            query: str,
            num_results: int = 5
    ) -> List[Dict]:
        """
        Поиск в Google Scholar (без scraping, только через API если есть)
        Заглушка - для production нужен API ключ
        """
        print(f"[INFO] Searching Google Scholar: {query}")

        # В реальности здесь был бы вызов API
        # Например: https://serpapi.com/google-scholar-api

        # Заглушка
        return [{
            "title": f"Academic article about {query}",
            "url": "https://scholar.google.com/",
            "source": "Google Scholar",
            "snippet": f"Research on {query}...",
            "year": 2023
        }]

    def search_wikipedia(
            self,
            query: str,
            lang: str = "ru"
    ) -> List[Dict]:
        """
        Поиск в Wikipedia через API
        """
        print(f"[INFO] Searching Wikipedia: {query}")

        api_url = f"https://{lang}.wikipedia.org/w/api.php"

        # Поиск статей
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 5,
            "format": "json"
        }

        # Правильный User-Agent для Wikipedia API

        headers = {

            'User-Agent': 'VideoIntelligenceSystem/1.0 (Educational project; https://github.com/video-intelligence) Python-requests'

        }

        try:

            # Делаем запрос с правильным User-Agent

            response = requests.get(

                api_url,

                params=search_params,

                headers=headers,

                timeout=15

            )

            response.raise_for_status()

            data = response.json()

            results = []

            for item in data.get("query", {}).get("search", []):
                page_id = item["pageid"]

                title = item["title"]

                snippet = item.get("snippet", "")

                # Получаем URL страницы

                url = f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"

                results.append({

                    "title": title,

                    "url": url,

                    "source": "Wikipedia",

                    "snippet": BeautifulSoup(snippet, "html.parser").get_text(),

                    "page_id": page_id

                })

            # Увеличенная задержка для соблюдения rate limits

            time.sleep(self.rate_limit_delay + 1)

            return results



        except requests.exceptions.HTTPError as e:

            if e.response.status_code == 403:

                print(f"[WARN] Wikipedia API blocked request (403). Try again later or check User-Agent.")

            else:

                print(f"[WARN] Wikipedia search failed with HTTP {e.response.status_code}: {e}")

            return []

        except Exception as e:

            print(f"[WARN] Wikipedia search failed: {e}")

            return []

    def search_habr(
            self,
            query: str
    ) -> List[Dict]:
        """
        Поиск на Habr.com (для технических тем)
        """
        if not self.enable_scraping:
            return []

        print(f"[INFO] Searching Habr: {query}")

        search_url = f"https://habr.com/ru/search/?q={query}&target_type=posts"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            response = requests.get(search_url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            articles = soup.find_all("article", class_="tm-articles-list__item", limit=5)

            results = []
            for article in articles:
                title_elem = article.find("a", class_="tm-title__link")
                if not title_elem:
                    continue

                title = title_elem.get_text(strip=True)
                url = "https://habr.com" + title_elem["href"]

                snippet_elem = article.find("div", class_="article-formatted-body")
                snippet = snippet_elem.get_text(strip=True)[:200] if snippet_elem else ""

                results.append({
                    "title": title,
                    "url": url,
                    "source": "Habr",
                    "snippet": snippet
                })

            time.sleep(self.rate_limit_delay)
            return results

        except Exception as e:
            print(f"[WARN] Habr search failed: {e}")
            return []

    def rank_articles_by_relevance(
            self,
            articles: List[Dict],
            query_embedding: np.ndarray,
            top_k: int = None
    ) -> List[Dict]:
        """
        Ранжирование статей по семантической релевантности
        """
        if not articles:
            return []

        if top_k is None:
            top_k = len(articles)

        print(f"[INFO] Ranking {len(articles)} articles by relevance")

        # Получаем эмбеддинги для статей
        article_texts = [
            f"{art['title']} {art.get('snippet', '')}"
            for art in articles
        ]

        article_embeddings = self.model.encode(
            article_texts,
            convert_to_numpy=True,
            show_progress_bar=False
        )

        # Вычисляем косинусное сходство
        from sklearn.metrics.pairwise import cosine_similarity
        similarities = cosine_similarity(
            query_embedding.reshape(1, -1),
            article_embeddings
        )[0]

        # Добавляем скор релевантности
        for i, art in enumerate(articles):
            art["relevance_score"] = float(similarities[i])

        # Сортируем по релевантности
        ranked = sorted(articles, key=lambda x: x["relevance_score"], reverse=True)

        return ranked[:top_k]

    def search_for_topics(
            self,
            topics: List[str],
            max_articles_per_topic: int = 3
    ) -> Dict[str, List[Dict]]:
        """
        Поиск статей для списка тем
        """
        print(f"\n{'=' * 60}")
        print(f"[INFO] Searching articles for {len(topics)} topics")
        print(f"{'=' * 60}\n")

        all_results = {}

        for topic in topics:
            print(f"[INFO] Topic: {topic}")

            # Получаем эмбеддинг запроса
            query_embedding = self.model.encode(topic, convert_to_numpy=True)

            # Поиск в разных источниках
            results = []

            # Wikipedia
            wiki_results = self.search_wikipedia(topic)
            results.extend(wiki_results)

            # Habr (если включен scraping)
            if self.enable_scraping:
                habr_results = self.search_habr(topic)
                results.extend(habr_results)

            # Ранжирование
            ranked = self.rank_articles_by_relevance(
                results,
                query_embedding,
                top_k=max_articles_per_topic
            )

            all_results[topic] = ranked
            print(f"[✓] Found {len(ranked)} articles for '{topic}'")
            print()

        return all_results

    def process_terms_file(
            self,
            terms_path: Path,
            output_dir: Path = None
    ) -> Dict:
        """
        Полный процесс поиска статей с умной генерацией запросов через GigaChat
        """
        print(f"\n{'=' * 60}")
        print("[INFO] Starting article search")
        print(f"{'=' * 60}\n")

        # Загрузка терминов
        with open(terms_path, 'r', encoding='utf-8') as f:
            terms_data = json.load(f)

        # Извлекаем ключевые термины (GigaChat формат)
        glossary = terms_data.get("glossary", {})
        key_terms = glossary.get("key_terms", [])

        # Приоритет для терминов высокой релевантности
        high_relevance = [t["term"] for t in key_terms if t.get("relevance") == "high"]
        medium_relevance = [t["term"] for t in key_terms if t.get("relevance") == "medium"]
        terms_list = (high_relevance + medium_relevance)[:15]

        if not terms_list:
            print(f"[WARN] No key terms found in glossary")
            terms_list = []

        print(f"[INFO] Using {len(terms_list)} GigaChat-extracted key terms")

        # Пытаемся получить контекст из суммаризации (если есть)
        context = ""
        summary_path = terms_path.parent / "summaries_per_segment.json"
        if summary_path.exists():
            try:
                with open(summary_path, 'r', encoding='utf-8') as f:
                    summary_data = json.load(f)
                    context = summary_data.get("meta_summary", "")[:300]  # Первые 300 символов
            except:
                pass

        print(f"[INFO] Extracted {len(terms_list)} key terms")
        if context:
            print(f"[INFO] Using video context for query generation")

        # Генерация умных поисковых запросов через GigaChat
        topics = self.generate_search_queries(
            terms=terms_list,
            context=context,
            num_queries=5
        )

        print(f"\n[INFO] Search queries to use:")
        for i, topic in enumerate(topics, 1):
            print(f"  {i}. {topic}")

        # Поиск статей
        articles_by_topic = self.search_for_topics(
            topics,
            max_articles_per_topic=self.max_articles // len(topics) if topics else 1
        )

        # Объединяем все статьи
        all_articles = []
        for topic, articles in articles_by_topic.items():
            for art in articles:
                art["topic"] = topic
                all_articles.append(art)

        # Удаляем дубликаты по URL
        seen_urls = set()
        unique_articles = []
        for art in all_articles:
            if art["url"] not in seen_urls:
                seen_urls.add(art["url"])
                unique_articles.append(art)

        # Ограничиваем количество
        unique_articles = unique_articles[:self.max_articles]

        result = {
            "total_articles": len(unique_articles),
            "articles": unique_articles,
            "topics_searched": topics,
            "sources": list(set(art["source"] for art in unique_articles))
        }

        print(f"\n[✓] Article search complete!")
        print(f"[INFO] Found {len(unique_articles)} unique articles")
        print(f"[INFO] Sources: {result['sources']}")

        # Сохранение
        if output_dir is None:
            output_dir = terms_path.parent

        self.save_articles(result, output_dir)

        return result

    def save_articles(self, articles_data: Dict, output_dir: Path):
        """Сохранение результатов поиска"""

        # JSON формат
        json_path = output_dir / "related_articles.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(articles_data, f, ensure_ascii=False, indent=2)
        print(f"[✓] Saved: {json_path}")

        # TXT формат (читаемый)
        txt_path = output_dir / "articles_list.txt"
        with open(txt_path, 'w', encoding='utf-8') as f:
            f.write("=" * 70 + "\n")
            f.write("РЕКОМЕНДУЕМЫЕ СТАТЬИ И МАТЕРИАЛЫ\n")
            f.write("=" * 70 + "\n\n")

            f.write(f"Всего статей: {articles_data['total_articles']}\n")
            f.write(f"Источники: {', '.join(articles_data['sources'])}\n")
            f.write(f"Темы поиска: {', '.join(articles_data['topics_searched'])}\n\n")

            f.write("=" * 70 + "\n\n")

            # Группировка по темам
            by_topic = {}
            for art in articles_data["articles"]:
                topic = art.get("topic", "Other")
                if topic not in by_topic:
                    by_topic[topic] = []
                by_topic[topic].append(art)

            for topic, articles in by_topic.items():
                f.write(f"ТЕМА: {topic}\n")
                f.write("-" * 70 + "\n\n")

                for i, art in enumerate(articles, 1):
                    f.write(f"{i}. {art['title']}\n")
                    f.write(f"   Источник: {art['source']}\n")
                    f.write(f"   URL: {art['url']}\n")

                    if "relevance_score" in art:
                        f.write(f"   Релевантность: {art['relevance_score']:.2f}\n")

                    if art.get("snippet"):
                        f.write(f"   Описание: {art['snippet'][:150]}...\n")

                    f.write("\n")

                f.write("=" * 70 + "\n\n")

        print(f"[✓] Saved: {txt_path}")

def main():
    """Пример использования"""
    import argparse

    parser = argparse.ArgumentParser(description="Search for related articles")
    parser.add_argument("terms", help="Path to terms_and_entities.json")
    parser.add_argument("--enable-scraping", action="store_true",
                        help="Enable web scraping (be careful with rate limits)")
    parser.add_argument("--max-articles", type=int, default=10,
                        help="Maximum number of articles")
    parser.add_argument("--rate-limit", type=int, default=2,
                        help="Delay between requests (seconds)")

    args = parser.parse_args()

    terms_path = Path(args.terms)
    output_dir = terms_path.parent

    # Создание поисковика
    searcher = ArticleSearcher(
        enable_scraping=args.enable_scraping,
        rate_limit_delay=args.rate_limit,
        max_articles=args.max_articles
    )

    # Поиск статей
    articles = searcher.process_terms_file(terms_path, output_dir)

    # Обновление checkpoint
    checkpoint_path = output_dir / "checkpoint.json"
    if checkpoint_path.exists():
        with open(checkpoint_path, 'r', encoding='utf-8') as f:
            checkpoint = json.load(f)

        checkpoint["stage"] = "article_search_complete"
        checkpoint["files"]["articles_json"] = str(output_dir / "related_articles.json")
        checkpoint["files"]["articles_txt"] = str(output_dir / "articles_list.txt")

        with open(checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)

    print(f"\n[SUCCESS] Article search complete!")

    if __name__ == "__main__":
        main()