# demo

A full-stack AI writer demo built with **Next.js** (frontend) and **Django** (backend).

## Tech Stack

- **Frontend:** Next.js 16, React 19, TypeScript, Tailwind CSS, Radix UI
- **Backend:** Django app modules
- **AI / Search:** OpenAI embeddings, Qdrant vector store, RAG (Retrieval-Augmented Generation)
- **Build Tool:** pnpm

## Project Structure

- `package.json`, `next.config.mjs`, `tsconfig.json`, `components.json` — Next.js frontend setup
- `models.py`, `views.py`, `urls.py`, `config.py` — Django models and routing
- `embeddings.py`, `rag.py`, `vector_store.py` — AI engine for embeddings and search
- `*.html` templates — Django UI pages

## Getting Started

### Frontend

```bash
pnpm install
pnpm dev
```

### Backend

```bash
pip install django openai qdrant-client python-dotenv
# Requires a Django project wrapper (settings.py, manage.py)
python manage.py runserver
```

## Features

- Create and manage writing projects and sources
- Ask questions over project sources using an LLM
- Audio transcription and vector search support
