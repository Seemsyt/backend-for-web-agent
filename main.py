import os
from langgraph.checkpoint.postgres import PostgresSaver
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage,AIMessage
import uuid
import sqlite3
from graph import build_workflow
app = FastAPI()
workflow = None
checkpointer_gen = None
checkpointer = None
@app.on_event("startup")
async def startup():
    global workflow
    global checkpointer_gen
    global checkpointer
    workflow, checkpointer, checkpointer_gen = await build_workflow()



# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Thread-Id"],
)

class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None

# fetch full chat messages for a thread
@app.get("/messages")
async def get_thread_messages(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}

    state = await workflow.aget_state(config=config)
    messages = state.values.get("messages", [])

    result = []
    for msg in messages:
        role = getattr(msg, "type", "unknown")

        # ❌ skip tool messages
        if role == "tool":
            continue

        content = getattr(msg, "content", "")
        result.append({
            "role": role,
            "content": content
        })

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
async def stream_chat(message: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}

    async for event in workflow.astream_events(
        {"messages": [HumanMessage(content=message)]},
        config=config,
        version="v1"
    ):
        event_type = event.get("event")

        # ✅ stream tokens
        if event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")

            if chunk and getattr(chunk, "content", None):
                yield f"data: {chunk.content}\n\n"

        # ✅ structured tool events (optional but better)
        elif event_type == "on_tool_start":
            yield f"\n[TOOL START: {event.get('name')}]\n"

        elif event_type == "on_tool_end":
            yield f"\n[TOOL END: {event.get('name')}]\n"

@app.post("/chat-stream")
async def chat_stream(request: ChatRequest):
    thread_id = request.thread_id or str(uuid.uuid4())
    headers = {"X-Thread-Id": thread_id,
               "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",}
    print(headers)

    return StreamingResponse(
        stream_chat(request.message, thread_id),
        media_type="text/event-stream",
        headers=headers,
    )