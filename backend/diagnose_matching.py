# Diagnostic: shows whether the "everyone gets hospitality" bug is in the
# role target DATA. Run from backend/:  python diagnose_matching.py
from database import get_connection

conn = get_connection()
cur = conn.cursor()

# 1) How many roles per sector, and their target values
cur.execute("""
    SELECT s.sector_name, COUNT(r.id) AS n,
           ROUND(AVG(r.target_al),2) AS al, ROUND(AVG(r.target_sh),2) AS sh,
           ROUND(AVG(r.target_pe),2) AS pe, ROUND(AVG(r.target_rt),2) AS rt,
           ROUND(AVG(r.target_as),2) AS as_
    FROM economic_sectors s
    LEFT JOIN archetypal_roles r ON s.id = r.sector_id
    GROUP BY s.sector_name
    ORDER BY s.sector_name
""")
print("=== Sectors and their average target values ===")
for row in cur.fetchall():
    print(f"{row['sector_name'][:40]:42} n={row['n']:3}  AL={row['al']} SH={row['sh']} PE={row['pe']} RT={row['rt']} AS={row['as_']}")

# 2) Total roles
cur.execute("SELECT COUNT(*) AS c FROM archetypal_roles")
print("\nTotal roles in archetypal_roles:", cur.fetchone()["c"])

# 3) Check if target values are all identical/empty (the likely bug)
cur.execute("""
    SELECT COUNT(DISTINCT (target_al, target_sh, target_pe, target_rt, target_as)) AS distinct_targets,
           COUNT(*) AS total
    FROM archetypal_roles
""")
r = cur.fetchone()
print(f"Distinct target combinations: {r['distinct_targets']} out of {r['total']} roles")
if r['distinct_targets'] <= 1:
    print(">>> BUG FOUND: all roles have the SAME (or no) target values — matching can't differentiate, so everyone gets whatever sorts first.")
elif r['distinct_targets'] < r['total'] * 0.3:
    print(">>> SUSPICIOUS: very few distinct targets — many roles are identical, weakening matching.")
else:
    print(">>> Target data looks varied — bug may be elsewhere.")

cur.close(); conn.close()