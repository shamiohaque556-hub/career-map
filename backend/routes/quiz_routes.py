import json
import os
import math
from collections import defaultdict

from flask import Blueprint, request, jsonify
from google import genai
from dotenv import load_dotenv

from database import get_connection
from routes.auth_routes import get_current_user

load_dotenv()

quiz_bp = Blueprint("quiz", __name__)


# ── Gemini call with retry on 503 "model busy" errors ─────────────────────────
import time

def generate_with_retry(client, model, contents, max_attempts=2):
    """Call Gemini, retrying on transient 503/overload errors with backoff.
    Raises the last exception if all attempts fail."""
    last_err = None
    for attempt in range(max_attempts):
        try:
            return client.models.generate_content(model=model, contents=contents)
        except Exception as e:
            msg = str(e).lower()
            is_busy = ("503" in msg or "unavailable" in msg or "overloaded" in msg
                       or "high demand" in msg or "try again" in msg)
            last_err = e
            if is_busy and attempt < max_attempts - 1:
                wait = 2 * (attempt + 1)   # 2s, 4s, 6s
                print(f"Gemini busy (attempt {attempt+1}/{max_attempts}), retrying in {wait}s...")
                time.sleep(wait)
                continue
            raise
    raise last_err


# ── SESSION START / RESUME ────────────────────────────────────────────────────

@quiz_bp.route("/session/start", methods=["POST"])
def start_session():
    payload, err = get_current_user()
    if err: return err
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT id FROM quiz_sessions
            WHERE user_id = %s AND is_complete = FALSE
            ORDER BY id DESC LIMIT 1
        """, (payload["user_id"],))
        existing = cur.fetchone()
        if existing:
            session_id = existing["id"]
            cur.execute("SELECT COUNT(*) as count FROM responses WHERE session_id = %s", (session_id,))
            answered_count = cur.fetchone()["count"]
            return jsonify({"session_id": session_id, "resume": True, "answered_count": answered_count}), 200
        cur.execute("INSERT INTO quiz_sessions (user_id) VALUES (%s) RETURNING id", (payload["user_id"],))
        session_id = cur.fetchone()["id"]
        conn.commit()
        return jsonify({"session_id": session_id, "resume": False, "answered_count": 0}), 201
    finally:
        cur.close()
        conn.close()


# ── QUESTIONS ─────────────────────────────────────────────────────────────────

@quiz_bp.route("/questions", methods=["GET"])
def get_questions():
    payload, err = get_current_user()
    if err: return err
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, trait, facet, text, is_reverse FROM questions ORDER BY id ASC")
        return jsonify([dict(row) for row in cur.fetchall()]), 200
    finally:
        cur.close()
        conn.close()


# ── ANSWERS MAP (for resume) ──────────────────────────────────────────────────

@quiz_bp.route("/session/<int:session_id>/answers-map", methods=["GET"])
def get_session_answers_map(session_id):
    payload, err = get_current_user()
    if err: return err
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT question_id, rating FROM responses WHERE session_id = %s AND user_id = %s",
            (session_id, payload["user_id"])
        )
        return jsonify({row["question_id"]: row["rating"] for row in cur.fetchall()}), 200
    finally:
        cur.close()
        conn.close()


# ── SAVE SINGLE ANSWER ────────────────────────────────────────────────────────

@quiz_bp.route("/session/<int:session_id>/answer", methods=["POST"])
def submit_answer(session_id):
    payload, err = get_current_user()
    if err: return err
    data = request.get_json()
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO responses (session_id, user_id, question_id, rating)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (session_id, question_id) DO UPDATE SET rating = EXCLUDED.rating
        """, (session_id, payload["user_id"], data.get("question_id"), data.get("rating")))
        conn.commit()
        return jsonify({"status": "saved"}), 200
    finally:
        cur.close()
        conn.close()


# ── SAVE QUALITATIVE ANSWERS ──────────────────────────────────────────────────

@quiz_bp.route("/session/<int:session_id>/qualitative", methods=["POST"])
def save_qualitative(session_id):
    payload, err = get_current_user()
    if err: return err
    data = request.get_json()
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE quiz_sessions
            SET qualitative_context = %s
            WHERE id = %s AND user_id = %s
        """, (json.dumps(data), session_id, payload["user_id"]))
        conn.commit()
        return jsonify({"status": "saved"}), 200
    finally:
        cur.close()
        conn.close()


# ── COMPLETE SESSION ──────────────────────────────────────────────────────────

@quiz_bp.route("/session/<int:session_id>/complete", methods=["POST"])
def complete_session(session_id):
    payload, err = get_current_user()
    if err: return err
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE quiz_sessions
            SET is_complete = TRUE, finished_at = NOW()
            WHERE id = %s AND user_id = %s
        """, (session_id, payload["user_id"]))
        conn.commit()
        return jsonify({"status": "complete"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ── BLUEPRINT ANSWERS (saved BEFORE report generation) ───────────────────────

@quiz_bp.route("/blueprint", methods=["POST"])
def save_blueprint():
    payload, err = get_current_user()
    if err: return err
    data = request.get_json()
    allowed_keys = {"desire", "evidence", "resistance", "cost"}
    conn = get_connection()
    cur = conn.cursor()
    try:
        for key, answer in data.items():
            if key not in allowed_keys:
                continue
            if not answer or not answer.strip():
                continue
            cur.execute("""
                INSERT INTO blueprint_answers (user_id, question_key, answer_text)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, question_key) DO UPDATE SET answer_text = EXCLUDED.answer_text
            """, (payload["user_id"], key, answer.strip()))
        cur.execute(
            "UPDATE users SET journey_status = 'Exploring' WHERE id = %s",
            (payload["user_id"],)
        )
        conn.commit()
        return jsonify({"status": "saved"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ── VECTOR SPACE ROLE MATCHING ────────────────────────────────────────────────

def calculate_best_roles(facet_scores):
    def fv(key):
        return float(facet_scores.get(key, 3.0))

    # Reduce all 15 facets -> 5 axes (every facet contributes signal)
    user_axes = {
        "al": (fv("Intellectual Curiosity") + fv("Orderliness")
               + fv("Deliberation & Caution") + fv("Duty and Achievement")) / 4.0,
        "sh": (fv("Compassion") + fv("Trust & Cooperation")
               + fv("Modesty & Deference")) / 3.0,
        "pe": (fv("Sociability") + fv("Assertiveness")
               + fv("Sensation Seeking")) / 3.0,
        "rt": ((6.0 - fv("Anxiety Proneness")) + (6.0 - fv("Stress Vulnerability"))
               + (6.0 - fv("Emotional Volatility")) + fv("Sensation Seeking")) / 4.0,
        "as": (fv("Aesthetic Sensitivity") + fv("Creative Imagination")) / 2.0,
    }

    conn = get_connection()
    cur = conn.cursor()
    matches = []
    try:
        cur.execute("""
            SELECT r.role_title, r.target_al, r.target_sh, r.target_pe,
                   r.target_rt, r.target_as, s.sector_name
            FROM archetypal_roles r
            JOIN economic_sectors s ON r.sector_id = s.id
        """)
        roles = cur.fetchall()
        axes = ["al", "sh", "pe", "rt", "as"]

        # Per-axis mean/std across all role targets, for normalization
        stats = {}
        for ax in axes:
            vals = [float(r[f"target_{ax}"]) for r in roles]
            mean = sum(vals) / len(vals)
            std = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals)) or 1.0
            stats[ax] = (mean, std)

        # Distance in normalized space — no axis can dominate
        for role in roles:
            dist_sq = 0.0
            for ax in axes:
                mean, std = stats[ax]
                u = (user_axes[ax] - mean) / std
                t = (float(role[f"target_{ax}"]) - mean) / std
                dist_sq += (u - t) ** 2
            matches.append({
                "role": role["role_title"],
                "sector": role["sector_name"],
                "distance": round(math.sqrt(dist_sq), 4),
                "breakdown": {
                    "AL": float(role["target_al"]), "SH": float(role["target_sh"]),
                    "PE": float(role["target_pe"]), "RT": float(role["target_rt"]),
                    "AS": float(role["target_as"]),
                },
            })
        matches.sort(key=lambda x: x["distance"])
    except Exception as e:
        print(f"Matching error: {e}")
    finally:
        cur.close()
        conn.close()

    return matches or [{"role": "Generalist",
                        "sector": "Entrepreneurship, Innovation & Consultative Agencies",
                        "distance": 0.0, "breakdown": {}}]
    
    
# ── CONTRADICTION DETECTION ───────────────────────────────────────────────────

def detect_contradictions(qualitative_context, avg_facet_scores):
    """
    Compares qualitative free-writing against quantitative scores.
    Returns a list of contradiction strings for injection into the AI prompt.
    These are the most diagnostically valuable signals available.
    """
    contradictions = []

    monday = (qualitative_context.get("monday_context") or "").lower()
    unfinished = (qualitative_context.get("unfinished_context") or "").lower()
    combined = monday + " " + unfinished

    sociability   = avg_facet_scores.get("Sociability", 3.0)
    orderliness   = avg_facet_scores.get("Orderliness", 3.0)
    anxiety       = avg_facet_scores.get("Anxiety Proneness", 3.0)
    assertiveness = avg_facet_scores.get("Assertiveness", 3.0)
    compassion    = avg_facet_scores.get("Compassion", 3.0)
    curiosity     = avg_facet_scores.get("Intellectual Curiosity", 3.0)

    # Solitary ideal vs high sociability score
    solitary_words = ["alone", "quiet", "solitude", "nobody", "by myself", "no one", "just me", "isolated", "in silence", "peaceful silence", "no people"]
    if any(w in combined for w in solitary_words) and sociability > 3.7:
        contradictions.append(
            f"Qualitative writing reveals a strong preference for solitary or quiet environments, "
            f"yet Sociability scores at {sociability:.1f}/5.0. "
            f"This gap frequently indicates social performance capacity that exists alongside — and masks — a genuine daily preference for low-contact environments. "
            f"The person can operate socially but does not recharge from it."
        )

    # Unstructured ideal vs high orderliness
    chaos_words = ["spontaneous", "go with the flow", "no plan", "whatever happens", "see where it goes", "no structure", "free", "just wander", "no schedule", "chaotic"]
    if any(w in combined for w in chaos_words) and orderliness > 3.7:
        contradictions.append(
            f"Writing describes an unstructured or spontaneous ideal state, "
            f"yet Orderliness scores at {orderliness:.1f}/5.0. "
            f"This commonly signals an identity lag: the person's self-image is 'flexible' but their actual behavior is highly structured. "
            f"They may experience rigid habits as freedom because they built the structure themselves."
        )

    # Aspirational calm vs high anxiety
    calm_words = ["calm", "relaxed", "no stress", "peaceful", "easy morning", "no pressure", "chill", "slow morning", "no rush"]
    if any(w in combined for w in calm_words) and anxiety > 3.7:
        contradictions.append(
            f"Writing presents an aspirational calm or low-pressure ideal, "
            f"yet Anxiety Proneness scores at {anxiety:.1f}/5.0. "
            f"This is almost certainly a description of a desired state rather than a current one. "
            f"The person is aware of their anxiety and is writing the antidote, not the reality."
        )

    # Abandonment pattern vs high conscientiousness
    abandon_words = ["gave up", "never finished", "stopped", "abandoned", "lost interest", "moved on", "left it", "didn't follow through", "distracted", "couldn't finish"]
    if any(w in unfinished for w in abandon_words) and orderliness > 3.9:
        contradictions.append(
            f"The unfinished project description contains abandonment language, "
            f"yet Orderliness scores at {orderliness:.1f}/5.0. "
            f"This is a significant contradiction. High-conscientiousness individuals rarely report abandonment unless "
            f"the project violated a core value, the environment removed autonomy, or the goal was adopted externally (other people's expectation) rather than internally chosen."
        )

    # High assertiveness vs explicit conflict-avoidance language
    avoid_words = ["can't say no", "hate conflict", "avoid confrontation", "keep the peace", "don't want to upset", "not worth the argument", "stay quiet"]
    if any(w in combined for w in avoid_words) and assertiveness > 3.7:
        contradictions.append(
            f"Writing signals conflict-avoidance patterns, yet Assertiveness scores at {assertiveness:.1f}/5.0. "
            f"This profile frequently belongs to people who assert strongly within task and intellectual domains "
            f"but systematically avoid interpersonal confrontation — particularly with authority figures or people they care about."
        )

    # High compassion vs described emotional detachment
    detach_words = ["don't care what they think", "don't need people", "independent", "on my own", "no one else involved", "just me and my work"]
    if any(w in combined for w in detach_words) and compassion > 3.9:
        contradictions.append(
            f"Writing expresses emotional independence or detachment from others, "
            f"yet Compassion scores at {compassion:.1f}/5.0. "
            f"This combination often belongs to individuals who feel others' emotions intensely but have learned to "
            f"protect themselves by intellectualizing or minimizing relational needs in their self-description."
        )

    return contradictions


# ── PERSONA REPORT GENERATION ─────────────────────────────────────────────────

@quiz_bp.route("/session/<int:session_id>/persona-report", methods=["POST"])
def generate_report(session_id):
    payload, err = get_current_user()
    if err: return err

    force_refresh = request.args.get("force", "false").lower() == "true"

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Serve cached report unless force=true
        if not force_refresh:
            cur.execute(
                "SELECT report_cached_json, trait_scores FROM summaries WHERE session_id = %s",
                (session_id,)
            )
            cached = cur.fetchone()
            if cached and cached["report_cached_json"]:
                print("Serving cached report.")
                return jsonify({
                    "report": cached["report_cached_json"],
                    "facet_scores": cached["trait_scores"],
                    "top_matches": calculate_best_roles(cached["trait_scores"])
                }), 200

        # ── Gather all context ────────────────────────────────────────────
        cur.execute(
            "SELECT age, gender, occupation, organization, role FROM users WHERE id = %s",
            (payload["user_id"],)
        )
        user_profile = cur.fetchone()
        demographics = {
            "age": user_profile.get("age", "Unknown"),
            "gender": user_profile.get("gender", "Unknown"),
            "occupation_status": user_profile.get("occupation", "Unknown"),
            "organization": user_profile.get("organization", "Unknown"),
            "role": user_profile.get("role", "Unknown")
        }

        cur.execute(
            "SELECT question_key, answer_text FROM blueprint_answers WHERE user_id = %s",
            (payload["user_id"],)
        )
        blueprint_context = {r["question_key"]: r["answer_text"] for r in cur.fetchall()}

        cur.execute("""
            SELECT q.trait, q.facet, r.rating, q.is_reverse
            FROM responses r
            JOIN questions q ON q.id = r.question_id
            WHERE r.session_id = %s
        """, (session_id,))
        rows = cur.fetchall()
        if not rows:
            return jsonify({"error": "No answers found for this session."}), 404

        cur.execute(
            "SELECT qualitative_context FROM quiz_sessions WHERE id = %s",
            (session_id,)
        )
        session_row = cur.fetchone()
        qualitative_context = (session_row["qualitative_context"] or {}) if session_row else {}

        # ── Compute facet scores ──────────────────────────────────────────
        facet_totals = defaultdict(list)
        for row in rows:
            score = (6 - row["rating"]) if row["is_reverse"] else row["rating"]
            facet_totals[row["facet"]].append(score)
        avg_facet_scores = {f: round(sum(v) / len(v), 2) for f, v in facet_totals.items()}

        # ── Role matching ─────────────────────────────────────────────────
        top_roles = calculate_best_roles(avg_facet_scores)
        primary_match = top_roles[0]

        # ── Contradiction detection ───────────────────────────────────────
        contradictions = detect_contradictions(qualitative_context, avg_facet_scores)
        if contradictions:
            contradiction_block = "\n".join(f"  - {c}" for c in contradictions)
        else:
            contradiction_block = "  None detected. Qualitative writing is broadly consistent with quantitative scores."

        # ── Extract key scores for grounding predictions ──────────────────
        orderliness   = avg_facet_scores.get("Orderliness", 3.0)
        anxiety       = avg_facet_scores.get("Anxiety Proneness", 3.0)
        assertiveness = avg_facet_scores.get("Assertiveness", 3.0)
        sociability   = avg_facet_scores.get("Sociability", 3.0)
        compassion    = avg_facet_scores.get("Compassion", 3.0)

        # ── Blueprint quality check ───────────────────────────────────────
        blueprint_note = ""
        if not blueprint_context:
            blueprint_note = "WARNING: No blueprint answers available. Generate analysis from quantitative and qualitative data only. Note this limitation in the_trap chapter."
        elif len(blueprint_context) < 4:
            blueprint_note = f"Partial blueprint data available ({len(blueprint_context)}/4 questions answered). Weight available answers heavily."

        # ── Build the prompt ──────────────────────────────────────────────
        prompt = f"""
You are an exceptionally perceptive psychological analyst writing a personality analysis that WILL be read by the person it describes. Write in second person ("you"), directly to them.

Your standard is honest precision, not flattery: vague praise and generic horoscope-style statements are failures. Name real patterns, real tensions, and real costs — but write like a brilliant mentor who is on this person's side, not like an interrogator. Never diagnose mental-health conditions, never use clinical labels (e.g. "anxiety disorder"), and never be cruel. Honesty and respect at the same time.

If the candidate's age is under 18 or unknown, keep the same honesty but increase warmth and frame every pattern as changeable — this person is still forming.

═══════════════════════════════════════════════════════
CANDIDATE DEMOGRAPHIC PROFILE
═══════════════════════════════════════════════════════
{json.dumps(demographics, indent=2)}

{blueprint_note}

═══════════════════════════════════════════════════════
FOUNDATION BLUEPRINT — DEEP VALUES EXCAVATION
(Candidate answered these in their own words. Read carefully — word choice, hedging, specificity, and avoidance patterns are all diagnostic.)
═══════════════════════════════════════════════════════
{json.dumps(blueprint_context, indent=2) if blueprint_context else "Not yet submitted."}

═══════════════════════════════════════════════════════
QUANTITATIVE PSYCHOMETRIC SCORES (1.0 – 5.0 scale)
═══════════════════════════════════════════════════════
{json.dumps(avg_facet_scores, indent=2)}

Key scores for grounding predictions:
  Orderliness:       {orderliness:.2f} / 5.0
  Anxiety Proneness: {anxiety:.2f} / 5.0
  Assertiveness:     {assertiveness:.2f} / 5.0
  Sociability:       {sociability:.2f} / 5.0
  Compassion:        {compassion:.2f} / 5.0

═══════════════════════════════════════════════════════
QUALITATIVE FREE-WRITING SAMPLES
(Unfiltered responses. Analyze word selection, structural density, what is avoided or omitted.)
═══════════════════════════════════════════════════════
{json.dumps(qualitative_context, indent=2)}

═══════════════════════════════════════════════════════
INTERNAL CONTRADICTION SIGNALS — HIGHEST DIAGNOSTIC VALUE
(Gaps between how the candidate writes and what their scores measure. These indicate self-perception vs. actual behavioral pattern mismatches.)
═══════════════════════════════════════════════════════
{contradiction_block}

═══════════════════════════════════════════════════════
MATCHED CAREER ECOSYSTEM
═══════════════════════════════════════════════════════
Primary Sector:   {primary_match['sector']}
Assigned Role:    {primary_match['role']}
Match Distance:   {primary_match['distance']} (lower = tighter personality alignment)

═══════════════════════════════════════════════════════
ARCHETYPE TITLE — STRICT PROTOCOL
═══════════════════════════════════════════════════════
The title names the candidate's INTERNAL PARADOX — not their strongest trait, not their career function.
Format: [Adjective that names the conflict] + [Noun that names the system they apply it to]

REJECTED titles (too generic — never produce these):
"Creative Strategist", "Analytical Leader", "Empathetic Manager", "Driven Achiever", "Strategic Thinker", "Natural Connector", "Innovative Thinker"

VALID examples and the tension each captures:
- "Disciplined Wanderer" → ordered execution instinct, restless soul that resists confinement
- "Anxious Architect" → builds elaborate systems to manage internal chaos, not external problems
- "Combative Empath" → feels others' pain acutely, then fights about it
- "Precise Idealist" → perfectionist standards applied relentlessly to an imperfect world
- "Collaborative Loner" → performs well in groups, regenerates in isolation, confused about which one is real

Extract the tension from the data. Do not describe the person. Name their fault line.

═══════════════════════════════════════════════════════
NARRATIVE COHERENCE MANDATE — ALL FOUR CHAPTERS FORM ONE ARGUMENT
═══════════════════════════════════════════════════════
The four chapters are not four separate observations. They are a single diagnostic arc.

THE GIFT:
  Identify the CORE BEHAVIORAL PATTERN that defines this person's optimal performance state.
  Be specific — name what they actually do, not a trait category.
  Ground it in the intersection of their highest-scoring facets AND their blueprint answers.
  3-4 sentences. Clinical. No hedging.

THE TRAP:
  Identify the EXACT MECHANISM by which the gift becomes self-defeating under specific conditions.
  Name the conditions precisely (what type of environment, what type of pressure, what type of relationship).
  Name the internal spiral — what thought pattern or behavior loop activates.
  If contradictions were detected above, the trap must address at least one of them directly.
  3-4 sentences. Highly specific — but framed as a pattern they can interrupt, not a verdict.

THE MISREAD:
  Identify the SPECIFIC PROFESSIONAL CONTEXT where The Trap is visible to observers, but The Gift is invisible.
  Name who misreads them (type of manager, type of peer, type of institution) and what they incorrectly conclude.
  This is where the candidate's professional reputation diverges from their actual internal state.
  3-4 sentences. Name the incorrect conclusion others reach, not just that they misread.

THE UNLOCK:
  Identify the PRECISE ENVIRONMENTAL CONFIGURATION that breaks The Trap and restores The Gift.
  This must be actionable and specific to their demographic context ({demographics['occupation_status']}, age {demographics['age']}).
  Not aspirational ("find a company that values you") — operational ("requires X type of autonomy over Y specific domain").
  Must implicitly address the gap identified in The Misread.
  3-4 sentences.

═══════════════════════════════════════════════════════
FALSIFIABLE PREDICTION PROTOCOL
═══════════════════════════════════════════════════════
These three predictions must be specific enough that the candidate can verify them immediately.
If a prediction could apply to 40% of people, it is wrong. Rewrite until it could only apply to ~10%.

DESK STATE:
  Describe the physical configuration of their workspace with ONE specific detail that would surprise observers.
  Ground this in Orderliness ({orderliness:.1f}/5.0) AND their qualitative writing style.
  Example structure: "[General configuration] except [specific surprising detail that reveals the underlying tension]."
  Not: "organized desk." That is useless.

TOXIC MANAGER:
  Name the SPECIFIC SUPERVISORY BEHAVIOR (not personality type) that triggers resignation thinking in this person.
  What does the manager DO? What specifically does it violate in this person?
  Ground in Assertiveness ({assertiveness:.1f}/5.0), Anxiety ({anxiety:.1f}/5.0), and Compassion ({compassion:.1f}/5.0).
  One sentence. Specific behavior, not character description.

INTERNAL MONOLOGUE:
  Write the LITERAL FIRST-PERSON SENTENCE this person says internally at the exact second a project collapses.
  Not a summary of their feeling — the actual thought. In quotes.
  Ground in their Anxiety Proneness ({anxiety:.1f}/5.0) and their unfinished project description.
  One sentence. Must sound like a specific person, not a type.

═══════════════════════════════════════════════════════
OUTPUT FORMAT — RETURN ONLY THIS JSON. NO MARKDOWN. NO PREAMBLE.
═══════════════════════════════════════════════════════
{{
  "archetype_title": "2-3 words capturing the internal paradox",
  "primary_ecosystem": "{primary_match['sector']}",
  "chapters": {{
    "the_gift": "3-4 sentence clinical description of core behavioral advantage",
    "the_trap": "3-4 sentence description of the exact mechanism of self-defeat",
    "the_misread": "3-4 sentence description of how this person is misread professionally",
    "the_unlock": "3-4 sentence description of the specific environment that restores performance"
  }},
  "falsifiable_predictions": {{
    "desk_state": "One sentence with a specific surprising detail about workspace configuration",
    "toxic_manager": "One sentence naming the exact supervisory behavior that triggers resignation",
    "internal_monologue": "One sentence — the literal thought at project collapse, in first person"
  }},
  "trait_explanations": {{
    "Openness": "1-2 sentences: given THIS person's score, why they landed there and what it means in plain language",
    "Conscientiousness": "1-2 sentences, same approach",
    "Extraversion": "1-2 sentences, same approach",
    "Agreeableness": "1-2 sentences, same approach",
    "Neuroticism": "1-2 sentences, same approach (frame constructively, not as a flaw)"
  }}
}}
"""

        # ── Call AI ───────────────────────────────────────────────────────
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        # Using gemini-2.5-flash for report generation.
        # If the AI is unreachable, we return an HONEST error — we do NOT
        # serve a generic pre-written report.
        try:
            ai_response = generate_with_retry(
                client,
                model="gemini-2.5-flash",
                contents=prompt
            )
            raw_text = ai_response.text.strip()
            clean_json = raw_text.replace("```json", "").replace("```", "").strip()
        except Exception as ai_err:
            print(f"Gemini unreachable after retries: {ai_err}")
            conn.rollback()
            cur.close(); conn.close()
            return jsonify({
                "error": "We couldn't generate your analysis right now — the AI service is temporarily unavailable. Please try again in a moment."
            }), 503

        try:
            report_data = json.loads(clean_json)
            required_root = ["archetype_title", "primary_ecosystem", "chapters", "falsifiable_predictions"]
            required_chapters = ["the_gift", "the_trap", "the_misread", "the_unlock"]
            required_preds = ["desk_state", "toxic_manager", "internal_monologue"]
            assert all(k in report_data for k in required_root)
            assert all(c in report_data["chapters"] for c in required_chapters)
            assert all(p in report_data["falsifiable_predictions"] for p in required_preds)
        except (json.JSONDecodeError, AssertionError) as e:
            print(f"AI output validation failed: {e}")
            conn.rollback()
            cur.close(); conn.close()
            return jsonify({
                "error": "The AI returned an unexpected result and we couldn't build your analysis. Please try again."
            }), 502

        # ── Persist ───────────────────────────────────────────────────────
        cur.execute("""
            INSERT INTO summaries (session_id, user_id, trait_scores, report_cached_json)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE
            SET trait_scores = EXCLUDED.trait_scores, report_cached_json = EXCLUDED.report_cached_json
        """, (session_id, payload["user_id"], json.dumps(avg_facet_scores), json.dumps(report_data)))
        cur.execute("UPDATE users SET journey_status = 'Analyzed' WHERE id = %s", (payload["user_id"],))
        conn.commit()

        return jsonify({
            "report": report_data,
            "facet_scores": avg_facet_scores,
            "top_matches": top_roles[:3]
        }), 200

    except Exception as e:
        conn.rollback()
        print(f"Report generation error: {e}")
        return jsonify({"error": "Report generation failed. Check server logs."}), 500
    finally:
        cur.close()
        conn.close()


# ── FEEDBACK (overall slider + per-prediction ratings) ────────────────────────

@quiz_bp.route("/session/<int:session_id>/feedback", methods=["POST"])
def submit_feedback(session_id):
    payload, err = get_current_user()
    if err: return err
    data = request.get_json()
    accuracy_rating = data.get("accuracy_rating")
    prediction_ratings = data.get("prediction_ratings", {})

    conn = get_connection()
    cur = conn.cursor()
    try:
        # Try to store prediction ratings in a column if it exists, else fall back
        try:
            cur.execute("""
                UPDATE summaries
                SET calibration_feedback_score = %s, prediction_ratings = %s
                WHERE session_id = %s AND user_id = %s
            """, (accuracy_rating, json.dumps(prediction_ratings), session_id, payload["user_id"]))
        except Exception:
            conn.rollback()
            cur.execute("""
                UPDATE summaries
                SET calibration_feedback_score = %s
                WHERE session_id = %s AND user_id = %s
            """, (accuracy_rating, session_id, payload["user_id"]))

        # Log prediction ratings for analysis even if DB column missing
        if prediction_ratings:
            print(f"Prediction ratings for session {session_id}: {json.dumps(prediction_ratings)}")

        conn.commit()
        return jsonify({"status": "saved"}), 200
    finally:
        cur.close()
        conn.close()


# ── WORLD MAP ─────────────────────────────────────────────────────────────────

@quiz_bp.route("/world-map", methods=["GET"])
def get_world_map():
    payload, err = get_current_user()
    if err: return err
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT trait_scores FROM summaries
            WHERE user_id = %s
            ORDER BY id DESC LIMIT 1
        """, (payload["user_id"],))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "No summary found. Complete the quiz first."}), 404

        raw = row["trait_scores"]
        trait_scores = json.loads(raw) if isinstance(raw, str) else raw

        all_matches = calculate_best_roles(trait_scores)
        primary = all_matches[0]

        reasoning = (
            f"Your personality vector places you closest to '{primary['role']}' in {primary['sector']}. "
            f"The match distance is {primary['distance']} — lower means tighter alignment between your "
            f"measured behavioral tendencies and what this role operationally demands."
        )

        cur.execute("""
            SELECT s.id, s.sector_name, s.core_driver,
                   COALESCE(json_agg(
                       json_build_object(
                           'title', r.role_title,
                           'role_description', COALESCE(r.role_description, 'Pathway details pending.'),
                           'honest_reality', COALESCE(r.honest_reality, 'Demands sustained cognitive commitment.')
                       )
                   ) FILTER (WHERE r.role_title IS NOT NULL), '[]') as roles
            FROM economic_sectors s
            LEFT JOIN archetypal_roles r ON s.id = r.sector_id
            GROUP BY s.id, s.sector_name, s.core_driver
            ORDER BY s.id ASC
        """)
        all_sectors = [dict(row) for row in cur.fetchall()]

        return jsonify({
            "top_matches": all_matches[:3],
            "algorithmic_reasoning": reasoning,
            "all_sectors": all_sectors,
            "user_traits": trait_scores
        }), 200
    except Exception as e:
        print(f"World map error: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ── COMPATIBILITY CHECK ───────────────────────────────────────────────────────

@quiz_bp.route("/compatibility-check", methods=["POST"])
def check_compatibility():
    payload, err = get_current_user()
    if err: return err
    data = request.get_json()
    roles = data.get("roles", [])
    if len(roles) < 2:
        return jsonify({"compatible": True, "distance": 0.0}), 200

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT role_title, target_al, target_sh, target_pe, target_rt, target_as FROM archetypal_roles WHERE role_title IN %s",
            (tuple(roles),)
        )
        rows = cur.fetchall()
        if len(rows) < 2:
            return jsonify({"compatible": True, "distance": 0.0}), 200

        r1, r2 = rows[0], rows[1]
        dist = math.sqrt(
            (float(r1["target_al"]) - float(r2["target_al"])) ** 2 +
            (float(r1["target_sh"]) - float(r2["target_sh"])) ** 2 +
            (float(r1["target_pe"]) - float(r2["target_pe"])) ** 2 +
            (float(r1["target_rt"]) - float(r2["target_rt"])) ** 2 +
            (float(r1["target_as"]) - float(r2["target_as"])) ** 2
        )
        warning = dist > 2.0
        msg = (
            "These two paths require opposing personality configurations. Someone pursuing both will find "
            "that the discipline one demands makes the other feel like escape — and that cycle becomes the career, not either path."
            if warning else "These paths are personality-compatible. Commitment to both is structurally coherent."
        )
        return jsonify({"distance": round(dist, 2), "warning": warning, "message": msg}), 200
    finally:
        cur.close()
        conn.close()


# ── NETWORK PEERS ─────────────────────────────────────────────────────────────

@quiz_bp.route("/network", methods=["GET"])
def get_network_peers():
    payload, err = get_current_user()
    if err: return err
    ecosystem = request.args.get("ecosystem")
    conn = get_connection()
    cur = conn.cursor()
    try:
        if ecosystem:
            cur.execute("""
                SELECT id, name, role, organization, locked_ecosystems
                FROM users
                WHERE journey_status = 'Locked_In'
                AND locked_ecosystems::jsonb @> jsonb_build_array(%s)
                AND id != %s
            """, (ecosystem, payload["user_id"]))
        else:
            cur.execute("""
                SELECT id, name, role, organization, locked_ecosystems
                FROM users
                WHERE journey_status = 'Locked_In' AND id != %s
            """, (payload["user_id"],))
        return jsonify([dict(row) for row in cur.fetchall()]), 200
    finally:
        cur.close()
        conn.close()


# ── PATH LOCKING ──────────────────────────────────────────────────────────────

@quiz_bp.route("/user/lock-path", methods=["POST"])
def lock_user_path():
    payload, err = get_current_user()
    if err: return err
    data = request.get_json()
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE users SET journey_status = 'Locked_In', locked_ecosystems = %s WHERE id = %s",
            (json.dumps(data.get("paths", [])), payload["user_id"])
        )
        conn.commit()
        return jsonify({"status": "success"}), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cur.close()
        conn.close()


# ── CANVAS STEPS ──────────────────────────────────────────────────────────────

@quiz_bp.route("/canvas/step", methods=["POST"])
def save_canvas_step():
    payload, err = get_current_user()
    if err: return err
    data = request.get_json()
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO canvas_steps (user_id, step_id, step_title, description, deliverable, resource_url, is_locked)
            VALUES (%s, %s, %s, %s, %s, %s, TRUE)
            ON CONFLICT (user_id, step_id) DO UPDATE
            SET step_title = EXCLUDED.step_title, description = EXCLUDED.description,
                deliverable = EXCLUDED.deliverable, resource_url = EXCLUDED.resource_url
        """, (payload["user_id"], data.get("step_id", 1), data.get("title"), data.get("description"), data.get("deliverable"), data.get("url")))
        conn.commit()
        return jsonify({"status": "saved"}), 200
    finally:
        cur.close()
        conn.close()


@quiz_bp.route("/canvas/step/<int:step_id>", methods=["GET"])
def get_canvas_step(step_id):
    payload, err = get_current_user()
    if err: return err
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT step_title, description, deliverable, resource_url, is_locked FROM canvas_steps WHERE user_id = %s AND step_id = %s",
            (payload["user_id"], step_id)
        )
        row = cur.fetchone()
        return jsonify(dict(row) if row else {"is_locked": False}), 200
    finally:
        cur.close()
        conn.close()
        


# ════════════════════════════════════════════════════════════════════
#  AI ROADMAP GENERATION
#  Paste this whole block into quiz_routes.py (anywhere among the other
#  @quiz_bp routes — e.g. right after the CANVAS STEPS section).
#
#  It reuses your existing imports already at the top of quiz_routes.py:
#     import json, os
#     from flask import request, jsonify
#     from google import genai
#     from routes.auth_routes import get_current_user
#     quiz_bp  (the Blueprint)
#
#  So you do NOT need to add new imports or register anything new.
#  The frontend calls:  POST /api/quiz/generate-roadmap
# ════════════════════════════════════════════════════════════════════

@quiz_bp.route("/generate-roadmap", methods=["POST"])
def generate_roadmap():
    payload, err = get_current_user()
    if err:
        return err

    data = request.get_json() or {}

    # ---- inputs from the canvas (the chosen path + the 4 answers) ----
    role_name        = (data.get("role_name") or "").strip()
    role_description = (data.get("role_description") or "").strip()
    role_reality     = (data.get("role_reality") or "").strip()
    current_level    = (data.get("current_level") or "").strip()
    time_available   = (data.get("time_available") or "").strip()
    goal             = (data.get("goal") or "").strip()
    budget           = (data.get("budget") or "").strip()

    if not role_name:
        return jsonify({"error": "No path provided."}), 400

    # ---- the approved prompt, filled in ----
    prompt = f"""You are an expert learning mentor and career coach. Your job is to create a practical, step-by-step learning roadmap for someone who wants to learn a specific career path. The roadmap must be realistic and tailored to their current level, available time, goal, and budget.

The path they want to learn: {role_name} — {role_description or "a career path"}

The honest reality of this path (factor this into the roadmap so they're prepared): {role_reality or "Requires consistent, sustained effort to build real competence."}

About this learner:
- Current level: {current_level or "not specified"}
- Time available: {time_available or "not specified"}
- Their goal / timeline: {goal or "not specified"}
- Budget for learning: {budget or "not specified"}

Your task: Create a clear, ordered, step-by-step roadmap that takes this person from their current level to their goal, respecting their time and budget. The steps should build on each other logically — foundations first, then progressively more advanced. Be specific and actionable (not vague advice). Where their budget allows paid resources, you may suggest the type of resource (e.g. "an online course in X"); where budget is tight, favour free/self-directed steps. Match the number and size of steps to their available time and timeline.

Format your answer as a JSON array ONLY, with no extra text, no markdown, no code fences, like this:
[{{"step": "Learn the fundamentals of X", "detail": "why this matters and what to focus on", "estimate": "2 weeks"}}]

Give between 6 and 12 steps. Return ONLY the JSON array."""

    # ---- call Gemini (same client style as the rest of quiz_routes.py) ----
    try:
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        raw = (response.text or "").strip()

        # strip accidental code fences if the model adds them
        if raw.startswith("```"):
            raw = raw.split("```", 2)[1] if "```" in raw else raw
            if raw.lower().startswith("json"):
                raw = raw[4:]
            raw = raw.strip("` \n")

        # find the JSON array within the text, just in case
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1:
            raw = raw[start:end + 1]

        steps = json.loads(raw)
        if not isinstance(steps, list):
            raise ValueError("Model did not return a list.")

        # normalize each step to {step, detail, estimate}
        clean = []
        for s in steps:
            if isinstance(s, dict) and s.get("step"):
                clean.append({
                    "step": str(s.get("step", "")).strip(),
                    "detail": str(s.get("detail", "")).strip(),
                    "estimate": str(s.get("estimate", "")).strip(),
                })
        if not clean:
            raise ValueError("No valid steps parsed.")

        return jsonify({"steps": clean}), 200

    except Exception as e:
        print(f"Roadmap generation error: {e}")
        return jsonify({"error": "Could not generate a roadmap right now. Please try again."}), 500
        


# ════════════════════════════════════════════════════════════════════
#  ADMIN CONTENT ENDPOINTS  — career content read/save
#  Paste this whole block into quiz_routes.py (with the other routes).
#
#  Reuses imports you already have: json, os, request, jsonify,
#  get_current_user, quiz_bp.  Adds ONE new need: a way to know the
#  path to industries.json and who is an admin.
#
#  Frontend calls:
#     GET  /api/quiz/admin/industries        -> returns the full JSON
#     POST /api/quiz/admin/industries        -> saves the full JSON
# ════════════════════════════════════════════════════════════════════

# --- where industries.json lives. Adjust if your file sits elsewhere. ---
# This assumes industries.json is in your FRONTEND folder. Point it at the
# real location on your machine.
import os
INDUSTRIES_PATH = os.environ.get(
    "INDUSTRIES_PATH",
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "industries.json")
)

# --- who is allowed to edit. Simplest: an allow-list of admin emails. ---
# Put your own login email here (or set ADMIN_EMAILS in your .env, comma-separated).
ADMIN_EMAILS = [
    e.strip().lower()
    for e in os.environ.get("ADMIN_EMAILS", "").split(",")
    if e.strip()
]

def _is_admin(payload):
    """Tokens issued by auth_routes now include the email. For older tokens
    that only carry user_id, fall back to a DB lookup."""
    if not ADMIN_EMAILS:
        return False
    email = (payload.get("email") or "").lower()
    if not email and payload.get("user_id"):
        conn = get_connection(); cur = conn.cursor()
        try:
            cur.execute("SELECT email FROM users WHERE id = %s", (payload["user_id"],))
            row = cur.fetchone()
            email = (row["email"] or "").lower() if row else ""
        finally:
            cur.close(); conn.close()
    return email in ADMIN_EMAILS


@quiz_bp.route("/admin/industries", methods=["GET"])
def admin_get_industries():
    payload, err = get_current_user()
    if err:
        return err
    if not _is_admin(payload):
        return jsonify({"error": "Admin access required."}), 403
    try:
        with open(INDUSTRIES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data), 200
    except FileNotFoundError:
        # if the file doesn't exist yet, return an empty shell
        return jsonify({"version": 1, "industries": []}), 200
    except Exception as e:
        print(f"admin_get_industries error: {e}")
        return jsonify({"error": "Could not read content."}), 500


@quiz_bp.route("/admin/industries", methods=["POST"])
def admin_save_industries():
    payload, err = get_current_user()
    if err:
        return err
    if not _is_admin(payload):
        return jsonify({"error": "Admin access required."}), 403

    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "industries" not in data:
        return jsonify({"error": "Invalid content: expected an object with an 'industries' list."}), 400
    if not isinstance(data["industries"], list):
        return jsonify({"error": "'industries' must be a list."}), 400

    try:
        # write a timestamped backup first, so a bad save can be recovered
        if os.path.exists(INDUSTRIES_PATH):
            import time
            backup = INDUSTRIES_PATH + f".bak-{int(time.time())}"
            try:
                with open(INDUSTRIES_PATH, "r", encoding="utf-8") as f:
                    old = f.read()
                with open(backup, "w", encoding="utf-8") as f:
                    f.write(old)
            except Exception as be:
                print(f"backup warning: {be}")  # non-fatal

        # write atomically: temp file then replace
        tmp = INDUSTRIES_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, INDUSTRIES_PATH)

        total_roles = sum(
            len(fam.get("roles", []))
            for ind in data["industries"]
            for fam in ind.get("families", [])
        )
        return jsonify({
            "ok": True,
            "industries": len(data["industries"]),
            "roles": total_roles
        }), 200
    except Exception as e:
        print(f"admin_save_industries error: {e}")
        return jsonify({"error": "Could not save content."}), 500
