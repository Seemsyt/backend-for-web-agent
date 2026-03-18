from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage,AIMessage
import uuid
import sqlite3
from graph import workflow, checkpointer

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None

# fetch full chat messages for a thread
@app.get("/messages")
def get_thread_messages(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    state = workflow.get_state(config=config)
    messages = state.values.get("messages", [])

    result = []
    for msg in messages:
        role = getattr(msg, "type", "unknown")
        content = getattr(msg, "content", "")
        result.append({"role": role, "content": content})
    return result

# fetch all threads with first message as title
@app.get("/all/threads")
@app.get("/all/threads")
def all_threads():
    threads = []
    seen = set()

    for cp in checkpointer.list(config=None):

        thread_id = cp.config["configurable"]["thread_id"]

        if thread_id in seen:
            continue
        seen.add(thread_id)

        channel_values = cp.checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])

        title = "New Chat"

        for m in messages:
            # handle LangChain message objects safely
            msg_type = getattr(m, "type", None)
            content = getattr(m, "content", "")

            if msg_type == "human" and content:
                title = content.strip()[:80]
                break

        threads.append({
            "id": thread_id,
            "title": title
        })

    return threads

# stream chat response
def stream_chat(message: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    
    for chunk, metadata in workflow.stream(
        {"messages": [HumanMessage(content=message)]},
        config=config,
        stream_mode="messages",
    ):
        if isinstance(chunk,AIMessage):
            yield chunk.content

@app.post("/chat-stream")
def chat_stream(request: ChatRequest):
    thread_id = request.thread_id or str(uuid.uuid4())
    headers = {"X-Thread-Id": thread_id}

    return StreamingResponse(
        stream_chat(request.message, thread_id),
        media_type="text/plain",
        headers=headers,
    )