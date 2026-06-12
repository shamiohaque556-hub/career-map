"""One-shot database setup. Run ONCE against a fresh database:
    python setup_db.py
Creates the full schema, seeds the 75 facet-mapped questions, and seeds the
career-world taxonomy. Safe to re-run (seeds replace their own tables only).
"""
from database import init_db
import seed_questions
import seed_world

if __name__ == "__main__":
    print("1/3 Creating schema...")
    init_db()
    print("2/3 Seeding questions...")
    seed_questions.seed_database()
    print("3/3 Seeding career worlds...")
    seed_world.seed_world()
    print("\nDone. The database is ready.")
