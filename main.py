from fastapi import FastAPI,Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from typing import Annotated
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from models import RegisterSchema,LoginSchema,AuthUserSchema
import uuid
import os
from depedency import authenticate_user
from contextlib import asynccontextmanager
from graph import build_workflow
from database.db import get_db
from database.schema import UserSchema,ThreadShema
from hash import hash_password,verify_password,create_acces_token

workflow = None
checkpointer_gen = None
checkpointer = None
@asynccontextmanager
async def lifespan(app: FastAPI):
    # -----------------------------
    # STARTUP
    # -----------------------------
    global workflow,checkpointer,checkpointer_gen
    
    print("🚀 Starting backend...")
    print(f"✓ OPENROUTER_API_KEY: {'✓' if os.getenv('OPENROUTER_API_KEY') else '❌'}")
    print(f"✓ DATABASE URL: {'✓' if os.getenv('URL') else '❌'}")
    
    try:
        workflow, checkpointer, checkpointer_gen = await build_workflow()
        print("✅ Workflow initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize workflow: {e}")
        import traceback
        traceback.print_exc()

    app.state.workflow = workflow
    app.state.checkpointer_gen = checkpointer_gen

    yield  # 🚨 app runs here

    # -----------------------------
    # SHUTDOWN
    # -----------------------------
    print("🛑 Shutting down...")
    if app.state.checkpointer_gen:
        await app.state.checkpointer_gen.__aexit__(None, None, None)
app = FastAPI(lifespan=lifespan)
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
async def get_thread_messages(
    thread_id: str,
    user: Annotated[AuthUserSchema, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)]
):
    # 🔒 Step 1: Check ownership
    stmt = select(ThreadShema).where(
        ThreadShema.id == thread_id,
        ThreadShema.user == user.id
    )
    thread = db.execute(stmt).scalar_one_or_none()

    if not thread:
        raise HTTPException(status_code=403, detail="Unauthorized access")

    # ✅ Step 2: Get messages from workflow
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
def all_threads(
    user: Annotated[AuthUserSchema, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)]
):
    threads = []
    seen = set()

    for cp in checkpointer.list(config=None):

        thread_id = cp.config["configurable"]["thread_id"]

        if thread_id in seen:
            continue

        # 🔒 Check ownership in DB
        stmt = select(ThreadShema).where(
            ThreadShema.id == thread_id,
            ThreadShema.user == user.id
        )
        thread_obj = db.execute(stmt).scalar_one_or_none()

        if not thread_obj:
            continue  # skip чужие threads (not owned)

        seen.add(thread_id)

        channel_values = cp.checkpoint.get("channel_values", {})
        messages = channel_values.get("messages", [])

        title = "New Chat"

        for m in messages:
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

    try:
        if not workflow:
            yield f"data: ERROR: Workflow not initialized\n\n"
            return
        
        if not message or not message.strip():
            yield f"data: ERROR: Empty message\n\n"
            return

        async for event in workflow.astream_events(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            version="v1"
        ):
            event_type = event["event"]

            # ✅ stream tokens
            if event_type == "on_chat_model_stream":
                chunk = event.get("data", {}).get("chunk")

                if chunk and getattr(chunk, "content", None):
                    yield f"data: {chunk.content}\n\n"

            # ✅ structured tool events (optional but better)
            elif event_type == "on_tool_start":
                yield f"\n[TOOL START: {event['name']}]\n"

            elif event_type == "on_tool_end":
                yield f"\n[TOOL END: {event['name']}]\n"
    
    except Exception as e:
        error_msg = f"ERROR: {str(e)}"
        print(f"❌ Stream error: {error_msg}")
        import traceback
        traceback.print_exc()
        yield f"data: {error_msg}\n\n"

@app.post("/chat-stream")
async def chat_stream(
    request: ChatRequest,
    user: Annotated[AuthUserSchema, Depends(authenticate_user)],
    db: Annotated[Session, Depends(get_db)]
):
    # ✅ Step 1: Handle thread
    if request.thread_id:
        thread_id = request.thread_id

        # 🔒 Check ownership
        stmt = select(ThreadShema).where(
            ThreadShema.id == thread_id,
            ThreadShema.user == user.id
        )
        thread = db.execute(stmt).scalar_one_or_none()

        if not thread:
            raise HTTPException(status_code=403, detail="Unauthorized thread access")

    else:
        thread_id = str(uuid.uuid4())

        # ✅ Create new thread
        new_thread = ThreadShema(id=thread_id, user=user.id)
        db.add(new_thread)
        db.commit()
        db.refresh(new_thread)

    # ✅ Headers for streaming
    headers = {
        "X-Thread-Id": thread_id,
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }

    # ✅ Streaming response
    return StreamingResponse(
        stream_chat(request.message, thread_id),
        media_type="text/event-stream",
        headers=headers,
    )

@app.post("/register")
async def create_user(data:RegisterSchema,db:Annotated[Session,Depends(get_db)]):
    existing_user = db.query(UserSchema).filter(or_(UserSchema.email == data.email,UserSchema.username==data.username)).first()
    if existing_user:
        raise HTTPException(status_code=400,detail="user with these credentials already exist")

    hashed_password = hash_password(data.password)
    new_user = UserSchema(
        username = data.username,
        email = data.email,
        password = hashed_password
        )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "new user successfully added", "user_id": new_user.id}
@app.post("/login")
async def login(data:LoginSchema,db:Annotated[Session,Depends(get_db)]):
    print(f"🔑 Login attempt for: {data.email}")
    
    existing_user = db.query(UserSchema).filter(UserSchema.email == data.email).first()
    if not existing_user:
        print(f"❌ User not found: {data.email}")
        raise HTTPException(status_code=404,detail="user does not exist")
    
    if not verify_password(data.password, existing_user.password):
        print(f"❌ Invalid password for: {data.email}")
        raise HTTPException(status_code=401,detail="invalid password")
    
    print(f"✅ Password verified for user: {existing_user.username} (ID: {existing_user.id})")
    
    payload = {
        "id":existing_user.id,
        "username":existing_user.username,
        "email":existing_user.email
    }
    
    access_token = create_acces_token(payload)
    print(f"✅ Token created: {access_token[:30]}...")
    
    payload['access_token'] = access_token
    
    return JSONResponse({"message":"user logged in successfully","data":payload},status_code=200)


@app.post("/me")
def get_me(auth_user: Annotated[AuthUserSchema, Depends(authenticate_user)]):
    print(f"✅ /me endpoint: Retrieved user {auth_user.username}")
    return auth_user
