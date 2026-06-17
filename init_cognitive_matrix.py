import psycopg
import sys
import time

# Core Connection configuration matrix
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "user": "apremgit",
    "password": "jarvis_secure_pass_2026",
    "dbname": "jarvis_cognitive_matrix"
}

def initialize_brain():
    print("🧠 Connecting to the sandboxed database cluster...")
    try:
        # Establish connection to the local Postgres container
        with psycopg.connect(**DB_CONFIG, autocommit=True) as conn:
            with conn.cursor() as cur:
                # 1. Activate the open-source pgvector extension
                print("⚡ Activating the pgvector engine extension...")
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # 2. Build the primary Capability Blueprint table
                print("📋 Creating 'capability_blueprints' table layout...")
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS capability_blueprints (
                        id SERIAL PRIMARY KEY,
                        task_category VARCHAR(100) NOT NULL,
                        intent_description TEXT NOT NULL,
                        abstract_rules TEXT NOT NULL,
                        embedding vector(1536),
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # 3. Apply the High-Performance HNSW Graph Index for 15-millisecond lookups
                print("🚀 Constructing HNSW express graph index matrix...")
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS idx_blueprints_hnsw_vector 
                    ON capability_blueprints 
                    USING hnsw (embedding vector_cosine_ops);
                """)
                
                print("\n✅ Jarvis Core Brain Setup Successfully Initialized!")
                print("Memory rows are open and ready for vector injection.")
                
    except Exception as e:
        print(f"\n❌ Error during database initialization: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    initialize_brain()
