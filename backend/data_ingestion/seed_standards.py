import os
from sentence_transformers import SentenceTransformer
from db.session import get_db_connection
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

print("Loading embedding model (takes ~1 min on first run)...")
model = SentenceTransformer('BAAI/bge-m3')

# NOTE: every entry below is a real IS number; the scope_text is a condensed
# paraphrase of the official scope, not a verbatim copy of the BIS abstract.
# Verify titles/amendment years against the BIS catalogue before publishing.
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
    },
    # --- added so every relation_type in the API response has seed rows ---
    {
        "is_number": "IS 375:1987",
        "title": "Common Rules for Construction of Plain and Reinforced Concrete",
        "scope_text": "Common rules covering materials, workmanship, inspection and safety precautions for building plain and reinforced concrete structures.",
        "status": "Live",
        "latest_amendment": "Reaffirmed 2019",
        "superseded_by": None,
        "category": "safety"
    },
    {
        "is_number": "IS 4926:2003",
        "title": "Ready-Mixed Concrete - Code of Practice",
        "scope_text": "Code of practice covering production, supply, delivery, placing, compaction and curing of ready-mixed concrete at site.",
        "status": "Live",
        "latest_amendment": "Reaffirmed 2019",
        "superseded_by": None,
        "category": "cement"
    },
    {
        "is_number": "IS 1199:1958",
        "title": "Methods of Sampling and Analysis of Concrete",
        "scope_text": "Methods for sampling fresh concrete and for carrying out analysis tests to determine cement content, water-cement ratio and strength.",
        "status": "Live",
        "latest_amendment": "Reaffirmed 2018",
        "superseded_by": None,
        "category": "testing"
    },
    {
        "is_number": "IS 1033:1983",
        "title": "Vocabulary of Building and Civil Engineering Terms",
        "scope_text": "Standard terminology and vocabulary used in building and civil engineering construction, materials and structural works.",
        "status": "Live",
        "latest_amendment": "Reaffirmed 2016",
        "superseded_by": None,
        "category": "terminology"
    },
    {
        "is_number": "IS 14480:1995",
        "title": "Hallmarked Gold and Silver Jewellery - Requirements",
        "scope_text": "Requirements for hallmarked precious metal jewellery including purity marking, hallo marking and testing of gold and silver articles.",
        "status": "Live",
        "latest_amendment": "Amendment 1, 2019",
        "superseded_by": None,
        "category": "jewellery"
    },
    {
        "is_number": "IS 14681:2018",
        "title": "LED Modules and LED Luminaires - Requirements and Tests",
        "scope_text": "Performance, safety and testing requirements for LED modules and LED luminaires used in general lighting applications.",
        "status": "Live",
        "latest_amendment": "Amendment 1, 2021",
        "superseded_by": None,
        "category": "electrical"
    }
]

# relation_type values must match the keys of the allied_standards dict
# in backend/routers/analyze.py, otherwise the row is silently dropped.
STANDARD_RELATIONS = [
    ("IS 1786:2008", "IS 1608:2005", "test_methods"),
    ("IS 1786:2008", "IS 375:1987", "safety"),
    ("IS 1786:2008", "IS 456:2000", "installation"),
    ("IS 1786:2008", "IS 4926:2003", "installation"),
    ("IS 456:2000", "IS 375:1987", "safety"),
    ("IS 456:2000", "IS 1199:1958", "test_methods"),
    ("IS 456:2000", "IS 1033:1983", "terminology"),
    ("IS 456:2000", "IS 4926:2003", "installation"),
    ("IS 4926:2003", "IS 1199:1958", "test_methods"),
    ("IS 14480:1995", "IS 1033:1983", "terminology"),
    ("IS 14681:2018", "IS 1033:1983", "terminology"),
]

# (category, is_number, scheme_name, mandatory, notes)
# The router matches on `category = <standard.category> OR is_number = <number>`.
CERTIFICATIONS = [
    ("steel", "IS 1786:2008", "BIS ISI Mark", True, "Mandatory under Steel QCO"),
    ("cement", "IS 456:2000", "BIS ISI Mark", True, "Mandatory for structural concrete"),
    ("electrical", "IS 14681:2018", "CRS", True, "Compulsory Registration Scheme certification required for LED lighting products"),
    ("jewellery", "IS 14480:1995", "BIS Hallmarking", True, "Hallmarking compulsory for gold and silver jewellery above 0.01 gram"),
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

    # One batched lookup keeps the relation insert to a single round-trip
    # instead of 2N queries.
    cur.execute("SELECT id, is_number FROM standards")
    ids_by_number = {row["is_number"]: row["id"] for row in cur.fetchall()}

    missing = [
        number
        for pair in STANDARD_RELATIONS
        for number in pair[:2]
        if number not in ids_by_number
    ]
    if missing:
        raise RuntimeError(
            "Cannot insert relations, these IS numbers are not in the standards "
            f"table: {sorted(set(missing))}"
        )

    execute_values(cur, """
        INSERT INTO standard_relations (standard_id, related_standard_id, relation_type)
        VALUES %s
        ON CONFLICT ON CONSTRAINT standard_relations_uniq DO NOTHING;
    """, [
        (ids_by_number[source], ids_by_number[target], relation_type)
        for source, target, relation_type in STANDARD_RELATIONS
    ])

    execute_values(cur, """
        INSERT INTO certifications (category, is_number, scheme_name, mandatory, notes)
        VALUES %s
        ON CONFLICT ON CONSTRAINT certifications_uniq DO NOTHING;
    """, CERTIFICATIONS)

    conn.commit()
    cur.close()
    conn.close()
    # Plain ASCII: the Windows console defaults to cp1252 and a Unicode
    # character in this print crashes the script *after* the data is committed.
    print(
        f"OK: seeded {len(SAMPLE_STANDARDS)} standards, "
        f"{len(STANDARD_RELATIONS)} relations, "
        f"{len(CERTIFICATIONS)} certifications."
    )

if __name__ == "__main__":
    seed_data()
