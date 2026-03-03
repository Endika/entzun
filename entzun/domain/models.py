from dataclasses import dataclass


@dataclass
class SentimentPoint:
    value: int


@dataclass
class Utterance:
    text: str


@dataclass
class MeetingSummary:
    text: str


@dataclass
class MeetingAnalysis:
    sentiment_points: list[SentimentPoint]
    incremental_summaries: list[MeetingSummary]
