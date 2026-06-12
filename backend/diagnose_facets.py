# Diagnostic: do the facet names in the DB match what calculate_best_roles expects?
# Run from backend/:  python diagnose_facets.py
from database import get_connection

# the exact facet names the matching code looks for
EXPECTED = [
    "Intellectual Curiosity","Orderliness","Deliberation & Caution","Duty and Achievement",
    "Compassion","Trust & Cooperation","Modesty & Deference",
    "Sociability","Assertiveness","Sensation Seeking",
    "Anxiety Proneness","Stress Vulnerability","Emotional Volatility",
    "Aesthetic Sensitivity","Creative Imagination",
]

conn = get_connection(); cur = conn.cursor()
cur.execute("SELECT DISTINCT facet FROM questions ORDER BY facet")
db_facets = [r["facet"] for r in cur.fetchall()]
cur.close(); conn.close()

print("=== Facet names IN YOUR DATABASE ===")
for f in db_facets: print("  ", repr(f))

print("\n=== Names the MATCHING CODE expects ===")
for f in EXPECTED: print("  ", repr(f))

missing = [f for f in EXPECTED if f not in db_facets]
extra   = [f for f in db_facets if f not in EXPECTED]

print("\n=== RESULT ===")
if not missing:
    print("✓ All expected facets exist in the DB — names match. Bug is elsewhere.")
else:
    print(">>> MISMATCH FOUND. These names the code expects are NOT in the DB:")
    for f in missing: print("   MISSING:", repr(f))
    print("\n   → Because these don't match, the code defaults them to 3.0 for EVERY user,")
    print("     making everyone's scores nearly identical → everyone matches the same sector.")
if extra:
    print("\n   DB has these facets the code doesn't use (possible renamed versions):")
    for f in extra: print("   EXTRA:  ", repr(f))