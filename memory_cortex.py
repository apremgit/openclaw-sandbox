from dotenv import load_dotenv
load_dotenv()  # Safely injects your hidden keys into os.environ automatically
import psycopg
import os
import sys
from typing import List, Dict, Any
from google import genai
from google.genai import types

# Local Database Connection Matrix
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "user": "apremgit",
    "password": "jarvis_secure_pass_2026",
    "dbname": "jarvis_cognitive_matrix"
}

try:
    ai_client = genai.Client()
except Exception as e:
    print(f"⚠️ Warning: Google AI Studio Client could not initialize: {e}")
    ai_client = None

def get_text_embedding(text: str) -> List[float]:
    """Generates a high-fidelity 1536-dimensional vector via gemini-embedding-2."""
    if not ai_client:
        raise ValueError("AI Client is uninitialized. Ensure GEMINI_API_KEY is exported.")
    try:
        response = ai_client.models.embed_content(
            model="gemini-embedding-2",
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=1536)
        )
        return response.embeddings[0].values
    except Exception as e:
        print(f"❌ Embedding Generation Failure: {e}", file=sys.stderr)
        raise e

def check_local_skills(task: str) -> Dict[str, Any]:
    """Scans the local HNSW layer to see if Jarvis already knows this tool offline."""
    try:
        # Enforcing Gemini 2 Asymmetric search query guidelines
        formatted_query = f"task: code retrieval | query: {task}"
        target_embedding = get_text_embedding(formatted_query)
        
        query = """
            SELECT skill_name, python_code, (embedding <=> %s::vector) as distance
            FROM local_executable_skills
            ORDER BY embedding <=> %s::vector LIMIT 1;
        """
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (target_embedding, target_embedding))
                row = cur.fetchone()
                if row and (1 - row[2]) > 0.85:
                    return {"found": True, "name": row[0], "code": row[1], "score": round(1 - row[2], 4)}
    except Exception as e:
        print(f"⚠️ Vector layer scan bypass active: {e}")
    return {"found": False}

def save_new_skill(name: str, task: str, code: str):
    """Commits a functional, sandboxed code snippet directly to long-term memory."""
    try:
        formatted_doc = f"title: {name} | text: {task}"
        embedding = get_text_embedding(formatted_doc)
        
        query = """
            INSERT INTO local_executable_skills (skill_name, associated_task, python_code, embedding)
            VALUES (%s, %s, %s, %s::vector)
            ON CONFLICT (skill_name) DO UPDATE SET python_code = EXCLUDED.python_code;
        """
        with psycopg.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (name, task, code, embedding))
        print(f"💾 Local Registry Updated: Skill '{name}' is now active completely offline.")
    except Exception as e:
        print(f"⚠️ Failed to commit local code block: {e}")
