## Entzun

Desktop assistant for meeting transcription, sentiment analysis, and summarisation using OpenAI, built with Tkinter and Python 3.14.

### Features

- Record audio from your microphone.
- Transcribe speech to text.
- Analyse sentiment over time and visualise it.
- Generate short meeting summaries and simple PDF/text reports.

### Prerequisites

- Python 3.14.
- [uv](https://docs.astral.sh/uv/) installed.
- System audio dependencies for microphone access (`PyAudio`, OS‑specific libs).
- An OpenAI API key.

### Quick start

```bash
git clone git@github.com:Endika/entzun.git
cd entzun

# Install dependencies
make dev-install

# Configure your OpenAI key, then edit .env
cp .env.example .env

# Run the app
make run
```

### Development

- **Format & lint**: `make format` and `make lint`
- **Type-check**: `make type-check`
- **Tests**: `make test`
- **Coverage (min 80% in CI)**: `make coverage`
- **Pre-commit hooks**:
  - Install once with: `make pre-commit-install`
  - On every commit:
    - `ruff`, `mypy`, `pytest`
    - Conventional Commit message validation

### Architecture (high level)

- **UI (inbound adapter)**: Tkinter app in `entzun/ui/app.py`.
- **Domain**: Core models and behaviour in `entzun/domain`.
- **Application**: Ports and use-cases in `entzun/application`.
- **Adapters (outbound)**: OpenAI client (sentiment, summaries) and transcription (Google, Whisper) in `entzun/adapters`. PDF/text reports are written by the UI.

The goal is to keep business logic independent from the UI and external services (Hexagonal Architecture + DDD + SOLID).

### CI & automation

- GitHub Actions workflow runs on pull requests:
  - `make lint`, `make type-check`
  - Tests with coverage (>= 80%)
- Dependabot:
  - Checks Python (uv) deps and GitHub Actions weekly.
  - Groups minor/patch updates, majors in separate PRs.

