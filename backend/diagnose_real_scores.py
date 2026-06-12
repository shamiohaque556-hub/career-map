# Diagnostic: look at the MOST RECENT completed session's real saved answers
# and the facet scores they produce. Run from backend/: python diagnose_real_scores.py
from collections import defaultdict
from database import get_connection

conn = get_connection(); cur = conn.cursor()

# most recent sessions
cur.execute("""SELECT id, user_id, is_complete FROM quiz_sessions ORDER BY id DESC LIMIT 5""")
sessions = cur.fetchall()
print("=== Recent sessions ===")
for s in sessions: print(f"  session {s['id']}  user {s['user_id']}  complete={s['is_complete']}")

if not sessions:
    print("No sessions found."); cur.close(); conn.close(); raise SystemExit

# inspect the most recent one
sid = sessions[0]["id"]
print(f"\n=== Inspecting session {sid} ===")

cur.execute("SELECT COUNT(*) AS c FROM responses WHERE session_id = %s", (sid,))
print("Answers saved for this session:", cur.fetchone()["c"], "(expect 75)")

# how the report query reads them
cur.execute("""SELECT q.facet, r.rating, q.is_reverse
               FROM responses r JOIN questions q ON q.id = r.question_id
               WHERE r.session_id = %s""", (sid,))
rows = cur.fetchall()
print("Rows joined for scoring:", len(rows))

facet_totals = defaultdict(list)
for row in rows:
    score = (6 - row["rating"]) if row["is_reverse"] else row["rating"]
    facet_totals[row["facet"]].append(score)
avg = {f: round(sum(v)/len(v),2) for f,v in facet_totals.items()}

print("\n=== Computed facet scores for this real session ===")
if not avg:
    print(">>> EMPTY — no answers scored. This is why everyone gets neutral/hospitality.")
else:
    for f,v in sorted(avg.items()): print(f"  {f:28} {v}")
    vals = list(avg.values())
    spread = max(vals) - min(vals)
    print(f"\nScore range: {min(vals)} to {max(vals)}  (spread {round(spread,2)})")
    if spread < 0.5:
        print(">>> SCORES ARE TOO FLAT — everything near the same value → everyone matches the same sector.")
    else:
        print(">>> Scores ARE varied. If matching still gives hospitality, check WHICH session the report uses.")

# also check the rating distribution — are all answers the same number?
cur.execute("SELECT rating, COUNT(*) AS c FROM responses WHERE session_id=%s GROUP BY rating ORDER BY rating", (sid,))
print("\n=== Rating distribution (how the user actually answered) ===")
for r in cur.fetchall(): print(f"  rating {r['rating']}: {r['c']} answers")

cur.close(); conn.close()