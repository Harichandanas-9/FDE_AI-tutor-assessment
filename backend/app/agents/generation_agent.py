"""
Generation Agent
================
Generates educational responses using retrieved context.
Implements:
- Context-aware answer generation
- Source-grounded responses
- Streaming support
- Different modes (explain, summarize, answer, notes)
"""

import time
from typing import Any, AsyncGenerator, Dict, List

from app.agents.base_agent import BaseAgent
from app.utils.helpers import build_topic_suggestions, format_sources
from app.utils.logger import get_logger

logger = get_logger("agents.generation")

GENERATION_SYSTEM_PROMPT = """You are an expert AI educational tutor specializing in clear, accurate explanations.

Your responses must:
1. Be grounded in the provided context/sources
2. Use clear, accessible language appropriate for the student's level
3. Include concrete examples where helpful
4. Structure responses logically (concept → explanation → example → summary)
5. Cite sources when referencing specific information
6. Acknowledge uncertainty when information is not in the context
7. Never fabricate facts or statistics

Format guidelines:
- Use markdown for structure (headers, bold, code blocks for programming)
- Keep explanations concise but complete
- End with a brief summary for complex topics
"""

SUMMARIZE_PROMPT = """You are an expert at summarizing educational content.
Create a clear, structured summary of the provided document/content.
Include: key concepts, main points, important definitions, and takeaways.
Format with headers and bullet points for easy reading."""

EXPLAIN_PROMPT = """You are an expert educator. Explain the given concept clearly and thoroughly.
Start with a simple definition, then build complexity.
Use analogies, examples, and visual descriptions.
Tailor the explanation to the student's level."""

NOTES_PROMPT = """You are an expert at creating educational notes.
Create well-structured study notes from the provided content.
Include: key terms, important concepts, formulas/rules, examples, and summary points.
Format as structured markdown notes."""


class GenerationAgent(BaseAgent):
    """
    Generation Agent — produces educational responses grounded in retrieved context.
    """

    def __init__(self):
        super().__init__(name="GenerationAgent")

    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate an answer based on query and retrieved documents.

        State keys consumed: query, intent, retrieved_documents, estimated_difficulty
        State keys produced: generated_answer, draft_answer, follow_up_topics
        """
        query = state.get("query", "")
        session_id = state.get("session_id", "")
        intent = state.get("intent", "answer")
        documents = state.get("retrieved_documents", [])
        difficulty = state.get("estimated_difficulty", "intermediate")
        memory_context = state.get("memory_context", "")

        self.logger.log_start(query, session_id)
        self._add_trace(state, "generation_start", {
            "intent": intent,
            "num_docs": len(documents),
            "difficulty": difficulty,
        })

        start = time.perf_counter()

        try:
            # Build context from retrieved documents
            context = self._build_context(documents)

            # Select system prompt based on intent
            system_prompt = self._get_system_prompt(intent, difficulty)

            # Build user message
            user_message = self._build_user_message(query, context, intent, memory_context)

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ]

            # Generate response
            answer = await self.call_llm(messages, temperature=0.4)

            latency_ms = (time.perf_counter() - start) * 1000

            # Build follow-up topic suggestions
            follow_ups = build_topic_suggestions(query, context)

            state["generated_answer"] = answer
            state["draft_answer"] = answer  # Draft = pre-reflection answer
            state["follow_up_topics"] = follow_ups

            self.logger.log_complete(
                f"Generated {len(answer)} chars | intent={intent}",
                latency_ms=latency_ms,
            )
            self._add_trace(state, "generation_complete", {
                "answer_len": len(answer),
                "latency_ms": round(latency_ms, 1),
                "follow_ups": follow_ups,
            })

        except Exception as e:
            self.logger.log_error(f"Generation failed: {e}", exc_info=True)
            state["generated_answer"] = (
                "I encountered an error while generating a response. "
                "Please try again or rephrase your question."
            )
            state["draft_answer"] = state["generated_answer"]
            state["follow_up_topics"] = []
            self._add_trace(state, "generation_error", {"error": str(e)})

        return state

    def _build_context(self, documents: List[Dict[str, Any]]) -> str:
        """Format retrieved documents into an LLM-readable context block."""
        if not documents:
            return "No specific source material available. Answer from general knowledge."

        context_parts = []
        for i, doc in enumerate(documents[:5], 1):
            content = doc.get("content", "").strip()
            source = doc.get("metadata", {}).get("source", "Document")
            page = doc.get("metadata", {}).get("page", "")
            ref = f" (Page {page})" if page else ""
            context_parts.append(f"[Context {i} — {source}{ref}]:\n{content}")

        return "\n\n".join(context_parts)

    def _get_system_prompt(self, intent: str, difficulty: str) -> str:
        """Select appropriate system prompt based on intent."""
        prompts = {
            "summarize": SUMMARIZE_PROMPT,
            "explain": EXPLAIN_PROMPT,
            "notes": NOTES_PROMPT,
        }
        base = prompts.get(intent, GENERATION_SYSTEM_PROMPT)
        level_note = f"\n\nTailor your response for a {difficulty} level student."
        return base + level_note

    def _build_user_message(
        self,
        query: str,
        context: str,
        intent: str,
        memory_context: str = "",
    ) -> str:
        """Construct the full user message for the LLM."""
        parts = []

        if memory_context:
            parts.append(f"Previous conversation context:\n{memory_context}\n")

        if context and context != "No specific source material available. Answer from general knowledge.":
            parts.append(f"Relevant source material:\n{context}\n")

        action_map = {
            "summarize": "Please summarize the following content:",
            "explain": "Please explain:",
            "notes": "Please create study notes for:",
            "answer": "Please answer:",
        }
        action = action_map.get(intent, "Please respond to:")
        parts.append(f"{action}\n{query}")

        if context and "No specific" not in context:
            parts.append(
                "\nIMPORTANT: Base your response on the provided source material. "
                "Cite sources when referencing specific information."
            )

        return "\n\n".join(parts)

    async def generate_streaming(
        self, state: Dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response (for real-time frontend display).

        Yields:
            Text chunks as they are generated
        """
        query = state.get("query", "")
        documents = state.get("retrieved_documents", [])
        intent = state.get("intent", "answer")
        difficulty = state.get("estimated_difficulty", "intermediate")

        context = self._build_context(documents)
        system_prompt = self._get_system_prompt(intent, difficulty)
        user_message = self._build_user_message(query, context, intent)

        try:
            stream = await self.openai_client.chat.completions.create(
                model=self.llm.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.4,
                max_tokens=2048,
                stream=True,
            )

            async for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content

        except Exception as e:
            self.logger.log_error(f"Streaming generation failed: {e}")
            yield "Error: Could not generate streaming response."
