import time
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
import sqlite3
from langchain_openai import ChatOpenAI,OpenAIEmbeddings
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langchain_tavily import TavilySearch
from langgraph.prebuilt import tools_condition, ToolNode
from langchain_core.tools import tool
import re
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from huggingface_hub import login

# -----------------------------
# Load ENV
# -----------------------------

load_dotenv()

# -----------------------------
# 1. LOAD BOOKS
# -----------------------------
INDEX_PATH = '../FAISS_index'
book_paths = [
    './Books/Aurélien-Géron-Hands-On-Machine-Learning-with-Scikit-Learn-Keras-and-Tensorflow_-Concepts-Tools-and-Techniques-to-Build-Intelligent-Systems-O’Reilly-Media-2019.pdf',
    './Books/mml-book.pdf'
]

def clean_text(text:str):
    text = text.replace("\n"," ")
    text = re.sub(r"-\s+",'',text)
    text = re.sub(r"\s+"," ",text)
    return text
docs = []
embeddings = FastEmbedEmbeddings()
if os.path.exists(INDEX_PATH):
    print('loading index path')
    vector_store = FAISS.load_local(
    INDEX_PATH,
    embeddings,
    allow_dangerous_deserialization=True
)
else:
    print('building index')
    for path in book_paths:
        loader = PyMuPDFLoader(path)
        loaded_docs = loader.load()

        for doc in loaded_docs:
            doc.metadata["book"] = os.path.basename(path)

        docs.extend(loaded_docs)

    # -----------------------------
    # 2. SPLIT INTO CHUNKS
    # -----------------------------
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
                )

    chunks = splitter.split_documents(docs)

    # -----------------------------
    # 3. CLEAN TEXT (IGNORE IMAGES + GARBAGE)
    # -----------------------------
    texts = []
    metadatas = []

    for doc in chunks:
        text = doc.page_content

        if not isinstance(text, str):
            continue

        text = text.strip()

    # ignore small / useless chunks
        if len(text) < 50:
            continue

    # remove weird encoding
        text = text.encode("utf-8", "ignore").decode("utf-8")

    # ignore image-related junk
        if "Figure" in text or "Fig." in text:
            continue

    # ignore garbage (low meaningful content)
        if sum(c.isalnum() for c in text) / len(text) < 0.5:
            continue

        texts.append(text)
        metadatas.append(doc.metadata)

        print(f"✅ Clean chunks: {len(texts)}")
    # -----------------------------
# 5. CREATE FAISS (BATCHED - IMPORTANT)
# -----------------------------
    BATCH_SIZE = 32   # you can increase now (local embedding)
    vector_store = None

    for i in range(0, len(texts), BATCH_SIZE):
        print(f"🚀 Embedding batch {i//BATCH_SIZE + 1}...")

        batch_texts = texts[i:i+BATCH_SIZE]
        batch_meta = metadatas[i:i+BATCH_SIZE]

        if vector_store is None:
            vector_store = FAISS.from_texts(
                batch_texts,
                embeddings,
                metadatas=batch_meta
            )
        else:
            vector_store.add_texts(
                batch_texts,
                metadatas=batch_meta
            )

    # ✅ SAVE ONLY ONCE (IMPORTANT)
    vector_store.save_local(INDEX_PATH)

    print("✅ FAISS index created & saved")

# -----------------------------
# 4. EMBEDDINGS (JINA)
# -----------------------------





# -----------------------------
# 6. RETRIEVER (FILTER BY BOOK)
def get_retreiver(book_name:str = None):
    if book_name:
        return vector_store.as_retriever(
            search_kwargs={
        "k": 4,
        "filter": {"book": book_name}  # change dynamically later
    }
                )
    return  vector_store.as_retriever(
            search_kwargs={
        "k": 4})
# -----------------------------


# -----------------------------
# 7. TEST QUERY
# -----------------------------

# -----------------------------
# Graph State
# -----------------------------

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


# -----------------------------
# Tools
# -----------------------------


    

@tool
def Rag(query: str, book: str = None):
    """RAG tool for ML & Math books"""
    retriever = get_retreiver(book)
    results = retriever.invoke(query)

    return "\n\n".join(
    f"Source: {doc.metadata.get('book')}\n{doc.page_content}"
    for doc in results
)

search_tool = TavilySearch(
    max_results=5,
    topic="general"
)


coding_llm = ChatOpenAI(
    model="stepfun/step-3.5-flash:free",
    temperature=0.2,
    streaming=True,
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    default_headers={
        "HTTP-Referer": "http://localhost",
        "X-Title": "LangGraph Coding Tool"
    }
)


@tool
def coding_agent(prompt: str) -> str:
    """
    - Use Rag tool for machine learning and math concepts from books.
- Use search tool for latest information.
- Use coding_agent for programming tasks.
    """
    response = coding_llm.invoke([HumanMessage(content=prompt)])
    return response.content


tools = [search_tool, coding_agent,Rag]


# -----------------------------
# Main Chat LLM
# -----------------------------

llm = ChatOpenAI(
    model="openrouter/hunter-alpha",
    temperature=0.7,
    streaming=True,
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    default_headers={
        "HTTP-Referer": "http://localhost",
        "X-Title": "LangGraph Chat"
    }
)

agent = llm.bind_tools(tools)


# -----------------------------
# Chat Node
# -----------------------------

def chat_node(state: ChatState):

    messages = state["messages"]

    system_prompt = SystemMessage(
        content="""
You are a helpful AI assistant.

Rules:
- Use the search tool for latest information.
- Use coding_agent for programming tasks.
- Answer normally if no tool is required.
"""
    )

    response = agent.invoke([system_prompt] + messages)

    return {
        "messages": [response]
    }


# -----------------------------
# Tool Node
# -----------------------------

tool_node = ToolNode(tools)


# -----------------------------
# SQLite Memory
# -----------------------------

conn = sqlite3.connect(
    database="chatbot.db",
    check_same_thread=False
)

checkpointer = SqliteSaver(conn=conn)


# -----------------------------
# Graph
# -----------------------------

graph = StateGraph(ChatState)

graph.add_node("chat_node", chat_node)
graph.add_node("tools", tool_node)


graph.add_edge(START, "chat_node")


graph.add_conditional_edges(
    "chat_node",
    tools_condition
)


graph.add_edge("tools", "chat_node")


# -----------------------------
# Compile Graph
# -----------------------------

workflow = graph.compile(
    checkpointer=checkpointer
)


