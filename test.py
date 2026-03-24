from langchain_openai import OpenAIEmbeddings
import os
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
import os

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

embedding = client.embeddings.create(
    model="nvidia/llama-nemotron-embed-vl-1b-v2:free",
    input=[
        {
            "content": [
                {"type": "text", "text": "test query"}
            ]
        }
    ],
    encoding_format="float"
)

print(embedding.data[0].embedding[:5])