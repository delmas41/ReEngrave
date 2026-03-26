# ReEngrave

**ReEngrave** is a full-stack music score re-engraving pipeline that combines Optical Music Recognition (Audiveris), AI vision comparison (Claude), and professional typesetting (LilyPond) with a self-improving human-in-the-loop review system.

---

## Overview

```
PDF Scan ──► Audiveris OMR ──► MusicXML ──► Claude Vision ──► Flagged Diffs
                                    │                               │
                                    │                          Human Review
                                    │                               │
                                    └────── Corrections Applied ◄──┘
                                                    │
                                             LilyPond Engrave
                                                    │
                                         Publication-quality PDF
```

The system learns from human review decisions over time, building a knowledge base of patterns and auto-accept rules that reduce manual effort on future scores.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                   Frontend                       │
│  React + Vite + TypeScript + React Query         │
│  Pages: Dashboard, IMSLP Search, Upload,         │
│         Review UI, Export                        │
└────────────────────┬────────────────────────────┘
                     │ HTTP (Axios)
┌────────────────────▼────────────────────────────┐
│                 Backend API                      │
│  FastAPI (Python 3.11) + SQLAlchemy 2.0          │
│  SQLite (aiosqlite) database                     │
│                                                  │
│  Modules:                                        │
│  ├── imslp_agent      IMSLP search/download      │
│  ├── audiveris_omr    OMR via Audiveris CLI       │
│  ├── claude_vision    Vision comparison          │
│  ├── lilypond_engrave Typesetting                │
│  ├── file_import      Upload handling            │
│  ├── export_module    Multi-format export        │
│  └── analytics        Self-improving agent       │
└──────────────────────────────────────────────────┘
         │              │              │
   Audiveris        Claude API     LilyPond
   (Java 21)     (Anthropic)      (CLI tool)
```

---

## Prerequisites

| Dependency | Version | Purpose |
|-----------|---------|---------|
| Node.js   | 20+     | Frontend build |
| Python    | 3.11+   | Backend API |
| Java      | 21+     | Audiveris OMR |
| LilyPond  | 2.24+   | Score engraving |
| Audiveris | 5.3+    | OMR engine |

---

## Local Development Setup

### 1. Clone the repository

```bash
git clone https://github.com/your-org/reengrave.git
cd reengrave
```

### 2. Backend

```bash
cd backend

# Create and activate virtual environment
python3.11 -m venv venv
source venv/bin/activate       # macOS/Linux
# venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp ../.env.example .env
# Edit .env with your ANTHROPIC_API_KEY and other settings

# Start the API server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000. Interactive docs at http://localhost:8000/docs.

### 3. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The frontend will be available at http://localhost:5173 and proxies `/api` requests to the backend.

---

## Installing Audiveris

Audiveris is the OMR engine used to convert PDF scans to MusicXML.

### Download from GitHub Releases

```bash
# Download Audiveris 5.3.1
wget https://github.com/Audiveris/audiveris/releases/download/5.3.1/Audiveris_5.3.1.zip
unzip Audiveris_5.3.1.zip -d /opt/
export AUDIVERIS_HOME=/opt/Audiveris
export PATH="$AUDIVERIS_HOME/bin:$PATH"
```

Add the `export` lines to your `~/.zshrc` or `~/.bashrc` for persistence.

### Verify installation

```bash
Audiveris -help
```

---

## Installing LilyPond

### macOS

```bash
brew install lilypond
```

Or download from https://lilypond.org/download.html and add to PATH.

### Linux / Railway (Dockerfile)

LilyPond is installed in the Dockerfile via `apt-get install lilypond`. No additional steps needed for Railway deployments.

### Verify installation

```bash
lilypond --version
musicxml2ly --version
```

---

## Environment Variables

Copy `.env.example` to `backend/.env` and fill in the values:

```bash
cp .env.example backend/.env
```

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key for Claude Vision |
| `DATABASE_URL` | SQLAlchemy async database URL (default: SQLite) |
| `UPLOAD_DIR` | Directory for uploaded files |
| `EXPORT_DIR` | Directory for exported scores |
| `AUDIVERIS_HOME` | Path to Audiveris installation |
| `VITE_API_URL` | Backend URL for frontend (used at build time) |

---

## Railway Deployment (Backend)

1. Install the Railway CLI: `npm install -g @railway/cli`
2. Link your project: `railway link`
3. Set environment variables in the Railway dashboard (Settings → Variables)
4. The Dockerfile in `backend/` will be used automatically
5. Deploy: `railway up` or push to the `main` branch (CI handles it)

Required Railway env vars:
- `ANTHROPIC_API_KEY`
- `DATABASE_URL` (Railway provides PostgreSQL – update connection string accordingly)
- `UPLOAD_DIR`, `EXPORT_DIR`

> **Note:** For production, replace SQLite with PostgreSQL. Change `DATABASE_URL` to `postgresql+asyncpg://...` and add `asyncpg` to `requirements.txt`.

---

## Vercel Deployment (Frontend)

1. Import the GitHub repo in Vercel dashboard
2. Set the **root directory** to `frontend`
3. Framework preset: **Vite**
4. Set environment variable: `VITE_API_URL=https://your-railway-app.railway.app`
5. Deploy

The CI workflow (`deploy.yml`) handles automated deployments on push to `main`.

---

## Database

SQLite is created automatically at startup. No migrations required for initial setup.

### Schema overview

| Table | Purpose |
|-------|---------|
| `scores` | Processed score metadata and file paths |
| `flagged_differences` | Per-measure differences found by Claude Vision |
| `knowledge_patterns` | Patterns derived from human review decisions |
| `auto_accept_rules` | Rules for automatically accepting known-good diffs |
| `claude_prompt_versions` | Prompt iteration history for self-improvement |
| `finetuning_dataset` | Exported image/label pairs for vision model training |

---

## Self-Improving Agent

ReEngrave learns from every human review decision:

1. **Pattern Analysis** – After each batch of reviews, `/api/analytics/update` groups accepted/rejected diffs by instrument and difference type.
2. **Knowledge Base** – Patterns are stored in `KnowledgePattern` with acceptance rates.
3. **Auto-Accept Rules** – When a pattern reaches >80% acceptance rate with >10 confirmations, an `AutoAcceptRule` is activated.
4. **Auto-Accept** – New diffs matching an active rule are auto-accepted without human review.
5. **Prompt Evolution** – Low-accuracy patterns trigger suggestions to refine the Claude Vision prompt.

---

## Fine-Tuning Dataset Export

Export accepted corrections for training a specialized vision model:

```
GET /api/analytics/finetuning-export
```

Output: `exports/finetuning/finetuning_dataset.jsonl`

Each line:
```json
{
  "image_path": "/uploads/snippet_abc123.png",
  "label": "<note><pitch>...</pitch></note>",
  "metadata": {
    "measure_number": 42,
    "instrument": "Violin I",
    "difference_type": "accidental",
    "human_decision": "edit"
  }
}
```

Split assignment: 80% train, 10% val, 10% test.

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/imslp/search?q=...` | Search IMSLP |
| POST | `/api/imslp/download` | Download and process IMSLP PDF |
| POST | `/api/import/upload` | Upload PDF scan |
| POST | `/api/import/musicxml` | Upload MusicXML |
| GET | `/api/scores` | List all scores |
| GET | `/api/scores/{id}` | Get score details |
| DELETE | `/api/scores/{id}` | Delete score |
| POST | `/api/scores/{id}/process/omr` | Run Audiveris OMR |
| POST | `/api/scores/{id}/process/compare` | Run Claude Vision comparison |
| GET | `/api/scores/{id}/status` | Get processing status |
| GET | `/api/scores/{id}/diffs` | List flagged differences |
| PATCH | `/api/diffs/{id}/decision` | Record human decision |
| POST | `/api/scores/{id}/diffs/bulk-decide` | Bulk accept/reject |
| GET | `/api/scores/{id}/export?format=pdf\|musicxml\|lilypond` | Export score |
| GET | `/api/analytics/report` | Learning report |
| GET | `/api/analytics/patterns` | Knowledge patterns |
| POST | `/api/analytics/update` | Trigger pattern analysis |
| GET | `/api/analytics/auto-rules` | Active auto-accept rules |
| GET | `/api/analytics/finetuning-export` | Export fine-tuning dataset |
| GET | `/health` | Health check |

Full interactive docs: http://localhost:8000/docs
