# Brain Box – prep.md

## Project Overview

Brain Box is a Telegram-first, agent-driven personal knowledge and decision support system. Users send documents, images, links, and text to a Telegram bot, and the system automatically stores, organizes, summarizes, and makes the content retrievable.

The system prioritizes simplicity, reliability, and production-grade architecture while remaining extensible to enterprise and research use cases.

---

## Core Goals

* Zero-friction knowledge capture via Telegram
* Automatic organization and tagging using AI agents
* Deterministic, reliable storage controlled by the application
* Clear separation of concerns between interface, intelligence, and storage
* Production-quality software hygiene from day one

---

## Scope (v1 – MVP)

### Supported Content Types

* Documents (PDF, DOCX)
* Images
* Links
* Plain text messages

### Platform

* Telegram-only interface

### Users

* Single user (restricted by Telegram User ID)

---

## High-Level Architecture

Telegram (Interface)
→ Backend Application (Control Layer)
→ AI Agents (Reasoning Layer)
→ Storage System (Memory Layer)

Telegram is only an input/output channel.
AI agents do not store data.
The backend application fully controls persistence.

---

## Agent Responsibilities

### Telegram Ingestion Agent

* Receives messages from Telegram Bot API
* Validates sender using allowed Telegram User ID
* Detects incoming content type
* Hands off raw data to storage layer

### Data Aggregation Agent

* Extracts text from documents and links
* Normalizes content into analysis-ready form
* Prepares data for AI processing

### Organization and Recommendation Agent

* Generates tags
* Produces short summaries
* Suggests storage categories and topics
* Returns structured instructions only (no file handling)

---

## Storage Architecture (Authoritative)

### Storage Principles

* Storage is deterministic and boring by design
* AI agents suggest organization; backend enforces it
* No AI writes directly to disk or database

### File Storage (v1)

* Local file system
* Base path defined by environment variable

Folder structure (hybrid):

storage/
images/
by_topic/
documents/
by_topic/
links/
by_topic/
notes/
by_topic/

Files are first grouped by content type, then by topic.

### File Naming Convention

<timestamp>*<telegram_message_id>*<original_name>

---

## Metadata Storage

### Database Choice (v1)

* SQLite

### Metadata Database Location

* storage/metadata.db

### Core Metadata Fields

* id
* content_type
* file_path
* original_name
* telegram_message_id
* telegram_user_id
* tags
* summary
* topic
* created_at

---

## Environment Variables (Required)

The application must load all configuration from `.env`.

Required variables (names only):

* TELEGRAM_BOT_TOKEN
* TELEGRAM_ALLOWED_USER_ID
* OPENAI_API_KEY (already present in `.env`)
* STORAGE_BASE_PATH
* DATABASE_URL
* ENVIRONMENT

No secrets or placeholders may be hardcoded.

---

## Retrieval Capabilities (v1)

* Show all documents
* Show all images
* Show all links
* Show all notes
* Keyword search
* Date-based filtering

---

## Non-Negotiable Engineering Standards

These rules are mandatory:

* No hardcoded secrets
* All keys loaded from `.env`
* Clear repository structure
* Code formatting with black
* Linting with ruff
* Testing with pytest
* pyproject.toml-based configuration
* Pre-commit hooks
* CI workflow (GitHub Actions)

---

## Repository Structure (Required)

brain_box/
app/
telegram/
agents/
storage/
database/
config/
tests/
scripts/
prep.md
claude.md
pyproject.toml
.gitignore

---

## Roadmap

### v1 (Current)

* Telegram ingestion
* Local storage
* SQLite metadata
* AI tagging and summaries

### v2 (Planned)

* PostgreSQL migration
* Cloud object storage
* Vector search for semantic retrieval
* Web dashboard
* Advanced multi-agent orchestration
* Analytics and usage insights


