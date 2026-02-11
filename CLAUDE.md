# Brain Box – claude.md

## Role

You are an expert software engineer building a production-quality Telegram-based AI application called Brain Box.

You must strictly follow this document. Do not infer missing requirements. Do not introduce placeholders. Do not hardcode secrets.

---

## Global Rules (Strict)

* All API keys already exist in the `.env` file
* The application must load and use them directly
* DO NOT create placeholders for API keys
* DO NOT ask the user for keys
* DO NOT write secrets into code

The OPENAI_API_KEY, GITHUB_TOKEN, and GITHUB_DEFAULT_REPO are already present in `.env` and must be used as-is.

---

## Application Responsibilities

The application must:

* Connect to Telegram using TELEGRAM_BOT_TOKEN
* Restrict access using TELEGRAM_ALLOWED_USER_ID
* Receive documents, images, links, and text
* Store raw files before AI processing
* Use AI only for classification, tagging, and summarization
* Persist metadata in SQL database

---

## AI Usage Rules

AI (OpenAI) is used only for:

* Tag generation
* Short summaries
* Topic classification
* Storage suggestions

AI must never:

* Write files
* Create folders
* Modify databases directly

All AI outputs must be structured and validated by the application.

---

## Storage Instructions

* Load STORAGE_BASE_PATH from `.env`
* Ensure base directory exists at startup
* Create content-type folders if missing
* Apply hybrid structure: content type first, topic inside

File saving order:

1. Receive Telegram update
2. Validate user ID
3. Save raw file to disk
4. Extract text if applicable
5. Send text to OpenAI for analysis
6. Store metadata in SQL database
7. Respond to user

Storage must occur before AI calls.

---

## Database Instructions

* Load DATABASE_URL from `.env`
* Use SQLite for v1
* Initialize schema at startup if missing
* All metadata writes must be transactional

---

## Retrieval Logic

The system must support:

* Listing by content type
* Keyword search
* Date filtering

Telegram commands or menu actions may be used.

---

## Error Handling

* Fail loudly if required environment variables are missing
* Gracefully handle malformed files
* Reject unauthorized users explicitly

---

## Software Hygiene (Mandatory)

* Format code with black
* Lint with ruff
* Test with pytest
* Use pyproject.toml for configuration
* Add pre-commit hooks
* Include CI workflow

No exceptions.

---

## Repository Structure (Enforced)

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

---

## Roadmap Awareness

Design code so that future upgrades can include:

* PostgreSQL replacement
* Cloud storage
* Vector databases
* Web dashboard

Do not hardcode SQLite-specific logic beyond v1 abstractions.

---

## GitHub Integration

* Load GITHUB_TOKEN and GITHUB_DEFAULT_REPO from `.env`
* Use these for repository operations (backup, sync, CI)
* DO NOT hardcode GitHub credentials in code

---

## Update Instructions

You are updating an existing production-quality Telegram-based AI application called Brain Box.

You must strictly follow the existing prep.md and claude.md files.
Do not break existing functionality. Do not refactor unrelated code.
If any requirement is unclear, stop and ask. Do not guess.

---

## Environment and Secrets (STRICT – NON-NEGOTIABLE)

All required secrets and configuration values already exist in the .env file and MUST be read and used directly.

The following variables are present in .env:

* OPENAI_API_KEY
* TELEGRAM_BOT_TOKEN
* TELEGRAM_ALLOWED_USER_ID
* STORAGE_BASE_PATH
* DATABASE_URL
* ENVIRONMENT
* GITHUB_TOKEN
* GITHUB_DEFAULT_REPO

Rules:

* DO NOT create placeholders for any keys
* DO NOT hardcode secrets
* DO NOT ask the user for API keys
* The application must fail loudly if any required env variable is missing

---

## Storage Model (AUTHORITATIVE)

* Local filesystem storage is the ONLY storage backend
* All content MUST be stored locally using STORAGE_BASE_PATH
* GitHub is NOT a storage backend
* GitHub is an explicit publishing destination only
* Local storage is the system of record and must always be written to first

---

## New Feature: Decision-Aware GitHub Publishing

Extend the application to support explicit publishing of AI-restructured content to an existing GitHub repository defined by GITHUB_DEFAULT_REPO.

The repository already exists and must NOT be created by the application.

---

## GitHub Publishing Rules (STRICT)

* GitHub interaction must be handled by a dedicated GitHub Publishing Agent
* AI must NEVER interact with GitHub directly

AI responsibilities:

* Restructure content
* Convert content into clean, readable Markdown
* Suggest folder paths and filenames
* Suggest commit messages

Application responsibilities:

* Create folders
* Write files
* Commit changes
* Push to GitHub using GITHUB_TOKEN

---

## Publishing Trigger (MANDATORY SAFETY RULE)

Content must be published to GitHub ONLY when explicitly triggered.

Valid triggers:

* Telegram command `/publish`
* Message containing `#github`

Without a trigger:

* Content is stored locally only
* Nothing is pushed to GitHub

---

## GitHub Repository Structure (ENFORCED)

At the root of the repository, the application must maintain:

* pictures/
* documents/
* audios/
* links/
* notes/

Folders must be created if missing.
AI may suggest subfolders by topic or date, but top-level folders must remain stable.

---

## Processing Flow (STRICT ORDER – DO NOT CHANGE)

1. Receive Telegram message
2. Validate sender using TELEGRAM_ALLOWED_USER_ID
3. Save raw content locally using STORAGE_BASE_PATH
4. Extract text if applicable
5. Use OpenAI (via OPENAI_API_KEY) to:
   - Generate Decision Objects
   - Restructure content
   - Generate summaries and tags
   - Suggest topic, folder, filename, commit message
6. Persist Decision Objects and metadata locally (SQLite)
7. If publishing trigger exists:
   - Create folders in GitHub repo if missing
   - Write files
   - Commit with a deterministic message
   - Push to GitHub
8. Respond to user via Telegram

Raw local storage MUST happen before any AI call.

---

## Decision Support Upgrade (MANDATORY)

You must introduce Decision Objects.

Each meaningful action (e.g. publish vs store locally) must produce a structured decision record containing:

* decision_name
* context
* options
* recommendation
* rationale
* confidence
* timestamp

Claude may help generate the text, but the application must control persistence.

---

## Architecture Rules (DO NOT VIOLATE)

* Telegram = interface only
* AI = reasoning and restructuring only
* Application = storage, decisions, GitHub control
* Clean separation of concerns is mandatory

---

## Engineering Standards (MANDATORY)

* Python only
* black for formatting
* ruff for linting
* pytest for tests
* pyproject.toml for configuration
* pre-commit hooks
* CI workflow (GitHub Actions)
* SQLite must be abstracted so it can later be replaced with PostgreSQL

---

## Output Expectations

* Update the existing codebase cleanly
* Add Decision Objects and GitHub publishing without breaking current logic
* Do not introduce cloud storage or alternative backends
* Do not weaken safety rules
* Keep GitHub logic modular and optional
* If any requirement conflicts with existing code, explain the conflict and stop


