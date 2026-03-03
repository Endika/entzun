from __future__ import annotations

from openai import OpenAI

from entzun.application.ports import MeetingSummarizerPort, SentimentAnalyzerPort


class OpenAISentimentAnalyzer(SentimentAnalyzerPort):
    def __init__(self, client: OpenAI, recent_context: list[str], max_context_items: int) -> None:
        self._client = client
        self._recent_context = recent_context
        self._max_context_items = max_context_items

    def analyze(self, text: str, context: list[str] | None = None) -> tuple[int, str]:
        if not text or not text.strip() or len(text.strip()) < 3:
            return 0, ""

        self._recent_context.append(text)
        if len(self._recent_context) > self._max_context_items:
            self._recent_context.pop(0)

        previous_context_str = ""
        if len(self._recent_context) > 1:
            previous_context_str = "\n\nConversation context (previous utterances):\n"
            for index, sentence in enumerate(self._recent_context[:-1], 1):
                previous_context_str += f"{index}. {sentence}\n"

        prompt = (
            "Analyse this meeting snippet: "
            f'"{text}"\n'
            f"{previous_context_str}\n"
            "Your task (strict format):\n"
            "1. Give a sentiment score from -10 (very hostile/angry) "
            "to +10 (very friendly/successful). 0 is neutral.\n"
            "2. Summarise what was said, TAKING INTO ACCOUNT the previous context.\n\n"
            "Respond ONLY in this format:\n"
            "SCORE: [Number]\n"
            "SUMMARY: [Text]"
        )

        response = self._client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content or ""

        score = 0
        summary = ""
        if "SCORE:" in content and "SUMMARY:" in content:
            parts = content.split("SUMMARY:")
            score_part = parts[0].replace("SCORE:", "").strip()
            summary = parts[1].strip()
            try:
                score = int(score_part)
            except ValueError:
                score = 0

        return score, summary


class OpenAIMeetingSummarizer(MeetingSummarizerPort):
    def __init__(self, client: OpenAI) -> None:
        self._client = client

    def summarize_full(self, transcript: str, avg_sentiment: float, num_utterances: int) -> str:
        prompt = (
            "You are an expert assistant for analysing meetings. "
            "Analyse the following FULL meeting transcript:\n\n"
            "TRANSCRIPT:\n"
            f"{transcript}\n\n"
            "ADDITIONAL DATA:\n"
            f"- Number of utterances: {num_utterances}\n"
            f"- Average sentiment: {avg_sentiment:.1f}/10\n\n"
            "Generate a professional executive summary with:\n\n"
            "1. OVERALL SUMMARY (2-3 paragraphs):\n"
            "- Main topic of the meeting\n"
            "- Key points discussed\n\n"
            "2. DECISIONS MADE:\n"
            "- List of decisions or agreements (if any)\n\n"
            "3. PENDING ACTIONS:\n"
            "- Tasks or next steps identified (if any)\n\n"
            "4. OVERALL TONE:\n"
            "- Analysis of the atmosphere of the meeting "
            "(constructive, tense, productive, etc.)\n\n"
            "5. HIGHLIGHTS:\n"
            "- 3-5 of the most important points mentioned\n\n"
            "Be concise but complete. Use a clear format with well-defined sections."
        )

        response = self._client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        return response.choices[0].message.content or ""
