from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import List, Dict, Optional
import pandas as pd

try:
    import ollama  # type: ignore
except Exception:  # pragma: no cover - optional dependency at runtime
    ollama = None


def llm_available() -> bool:
    return ollama is not None


def answer_question(question: str, df: pd.DataFrame, model: str | None = None) -> str:
    if ollama is None:
        return "LLM backend not installed. Please install and run Ollama, or disable chat."

    model_name = model or os.environ.get("OLLAMA_MODEL", "gemma3:4b")
    preview = df.head(10).to_string(index=False)
    schema = ", ".join([f"{c}({df[c].dtype})" for c in df.columns])
    system = (
        "You are a data analyst. Answer questions about the user's tabular data. "
        "Use only the provided schema and preview as grounding. "
        "If you are uncertain, ask for clarification."
    )
    user = (
        f"Data schema: {schema}\n\nPreview (first 10 rows):\n{preview}\n\n"
        f"Question: {question}"
    )
    try:
        response = ollama.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.get("message", {}).get("content", "")
    except Exception as exc:
        return f"LLM error: {exc}"


# ---------------------- Conversational (in-memory) chat ----------------------

@dataclass
class ChatSession:
    model: str
    messages: List[Dict[str, str]] = field(default_factory=list)


def _default_model(model: Optional[str] = None) -> str:
    return model or os.environ.get("OLLAMA_MODEL", "gemma3:4b")


def _system_prompt() -> str:
    return (
        "You are a helpful data analyst. You answer questions about a table provided by the user. "
        "Use only the provided schema and preview as grounding. If something is unclear, ask for clarification."
    )


def _context_from_df(df: pd.DataFrame) -> str:
    preview = df.head(10).to_string(index=False)
    schema = ", ".join([f"{c}({df[c].dtype})" for c in df.columns])
    return f"Data schema: {schema}\n\nPreview (first 10 rows):\n{preview}"


def start_session(df: pd.DataFrame, model: Optional[str] = None) -> ChatSession:
    model_name = _default_model(model)
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": _context_from_df(df)},
        {"role": "assistant", "content": "Saya siap membantu. Silakan ajukan pertanyaan tentang datanya."},
    ]
    return ChatSession(model=model_name, messages=messages)


def ask_with_memory(session: ChatSession, question: str) -> str:
    session.messages.append({"role": "user", "content": question})

    if ollama is None:
        offline = "LLM backend tidak tersedia. Install dan jalankan Ollama untuk menggunakan chat."
        session.messages.append({"role": "assistant", "content": offline})
        return offline

    try:
        response = ollama.chat(model=session.model, messages=session.messages)
        answer = response.get("message", {}).get("content", "")
        session.messages.append({"role": "assistant", "content": answer})
        return answer
    except Exception as exc:
        error_msg = f"LLM error: {exc}"
        session.messages.append({"role": "assistant", "content": error_msg})
        return error_msg

