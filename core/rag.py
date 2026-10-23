"""Small, workspace-local TF-IDF retrieval for uploaded college documents."""

from __future__ import annotations

from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def chunk_documents(documents: list[dict[str, Any]], size: int = 500, overlap: int = 100) -> list[dict[str, Any]]:
    """Split documents into overlapping chunks while retaining citation details."""
    if size <= overlap:
        raise ValueError("Chunk size must be larger than overlap.")
    chunks = []
    for document in documents:
        text = document.get("content", "")
        start, index = 0, 1
        while start < len(text):
            excerpt = text[start:start + size].strip()
            if excerpt:
                chunks.append({"filename": document["filename"], "chunk": index, "text": excerpt})
            start += size - overlap
            index += 1
    return chunks


def retrieve(question: str, documents: list[dict[str, Any]], limit: int = 3,
             filename: str | None = None) -> list[dict[str, Any]]:
    """Find the most relevant chunks and attach cosine similarity scores."""
    selected = [document for document in documents if not filename or document["filename"] == filename]
    chunks = chunk_documents(selected)
    if not question.strip() or not chunks:
        return []
    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vectorizer.fit_transform([item["text"] for item in chunks] + [question])
    scores = cosine_similarity(matrix[-1], matrix[:-1]).ravel()
    ranked = sorted(zip(chunks, scores), key=lambda item: item[1], reverse=True)[:limit]
    return [{**item, "score": float(score)} for item, score in ranked]
