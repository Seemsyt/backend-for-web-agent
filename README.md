# Web Agent Backend

Backend service for an **AI Web Agent** that generates and manages websites from natural language prompts.
The system is built using **FastAPI** and **LangGraph** to orchestrate agent workflows, tools, and code generation pipelines.

---

# Overview

The Web Agent converts user prompts into fully functional websites.
It uses a **LangGraph agent workflow** to plan, generate, edit, and build website code.

The backend exposes APIs through **FastAPI** and manages:

* Agent orchestration
* Tool execution
* Project file generation
* Code updates
* Website builds and previews

---

# Architecture

```
Frontend (Web App)
        │
        ▼
     FastAPI
        │
        ▼
   Agent Graph (LangGraph)
        │
 ┌──────┼─────────┐
 ▼      ▼         ▼
Planner  Tools   Code Generator
        │
        ▼
   Project Manager
        │
        ▼
  File System / Storage
        │
        ▼
  Build + Preview Server
```

---

# Tech Stack

**Backend Framework**

* FastAPI

**Agent Framework**

* LangGraph
* LangChain

**LLM Providers**

* OpenAI / Anthropic / Local Models

**Other Services**

* Redis (state/cache)
* PostgreSQL (projects metadata)
* Docker (sandbox builds)

---

# Project Structure

```
backend/
│
├── app/
│
│   ├── main.py
│   │
│   ├── api/
│   │   ├── routes.py
│   │   └── dependencies.py
│   │
│   ├── agents/
│   │   ├── graph.py
│   │   ├── nodes.py
│   │   ├── state.py
│   │   └── prompts.py
│   │
│   ├── tools/
│   │   ├── file_tools.py
│   │   ├── build_tools.py
│   │   └── project_tools.py
│   │
│   ├── services/
│   │   ├── project_service.py
│   │   ├── build_service.py
│   │   └── storage_service.py
│   │
│   ├── models/
│   │   └── project.py
│   │
│   ├── schemas/
│   │   └── request_schemas.py
│   │
│   ├── config/
│   │   └── settings.py
│   │
│   └── utils/
│       └── sandbox.py
│
├── tests/
│
├── requirements.txt
│
└── README.md
```

---

# LangGraph Agent Workflow

The agent workflow is implemented using **LangGraph**.

### Steps

1. User sends prompt
2. Planner decides website structure
3. Generator creates project files
4. Tools write files to project
5. Build tool compiles project
6. Preview URL returned

---

# Agent Graph

Example flow:

```
User Prompt
     │
     ▼
 Planner Node
     │
     ▼
 Code Generator Node
     │
     ▼
 File Write Tool
     │
     ▼
 Build Tool
     │
     ▼
 Result
```

---

# API Endpoints

### Generate Website

```
POST /agent/generate
```

Request

```
{
  "prompt": "Create a SaaS landing page with pricing and testimonials"
}
```

Response

```
{
  "project_id": "proj_123",
  "status": "generated"
}
```

---

### Update Website

```
POST /agent/update
```

Request

```
{
  "project_id": "proj_123",
  "prompt": "Add a blog section"
}
```

---

### Get Project

```
GET /projects/{project_id}
```

---

# Setup

### Clone Repository

```
git clone https://github.com/your-org/web-agent-backend
cd backend
```

---

### Install Dependencies

```
pip install -r requirements.txt
```

---

### Environment Variables

Create `.env`

```
OPENAI_API_KEY=
DATABASE_URL=
REDIS_URL=
PROJECT_STORAGE_PATH=
```

---

### Run Development Server

```
uvicorn app.main:app --reload
```

Server runs at:

```
http://localhost:8000
```

---

# Tool System

The agent uses tools to interact with the environment.

Examples:

* **File Tool** → create / update project files
* **Build Tool** → run build process
* **Project Tool** → manage project metadata

---

# Security

* Code execution sandbox
* Input validation
* Rate limiting
* Environment isolation

---

# Future Improvements

* Multi-agent collaboration
* Streaming agent responses
* Template learning
* Visual editing support
* Deployment integrations (Vercel, Netlify)

---

# License

MIT License
# webcoder-backend
