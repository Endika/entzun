# Audio Transcription Project

A project to transcribe audio and generate visualizations using Whisper, ChatGPT, and D3.js.

## Architecture

The project consists of two main parts:

- **Backend**: FastAPI API that uses Whisper to transcribe audio and ChatGPT to generate reports.
- **Frontend**: React application that allows recording or uploading audio files and displays report visualizations.

## Requirements

- Python 3.12+
- Node.js 23+
- Poetry for Python dependency management
- npm for JavaScript dependency management
- Docker and Docker Compose (optional)

## Installation

### Using Make

```bash
# Install all dependencies (backend and frontend)
make install

# Install only the backend
make backend-install

# Install only the frontend
make frontend-install
```

### Manual Installation

```bash
# Backend
cd backend
poetry env remove --all
poetry config virtualenvs.in-project true
poetry install

# Frontend
cd frontend
npm install
```

## Configuration

1. Create a `.env` file in the `backend` directory based on `.env.example`:

```bash
cp backend/.env.example backend/.env
```

2. Edit the `.env` file and add your OpenAI API key:

```
OPENAI_API_KEY=your_api_key_here
```

## Execution

### Using Make

```bash
# Run the entire project (backend and frontend)
make all-run

# Run only the backend
make backend-run

# Run only the frontend
make frontend-run
```

### Manual Execution

```bash
# Backend
cd backend
poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend
npm run dev
```

### Using Docker

```bash
# Build images
make docker-build

# Start services
make docker-run

# Stop services
make docker-stop
```

## Development

### Linting and Formatting

```bash
# Run linting on the entire project
make lint

# Format the entire project
make format

# Backend only
make backend-lint
make backend-format

# Frontend only
make frontend-lint
make frontend-format
```

### Tests

```bash
# Run backend tests
make test
```

## Features

- Real-time audio transcription using Whisper
- Report generation using ChatGPT
- Data visualization with D3.js
- Audio recording and streaming
- Audio file uploads

## Backend Endpoints

- `POST /api/v1/transcription/transcribe`: Transcribes an audio file and generates a report
- `POST /api/v1/transcription/transcribe/stream`: Streaming transcription and report generation

## Access

- **Backend API**: http://localhost:8000
- **Frontend App**: http://localhost:5173 (development) or http://localhost (Docker)
