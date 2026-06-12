# Diagnostic: run several DIFFERENT personality profiles through the REAL matching
# logic and see what sector each gets. Run from backend/: python diagnose_match_test.py
import math
from database import get_connection

def calculate_best_roles(facet_scores):
    def fv(key): return float(facet_scores.get(key, 3.0))
    user_axes = {
        "al": (fv("Intellectual Curiosity") + fv("Orderliness") + fv("Deliberation & Caution") + fv("Duty and Achievement")) / 4.0,
        "sh": (fv("Compassion") + fv("Trust & Cooperation") + fv("Modesty & Deference")) / 3.0,
        "pe": (fv("Sociability") + fv("Assertiveness") + fv("Sensation Seeking")) / 3.0,
        "rt": ((6.0 - fv("Anxiety Proneness")) + (6.0 - fv("Stress Vulnerability")) + (6.0 - fv("Emotional Volatility")) + fv("Sensation Seeking")) / 4.0,
        "as": (fv("Aesthetic Sensitivity") + fv("Creative Imagination")) / 2.0,
    }
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""SELECT r.role_title, r.target_al, r.target_sh, r.target_pe, r.target_rt, r.target_as, s.sector_name
                   FROM archetypal_roles r JOIN economic_sectors s ON r.sector_id = s.id""")
    roles = cur.fetchall(); cur.close(); conn.close()
    axes = ["al","sh","pe","rt","as"]
    stats = {}
    for ax in axes:
        vals = [float(r[f"target_{ax}"]) for r in roles]
        mean = sum(vals)/len(vals)
        std = math.sqrt(sum((v-mean)**2 for v in vals)/len(vals)) or 1.0
        stats[ax] = (mean, std)
    matches = []
    for role in roles:
        d = 0.0
        for ax in axes:
            mean,std = stats[ax]
            u = (user_axes[ax]-mean)/std
            t = (float(role[f"target_{ax}"])-mean)/std
            d += (u-t)**2
        matches.append((round(math.sqrt(d),3), role["sector_name"], role["role_title"]))
    matches.sort()
    return user_axes, matches[0]

# Test profiles — deliberately VERY different people
profiles = {
  "Highly creative artist":   {"Aesthetic Sensitivity":5,"Creative Imagination":5,"Intellectual Curiosity":4,"Sociability":2,"Assertiveness":2,"Orderliness":2,"Compassion":4,"Trust & Cooperation":3,"Modesty & Deference":3,"Sensation Seeking":3,"Anxiety Proneness":3,"Stress Vulnerability":3,"Emotional Volatility":3,"Deliberation & Caution":3,"Duty and Achievement":3},
  "Analytical engineer":      {"Intellectual Curiosity":5,"Orderliness":5,"Deliberation & Caution":5,"Duty and Achievement":5,"Compassion":2,"Trust & Cooperation":2,"Sociability":1,"Assertiveness":2,"Aesthetic Sensitivity":2,"Creative Imagination":2,"Sensation Seeking":2,"Anxiety Proneness":2,"Stress Vulnerability":2,"Emotional Volatility":2,"Modesty & Deference":3},
  "Social caregiver":         {"Compassion":5,"Trust & Cooperation":5,"Modesty & Deference":4,"Sociability":4,"Assertiveness":2,"Intellectual Curiosity":3,"Orderliness":3,"Aesthetic Sensitivity":3,"Creative Imagination":3,"Sensation Seeking":2,"Anxiety Proneness":3,"Stress Vulnerability":3,"Emotional Volatility":3,"Deliberation & Caution":3,"Duty and Achievement":3},
  "Bold athlete/extravert":   {"Sociability":5,"Assertiveness":5,"Sensation Seeking":5,"Anxiety Proneness":1,"Stress Vulnerability":1,"Emotional Volatility":1,"Compassion":3,"Trust & Cooperation":3,"Intellectual Curiosity":3,"Orderliness":3,"Aesthetic Sensitivity":2,"Creative Imagination":2,"Modesty & Deference":2,"Deliberation & Caution":2,"Duty and Achievement":4},
  "All neutral (3.0)":        {},
}

print("=== What sector does each VERY DIFFERENT person get? ===\n")
results = {}
for name, prof in profiles.items():
    axes, top = calculate_best_roles(prof)
    results[name] = top[1]
    print(f"{name:26} -> {top[1][:38]:40} (dist {top[0]}, role: {top[2][:30]})")
    print(f"{'':26}    axes: AL={axes['al']:.2f} SH={axes['sh']:.2f} PE={axes['pe']:.2f} RT={axes['rt']:.2f} AS={axes['as']:.2f}")

distinct = set(results.values())
print(f"\n=== RESULT ===")
print(f"Distinct sectors across {len(profiles)} very different people: {len(distinct)}")
if len(distinct) == 1:
    print(f">>> BUG CONFIRMED: everyone gets '{list(distinct)[0]}' regardless of personality.")
else:
    print(">>> Matching DOES differentiate. The 4 different test people got:", distinct)
    print("    If real users still all get hospitality, the issue is in the real SCORES being saved (not the matching).")