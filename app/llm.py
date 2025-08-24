from __future__ import annotations

import os
import re
import logging
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import OrderedDict
import pandas as pd

try:
    import ollama  # type: ignore
except Exception:  # pragma: no cover - optional dependency at runtime
    ollama = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration for tag cleaning
CLEAN_REASONING_TAGS = os.environ.get("CLEAN_REASONING_TAGS", "true").lower() == "true"
AGGRESSIVE_CLEANING = os.environ.get("AGGRESSIVE_CLEANING", "true").lower() == "true"

# Configuration for streaming
ENABLE_STREAMING = os.environ.get("ENABLE_STREAMING", "true").lower() == "true"
STREAMING_CHUNK_SIZE = int(os.environ.get("STREAMING_CHUNK_SIZE", "50"))  # Characters per update

# Configuration for optimization
ENABLE_OPTIMIZATION = os.environ.get("ENABLE_OPTIMIZATION", "true").lower() == "true"
MAX_CONTEXT_LENGTH = int(os.environ.get("MAX_CONTEXT_LENGTH", "2000"))  # Max context characters
MAX_RESPONSE_LENGTH = int(os.environ.get("MAX_RESPONSE_LENGTH", "1000"))  # Max response characters
ENABLE_CACHING = os.environ.get("ENABLE_CACHING", "true").lower() == "true"
CACHE_SIZE = int(os.environ.get("CACHE_SIZE", "100"))  # Number of cached responses
ENABLE_PARALLEL = os.environ.get("ENABLE_PARALLEL", "false").lower() == "true"  # Parallel processing


class ResponseCache:
    """Smart cache for LLM responses to improve response time"""
    
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.cache: OrderedDict = OrderedDict()
        self.hit_count = 0
        self.miss_count = 0
    
    def _generate_key(self, question: str, context_hash: str) -> str:
        """Generate cache key from question and context"""
        combined = f"{question}:{context_hash}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def get(self, question: str, context_hash: str) -> Optional[str]:
        """Get cached response if available"""
        key = self._generate_key(question, context_hash)
        if key in self.cache:
            # Move to end (most recently used)
            response = self.cache.pop(key)
            self.cache[key] = response
            self.hit_count += 1
            logger.info(f"Cache HIT for question: {question[:50]}...")
            return response
        
        self.miss_count += 1
        logger.info(f"Cache MISS for question: {question[:50]}...")
        return None
    
    def put(self, question: str, context_hash: str, response: str):
        """Cache a new response"""
        key = self._generate_key(question, context_hash)
        
        # Remove oldest if cache is full
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)
        
        self.cache[key] = response
        logger.info(f"Cached response for question: {question[:50]}...")
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        total = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total * 100) if total > 0 else 0
        
        return {
            "cache_size": len(self.cache),
            "max_size": self.max_size,
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": round(hit_rate, 2)
        }


# Global cache instance
response_cache = ResponseCache(CACHE_SIZE) if ENABLE_CACHING else None


def clean_reasoning_tags(text: str, aggressive: bool = True) -> str:
    """
    Clean reasoning tags from DeepSeek R1:8B and similar models that output internal reasoning.
    Removes <think>...</think> tags and similar reasoning patterns.
    
    Args:
        text: The raw text from the LLM
        aggressive: If True, also removes incomplete tags and cleans up formatting
    """
    if not text:
        return text
    
    # Store original for logging
    original_text = text
    
    # Remove complete reasoning tags and their content
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<reasoning>.*?</reasoning>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<analysis>.*?</analysis>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<thought>.*?</thought>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<step>.*?</step>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<process>.*?</process>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<plan>.*?</plan>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<approach>.*?</approach>', '', text, flags=re.DOTALL | re.IGNORECASE)
    
    if aggressive:
        # Remove incomplete reasoning tags (those without closing tags)
        text = re.sub(r'<think>.*', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<reasoning>.*', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<analysis>.*', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<thought>.*', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<step>.*', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<process>.*', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<plan>.*', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<approach>.*', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove any remaining angle brackets that might be left
        text = re.sub(r'<[^>]*$', '', text)  # Remove incomplete tags at end
        
        # Clean up excessive whitespace and newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)  # Remove excessive newlines
        text = re.sub(r'^\s*\n+', '', text)  # Remove leading newlines
        text = re.sub(r'\n+\s*$', '', text)  # Remove trailing newlines
        
        # Clean up multiple spaces
        text = re.sub(r' +', ' ', text)
    
    # Log if significant cleaning occurred
    if len(original_text) != len(text):
        logger.debug(f"Cleaned text from {len(original_text)} to {len(text)} characters")
    
    return text.strip()


def test_tag_cleaning():
    """
    Test function to verify tag cleaning works correctly.
    Useful for debugging and development.
    """
    test_cases = [
        # Test case 1: Complete think tags
        (
            "<think>This is my reasoning</think>Here is the answer",
            "Here is the answer"
        ),
        # Test case 2: Incomplete think tags
        (
            "<think>This is incomplete reasoning",
            ""
        ),
        # Test case 3: Mixed content
        (
            "Start<think>Reasoning here</think>Middle<reasoning>More reasoning</reasoning>End",
            "StartMiddleEnd"
        ),
        # Test case 4: No tags
        (
            "This is normal text without any tags",
            "This is normal text without any tags"
        ),
        # Test case 5: DeepSeek R1:8B style output
        (
            "<think> Hmm, user is asking for daily expenditure analysis and savings suggestions based on the provided data schema and dataset preview. I see they've given a table with 27 rows of transaction data including tanggal (date), deskripsi (description), total (amount), kategori (category), and pembayaran (payment method).</think>Berikut adalah analisis pengeluaran harian berdasarkan data yang diberikan dan beberapa saran untuk menghemat 10-20% pengeluaran di minggu depan:",
            "Berikut adalah analisis pengeluaran harian berdasarkan data yang diberikan dan beberapa saran untuk menghemat 10-20% pengeluaran di minggu depan:"
        )
    ]
    
    print("Testing tag cleaning functionality:")
    print("=" * 50)
    
    for i, (input_text, expected) in enumerate(test_cases, 1):
        result = clean_reasoning_tags(input_text)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        print(f"Test {i}: {status}")
        print(f"Input: {repr(input_text)}")
        print(f"Expected: {repr(expected)}")
        print(f"Got: {repr(result)}")
        print("-" * 30)
    
    print("Tag cleaning test completed!")


def llm_available() -> bool:
    return ollama is not None


def answer_question(question: str, df: pd.DataFrame, model: str | None = None) -> str:
    if ollama is None:
        return "LLM backend not installed. Please install and run Ollama, or disable chat."

    model_name = model or os.environ.get("OLLAMA_MODEL", "gemma3:4b")
    
    # Use the same improved context formatting
    context = _context_from_df(df)
    
    system = (
        "You are an expert financial data analyst. Your role is to analyze the provided financial transaction data "
        "and provide detailed insights, analysis, and recommendations based on the data schema and complete dataset "
        "that will be shared with you.\n\n"
        "IMPORTANT: You have access to the complete dataset with all transaction records. Use this data to:\n"
        "1. Analyze spending patterns and trends\n"
        "2. Identify areas for potential savings\n"
        "3. Provide actionable financial advice\n"
        "4. Answer specific questions about the data\n\n"
        "Always base your analysis on the actual data provided. If you need more information, ask for clarification. "
        "Provide specific numbers, percentages, and concrete examples from the data when possible."
    )
    
    user = f"{context}\n\nQuestion: {question}"
    
    try:
        response = ollama.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        raw_content = response.get("message", {}).get("content", "")
        
        # Clean reasoning tags if enabled
        if CLEAN_REASONING_TAGS:
            original_length = len(raw_content)
            cleaned_content = clean_reasoning_tags(raw_content, aggressive=AGGRESSIVE_CLEANING)
            final_length = len(cleaned_content)
            
            if original_length != final_length:
                logger.info(f"Cleaned reasoning tags: {original_length} -> {final_length} characters")
                if "<think>" in raw_content.lower() or "<reasoning>" in raw_content.lower():
                    logger.info("Detected reasoning tags in response")
            
            return cleaned_content
        else:
            return raw_content
            
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
        "You are an expert financial data analyst. Your role is to analyze the provided financial transaction data "
        "and provide detailed insights, analysis, and recommendations based on the data schema and complete dataset "
        "that will be shared with you.\n\n"
        "IMPORTANT: You have access to the complete dataset with all transaction records. Use this data to:\n"
        "1. Analyze spending patterns and trends\n"
        "2. Identify areas for potential savings\n"
        "3. Provide actionable financial advice\n"
        "4. Answer specific questions about the data\n\n"
        "Always base your analysis on the actual data provided. If you need more information, ask for clarification. "
        "Provide specific numbers, percentages, and concrete examples from the data when possible."
    )


def _context_from_df(df: pd.DataFrame) -> str:
    """
    Create a well-formatted context string from the DataFrame for the LLM to understand.
    This includes schema, summary statistics, and a clean table format.
    """
    # Get schema information
    schema = ", ".join([f"{c}({df[c].dtype})" for c in df.columns])
    total_rows = len(df)
    
    # Get summary statistics
    if "total" in df.columns:
        total_spend = df["total"].sum()
        avg_spend = df["total"].mean()
        min_spend = df["total"].min()
        max_spend = df["total"].max()
        spend_summary = f"\n💰 Financial Summary:\n- Total Spending: Rp {total_spend:,.0f}\n- Average Transaction: Rp {avg_spend:,.0f}\n- Min Transaction: Rp {min_spend:,.0f}\n- Max Transaction: Rp {max_spend:,.0f}"
    else:
        spend_summary = ""
    
    # Get category summary if available
    if "kategori" in df.columns:
        category_counts = df["kategori"].value_counts()
        category_summary = f"\n📊 Category Distribution:\n" + "\n".join([f"- {cat}: {count} transactions" for cat, count in category_counts.items()])
    else:
        category_summary = ""
    
    # Get date range if available
    if "tanggal" in df.columns and df["tanggal"].notna().any():
        date_range = df["tanggal"].dropna()
        if len(date_range) > 0:
            start_date = date_range.min()
            end_date = date_range.max()
            date_summary = f"\n📅 Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
        else:
            date_summary = ""
    else:
        date_summary = ""
    
    # Format the data table in a clean way
    # Create a copy for formatting
    df_formatted = df.copy()
    
    # Format tanggal column to be more readable
    if "tanggal" in df_formatted.columns:
        df_formatted["tanggal"] = df_formatted["tanggal"].dt.strftime("%Y-%m-%d")
    
    # Format total column with currency
    if "total" in df_formatted.columns:
        df_formatted["total"] = df_formatted["total"].apply(lambda x: f"Rp {x:,}")
    
    # Use better pandas formatting
    pd.set_option('display.max_columns', None)
    pd.set_option('display.max_colwidth', 40)
    pd.set_option('display.width', None)
    
    formatted_data = df_formatted.to_string(index=False, justify='left')
    
    # Reset pandas options
    pd.reset_option('display.max_columns')
    pd.reset_option('display.max_colwidth')
    pd.reset_option('display.width')
    
    # Create the context string
    context = f"""Data schema: {schema}

📈 Dataset Overview:
- Total Records: {total_rows} rows
- Columns: {', '.join(df.columns.tolist())}{spend_summary}{category_summary}{date_summary}

📋 Complete Dataset ({total_rows} rows):
{formatted_data}

Please analyze this data and provide insights based on the user's questions. Use the schema and data above as your reference."""
    
    return context


def debug_context(df: pd.DataFrame) -> str:
    """
    Debug function to show what context is being sent to the model.
    Useful for troubleshooting and ensuring data is properly formatted.
    """
    context = _context_from_df(df)
    
    print("=" * 80)
    print("DEBUG: Context being sent to LLM")
    print("=" * 80)
    print(context)
    print("=" * 80)
    print(f"Context length: {len(context)} characters")
    print(f"DataFrame shape: {df.shape}")
    print(f"DataFrame columns: {df.columns.tolist()}")
    print(f"DataFrame dtypes: {df.dtypes.to_dict()}")
    print("=" * 80)
    
    return context


def start_session(df: pd.DataFrame, model: Optional[str] = None) -> ChatSession:
    model_name = _default_model(model)
    
    # Log session creation
    logger.info(f"Starting new chat session with model: {model_name}")
    logger.info(f"DataFrame shape: {df.shape}")
    logger.info(f"DataFrame columns: {df.columns.tolist()}")
    
    # Create context (will be optimized when questions are asked)
    context = _context_from_df(df)
    logger.info(f"Context length: {len(context)} characters")
    
    messages: List[Dict[str, str]] = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": context},
        {"role": "assistant", "content": "Saya siap membantu. Silakan ajukan pertanyaan tentang datanya."},
    ]
    
    logger.info(f"Chat session initialized with {len(messages)} initial messages")
    return ChatSession(model=model_name, messages=messages)


def get_cache_stats() -> Dict[str, int]:
    """Get cache statistics for monitoring"""
    if response_cache:
        return response_cache.get_stats()
    return {"cache_enabled": False}


def clear_cache():
    """Clear the response cache"""
    if response_cache:
        response_cache.cache.clear()
        response_cache.hit_count = 0
        response_cache.miss_count = 0
        logger.info("Response cache cleared")
        return True
    return False


def ask_with_memory_streaming(session: ChatSession, question: str, stream_callback=None):
    """
    Streaming version of ask_with_memory that provides real-time updates with optimization.
    
    Args:
        session: Chat session
        question: User question
        stream_callback: Optional callback function to handle streaming updates
    """
    session.messages.append({"role": "user", "content": question})
    
    logger.info(f"User question: {question[:100]}...")
    logger.info(f"Session has {len(session.messages)} messages")

    if ollama is None:
        offline = "LLM backend tidak tersedia. Install dan jalankan Ollama untuk menggunakan chat."
        session.messages.append({"role": "assistant", "content": offline})
        if stream_callback:
            stream_callback(offline, is_complete=True)
        return offline

    # Check if streaming is enabled
    if not ENABLE_STREAMING:
        logger.info("Streaming disabled, using non-streaming fallback")
        return ask_with_memory(session, question)

    try:
        # Check cache first if enabled
        if ENABLE_CACHING and response_cache:
            # Get the DataFrame from session context
            df = None
            for msg in session.messages:
                if msg["role"] == "user" and "Data schema:" in msg["content"]:
                    # Extract DataFrame info from context
                    df = pd.DataFrame()  # Placeholder, we'll use context hash
                    break
            
            if df is not None:
                # Generate context hash for caching
                context_hash = hashlib.md5(str(session.messages[1]["content"]).encode()).hexdigest()
                cached_response = response_cache.get(question, context_hash)
                
                if cached_response:
                    logger.info("Using cached response")
                    session.messages.append({"role": "assistant", "content": cached_response})
                    if stream_callback:
                        # Simulate streaming for cached response
                        stream_callback(cached_response, is_complete=True)
                    return cached_response

        logger.info(f"Sending streaming request to model: {session.model}")
        
        # Use streaming API if available
        try:
            response = ollama.chat(
                model=session.model, 
                messages=session.messages,
                stream=True
            )
            
            # Handle streaming response
            full_response = ""
            buffer = ""
            
            for chunk in response:
                if 'message' in chunk and 'content' in chunk['message']:
                    content = chunk['message']['content']
                    full_response += content
                    buffer += content
                    
                    # Send updates in chunks to avoid too frequent updates
                    if len(buffer) >= STREAMING_CHUNK_SIZE and stream_callback:
                        stream_callback(buffer, is_complete=False)
                        buffer = ""
            
            # Send any remaining buffer content
            if buffer and stream_callback:
                stream_callback(buffer, is_complete=False)
            
            # Clean reasoning tags if enabled
            if CLEAN_REASONING_TAGS:
                original_length = len(full_response)
                clean_answer = clean_reasoning_tags(full_response, aggressive=AGGRESSIVE_CLEANING)
                final_length = len(clean_answer)
                
                if original_length != final_length:
                    logger.info(f"Cleaned reasoning tags in streaming chat: {original_length} -> {final_length} characters")
                    if "<think>" in full_response.lower() or "<reasoning>" in full_response.lower():
                        logger.info("Detected reasoning tags in streaming chat response")
                
                # Limit response length if optimization is enabled
                if ENABLE_OPTIMIZATION and len(clean_answer) > MAX_RESPONSE_LENGTH:
                    clean_answer = clean_answer[:MAX_RESPONSE_LENGTH] + "..."
                    logger.info(f"Response truncated to {MAX_RESPONSE_LENGTH} characters")
                
                session.messages.append({"role": "assistant", "content": clean_answer})
                
                # Cache the response if caching is enabled
                if ENABLE_CACHING and response_cache:
                    context_hash = hashlib.md5(str(session.messages[1]["content"]).encode()).hexdigest()
                    response_cache.put(question, context_hash, clean_answer)
                
                # Call callback with final cleaned content
                if stream_callback:
                    stream_callback(clean_answer, is_complete=True)
                
                return clean_answer
            else:
                # Limit response length if optimization is enabled
                if ENABLE_OPTIMIZATION and len(full_response) > MAX_RESPONSE_LENGTH:
                    full_response = full_response[:MAX_RESPONSE_LENGTH] + "..."
                    logger.info(f"Response truncated to {MAX_RESPONSE_LENGTH} characters")
                
                session.messages.append({"role": "assistant", "content": full_response})
                
                # Cache the response if caching is enabled
                if ENABLE_CACHING and response_cache:
                    context_hash = hashlib.md5(str(session.messages[1]["content"]).encode()).hexdigest()
                    response_cache.put(question, context_hash, full_response)
                
                # Call callback with final content
                if stream_callback:
                    stream_callback(full_response, is_complete=True)
                
                return full_response
                
        except Exception as stream_error:
            logger.warning(f"Streaming failed, falling back to non-streaming: {stream_error}")
            
            # Fallback to non-streaming
            return ask_with_memory(session, question)
            
    except Exception as exc:
        error_msg = f"LLM error: {exc}"
        logger.error(f"Error in ask_with_memory_streaming: {exc}")
        session.messages.append({"role": "assistant", "content": error_msg})
        return error_msg


def ask_with_memory(session: ChatSession, question: str) -> str:
    """
    Non-streaming version for backward compatibility.
    """
    session.messages.append({"role": "user", "content": question})
    
    logger.info(f"User question: {question[:100]}...")
    logger.info(f"Session has {len(session.messages)} messages")

    if ollama is None:
        offline = "LLM backend tidak tersedia. Install dan jalankan Ollama untuk menggunakan chat."
        session.messages.append({"role": "assistant", "content": offline})
        return offline

    try:
        logger.info(f"Sending request to model: {session.model}")
        response = ollama.chat(model=session.model, messages=session.messages)
        raw_answer = response.get("message", {}).get("content", "")
        
        logger.info(f"Raw response length: {len(raw_answer)} characters")
        
        # Clean reasoning tags if enabled
        if CLEAN_REASONING_TAGS:
            original_length = len(raw_answer)
            clean_answer = clean_reasoning_tags(raw_answer, aggressive=AGGRESSIVE_CLEANING)
            final_length = len(clean_answer)
            
            if original_length != final_length:
                logger.info(f"Cleaned reasoning tags in chat: {original_length} -> {final_length} characters")
                if "<think>" in raw_answer.lower() or "<reasoning>" in raw_answer.lower():
                    logger.info("Detected reasoning tags in chat response")
            
            session.messages.append({"role": "assistant", "content": clean_answer})
            return clean_answer
        else:
            session.messages.append({"role": "assistant", "content": raw_answer})
            return raw_answer
            
    except Exception as exc:
        error_msg = f"LLM error: {exc}"
        logger.error(f"Error in ask_with_memory: {exc}")
        session.messages.append({"role": "assistant", "content": error_msg})
        return error_msg


def optimize_context(df: pd.DataFrame, question: str) -> Tuple[str, str]:
    """
    Optimize context based on the question to reduce size while maintaining accuracy.
    
    Args:
        df: DataFrame with transaction data
        question: User question to determine what data is relevant
    
    Returns:
        Tuple of (optimized_context, context_hash)
    """
    if not ENABLE_OPTIMIZATION:
        return _context_from_df(df), hashlib.md5(str(df.shape).encode()).hexdigest()
    
    # Analyze question to determine relevant data
    question_lower = question.lower()
    
    # Determine what data is needed based on question
    needs_financial_summary = any(word in question_lower for word in ['total', 'spending', 'expense', 'cost', 'budget', 'hemat', 'boros'])
    needs_category_analysis = any(word in question_lower for word in ['kategori', 'category', 'makan', 'belanja', 'transportasi', 'hiburan'])
    needs_date_analysis = any(word in question_lower for word in ['tanggal', 'date', 'hari', 'minggu', 'bulan', 'trend', 'pattern'])
    needs_payment_analysis = any(word in question_lower for word in ['pembayaran', 'payment', 'jago', 'cash', 'method'])
    
    # Create optimized context
    schema = ", ".join([f"{c}({df[c].dtype})" for c in df.columns])
    total_rows = len(df)
    
    context_parts = [f"Data schema: {schema}"]
    context_parts.append(f"📈 Dataset Overview: {total_rows} rows")
    
    # Add financial summary if needed
    if needs_financial_summary and "total" in df.columns:
        total_spend = df["total"].sum()
        avg_spend = df["total"].mean()
        context_parts.append(f"💰 Total Spending: Rp {total_spend:,.0f}")
        context_parts.append(f"💰 Average Transaction: Rp {avg_spend:,.0f}")
    
    # Add category analysis if needed
    if needs_category_analysis and "kategori" in df.columns:
        category_counts = df["kategori"].value_counts()
        top_categories = category_counts.head(5)  # Only top 5
        context_parts.append("📊 Top Categories:")
        for cat, count in top_categories.items():
            context_parts.append(f"  - {cat}: {count} transactions")
    
    # Add date range if needed
    if needs_date_analysis and "tanggal" in df.columns and df["tanggal"].notna().any():
        date_range = df["tanggal"].dropna()
        if len(date_range) > 0:
            start_date = date_range.min()
            end_date = date_range.max()
            context_parts.append(f"📅 Date Range: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    
    # Add payment analysis if needed
    if needs_payment_analysis and "pembayaran" in df.columns:
        payment_counts = df["pembayaran"].value_counts()
        context_parts.append("💳 Payment Methods:")
        for method, count in payment_counts.items():
            context_parts.append(f"  - {method}: {count} transactions")
    
    # Add sample data (limited rows)
    if needs_financial_summary or needs_category_analysis:
        # Show only relevant columns and limited rows
        sample_df = df.head(10)  # Only first 10 rows
        if "tanggal" in sample_df.columns:
            sample_df = sample_df.copy()
            sample_df["tanggal"] = sample_df["tanggal"].dt.strftime("%Y-%m-%d")
        if "total" in sample_df.columns:
            sample_df = sample_df.copy()
            sample_df["total"] = sample_df["total"].apply(lambda x: f"Rp {x:,}")
        
        context_parts.append(f"\n📋 Sample Data (first 10 rows):")
        context_parts.append(sample_df.to_string(index=False, max_colwidth=30))
    
    # Create optimized context
    optimized_context = "\n".join(context_parts)
    
    # Generate context hash for caching
    context_hash = hashlib.md5(optimized_context.encode()).hexdigest()
    
    # Log optimization results
    original_size = len(_context_from_df(df))
    optimized_size = len(optimized_context)
    reduction = ((original_size - optimized_size) / original_size * 100) if original_size > 0 else 0
    
    logger.info(f"Context optimization: {original_size} -> {optimized_size} characters ({reduction:.1f}% reduction)")
    
    return optimized_context, context_hash


def optimize_system_prompt(question: str) -> str:
    """
    Optimize system prompt based on the question type.
    """
    if not ENABLE_OPTIMIZATION:
        return _system_prompt()
    
    question_lower = question.lower()
    
    # Determine question type
    if any(word in question_lower for word in ['hemat', 'boros', 'saving', 'budget']):
        return (
            "You are a financial advisor. Analyze spending patterns and provide specific "
            "savings recommendations. Focus on actionable advice with concrete numbers. "
            "Keep responses concise and practical."
        )
    elif any(word in question_lower for word in ['trend', 'pattern', 'analysis', 'analisis']):
        return (
            "You are a data analyst. Provide clear insights about spending trends and patterns. "
            "Use specific numbers and percentages. Focus on key findings and implications."
        )
    elif any(word in question_lower for word in ['hitung', 'calculate', 'total', 'jumlah']):
        return (
            "You are a financial calculator. Provide accurate calculations and clear explanations. "
            "Show your work and format numbers properly. Keep responses focused and precise."
        )
    else:
        return _system_prompt()

