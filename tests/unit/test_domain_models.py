from __future__ import annotations

from entzun.domain.models import MeetingAnalysis, MeetingSummary, SentimentPoint


def test_domain_models_can_be_instantiated() -> None:
    points = [SentimentPoint(value=1), SentimentPoint(value=-2)]
    summaries = [
        MeetingSummary(text="Short summary"),
        MeetingSummary(text="Another summary"),
    ]

    analysis = MeetingAnalysis(sentiment_points=points, incremental_summaries=summaries)

    assert analysis.sentiment_points == points
    assert len(analysis.incremental_summaries) == 2
    assert analysis.incremental_summaries[0].text == "Short summary"
