from db.session import get_db_connection

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS standards (
            id SERIAL PRIMARY KEY,
            is_number TEXT UNIQUE,
            title TEXT,
            scope_text TEXT,
            scope_embedding VECTOR(1024),
            status TEXT,
            latest_amendment TEXT,
            superseded_by TEXT,
            category TEXT,
            raw_metadata JSONB
        );
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS standard_relations (
            id SERIAL PRIMARY KEY,
            standard_id INTEGER REFERENCES standards(id),
            related_standard_id INTEGER REFERENCES standards(id),
            relation_type TEXT,
            CONSTRAINT standard_relations_uniq UNIQUE (standard_id, related_standard_id, relation_type)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS certifications (
            id SERIAL PRIMARY KEY,
            category TEXT,
            is_number TEXT,
            scheme_name TEXT,
            mandatory BOOLEAN,
            notes TEXT,
            CONSTRAINT certifications_uniq UNIQUE (category, is_number, scheme_name)
        );
    """)

    # HNSW Index for fast cosine distance search
    cur.execute("""
        CREATE INDEX IF NOT EXISTS standards_embedding_idx 
        ON standards USING hnsw (scope_embedding vector_cosine_ops) 
        WITH (m = 16, ef_construction = 64);
    """)
    
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database initialized with HNSW index and unique constraints.")

if __name__ == "__main__":
    init_db()
