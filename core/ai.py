"""Optional Groq calls with explicit, useful rule-based fallbacks."""

from __future__ import annotations

import os

import streamlit as st


def answer_with_context(question: str, context: str, language: str = "English") -> tuple[str, bool]:
    """Answer from supplied context when Groq is configured, otherwise use the passage."""
    try:
        api_key = st.secrets["GROQ_API_KEY"]
    except KeyError:
        api_key = None
    api_key = api_key or os.getenv("GROQ_API_KEY")
    if not api_key:
        return context, False
    try:
        from groq import Groq

        model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        language_instruction = (
            "simple clear English"
            if language == "English"
            else "Hindi in Roman script mixed naturally with English, friendly and motivating, no Devanagari, keep subject names and numbers unchanged"
        )
        response = Groq(api_key=api_key, timeout=15).chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": f"Use only the supplied data and context. Never invent or alter figures, subjects, or facts. Reply in {language_instruction}."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
            ],
            temperature=0.4,
            max_tokens=1200,
        )
        return response.choices[0].message.content or context, True
    except Exception:
        return context, False
