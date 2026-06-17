import psycopg

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "user": "apremgit",
    "password": "jarvis_secure_pass_2026",
    "dbname": "jarvis_cognitive_matrix"
}

def build_skills_matrix():
    print("🧠 Updating database with Local Skills Registry tables...")
    query = """
        CREATE TABLE IF NOT EXISTS local_executable_skills (
            id SERIAL PRIMARY KEY,
            skill_name VARCHAR(100) UNIQUE NOT NULL,
            associated_task TEXT NOT NULL,
            python_code TEXT NOT NULL,
            embedding vector(1536),
            execution_count INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_skills_hnsw_vector 
        ON local_executable_skills USING hnsw (embedding vector_cosine_ops);
    """
    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
    print("✅ Local Skills Registry is online and indexed.")

if __name__ == "__main__":
    build_skills_matrix()
