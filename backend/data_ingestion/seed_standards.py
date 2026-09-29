import os
from sentence_transformers import SentenceTransformer
from db.session import get_db_connection
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

print("Loading embedding model (takes ~1 min on first run)...")
model = SentenceTransformer('BAAI/bge-m3')

SAMPLE_STANDARDS = [
    {
        "is_number": "IS 1786:2008",
        "title": "High Strength Deformed Steel Bars for Concrete Reinforcement",
        "scope_text": "This standard covers requirements for high strength deformed steel bars and wires for concrete reinforcement including weldable grade.",
        "status": "Live",
        "latest_amendment": "Amendment 3, 2022",
        "superseded_by": None,
        "category": "steel"
    },
    {
        "is_number": "IS 456:2000",
        "title": "Plain and Reinforced Concrete - Code of Practice",
        "scope_text": "This standard covers general structural use of reinforced and plain concrete, including materials, workmanship, and inspection.",
        "status": "Live",
        "latest_amendment": "Amendment 5, 2021",
        "superseded_by": None,
        "category": "cement"
    },
    {
        "is_number": "IS 1608:2005",
        "title": "Mechanical testing of metals - Tensile testing",
        "scope_text": "This standard specifies the method for tensile testing of metals at room temperature.",
        "status": "Live",
        "latest_amendment": "Reaffirmed 2021",
        "superseded_by": None,
        "category": "testing"
    }
]

def seed_data():
    conn = get_db_connection()
    cur = conn.cursor()
    texts = [std["scope_text"] for std in SAMPLE_STANDARDS]
    embeddings = model.encode(texts, normalize_embeddings=True).tolist()

    insert_data = [
        (std["is_number"], std["title"], std["scope_text"], str(emb), 
         std["status"], std["latest_amendment"], std["superseded_by"], std["category"], '{}')
        for std, emb in zip(SAMPLE_STANDARDS, embeddings)
    ]

    # Upsert ALL fields, not just embedding
    execute_values(cur, """
        INSERT INTO standards (is_number, title, scope_text, scope_embedding, status, latest_amendment, superseded_by, category, raw_metadata)
        VALUES %s
        ON CONFLICT (is_number) DO UPDATE SET 
            title = EXCLUDED.title,
            scope_text = EXCLUDED.scope_text,
            scope_embedding = EXCLUDED.scope_embedding,
            status = EXCLUDED.status,
            latest_amendment = EXCLUDED.latest_amendment;
    """, insert_data)

    cur.execute("SELECT id FROM standards WHERE is_number = 'IS 1786:2008'")
    steel_id = cur.fetchone()['id']
    cur.execute("SELECT id FROM standards WHERE is_number = 'IS 1608:2005'")
    test_id = cur.fetchone()['id']
    
    # FIXED: Changed 'test_method' to 'test_methods' to match router dictionary key
    cur.execute("""
        INSERT INTO standard_relations (standard_id, related_standard_id, relation_type)
        VALUES (%s, %s, 'test_methods')
        ON CONFLICT ON CONSTRAINT standard_relations_uniq DO NOTHING;
    """, (steel_id, test_id))

    cur.execute("""
        INSERT INTO certifications (category, is_number, scheme_name, mandatory, notes)
        VALUES ('steel', 'IS 1786:2008', 'BIS ISI Mark', true, 'Mandatory under Steel QCO')
        ON CONFLICT ON CONSTRAINT certifications_uniq DO NOTHING;
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("✅ Seeded standards, relations, and certifications.")

if __name__ == "__main__":
    seed_data()
