import os
from dotenv import load_dotenv
from database import get_connection

load_dotenv()
# 75-Question Psychological Battery Mapped to Accurate Facets
PSYCHOMETRIC_BATTERY = [
    # ─── OPENNESS TO EXPERIENCE ──────────────────────────────────────────────
    {"trait": "Openness", "facet": "Intellectual Curiosity", "text": "I find myself absorbed in abstract philosophical discussions.", "is_reverse": False},
    {"trait": "Openness", "facet": "Intellectual Curiosity", "text": "I avoid complex theoretical arguments whenever possible.", "is_reverse": True},
    {"trait": "Openness", "facet": "Intellectual Curiosity", "text": "I enjoy solving puzzles or riddles that require deep logical reasoning.", "is_reverse": False},
    {"trait": "Openness", "facet": "Intellectual Curiosity", "text": "I prefer sticking to practical facts rather than unproven hypotheses.", "is_reverse": True},
    {"trait": "Openness", "facet": "Intellectual Curiosity", "text": "I am deeply curious about how advanced technical systems operate under the hood.", "is_reverse": False},
    
    {"trait": "Openness", "facet": "Creative Imagination", "text": "I spend a significant amount of time daydreaming or imagining alternative realities.", "is_reverse": False},
    {"trait": "Openness", "facet": "Creative Imagination", "text": "I rarely create fictional scenarios or stories in my head.", "is_reverse": True},
    {"trait": "Openness", "facet": "Creative Imagination", "text": "I feel a strong urge to design, write, or build original creative works.", "is_reverse": False},
    {"trait": "Openness", "facet": "Creative Imagination", "text": "I prefer concrete realities over artistic or symbolic concepts.", "is_reverse": True},
    {"trait": "Openness", "facet": "Creative Imagination", "text": "I often find unconventional solutions to problems by combining unrelated ideas.", "is_reverse": False},
    
    {"trait": "Openness", "facet": "Aesthetic Sensitivity", "text": "I am deeply moved by exceptional art, music, or atmospheric cinema.", "is_reverse": False},
    {"trait": "Openness", "facet": "Aesthetic Sensitivity", "text": "I rarely notice the design or artistic choices of my physical surroundings.", "is_reverse": True},
    {"trait": "Openness", "facet": "Aesthetic Sensitivity", "text": "A beautifully composed piece of music can give me literal chills.", "is_reverse": False},
    {"trait": "Openness", "facet": "Aesthetic Sensitivity", "text": "I view art and design as secondary to pure functional utility.", "is_reverse": True},
    {"trait": "Openness", "facet": "Aesthetic Sensitivity", "text": "I enjoy exploring architecture and structural styles when visiting new places.", "is_reverse": False},

    # ─── CONSCIENTIOUSNESS ───────────────────────────────────────────────────
    {"trait": "Conscientiousness", "facet": "Orderliness", "text": "If I see a picture hanging slightly crooked on a wall, I feel an itch to fix it.", "is_reverse": False},
    {"trait": "Conscientiousness", "facet": "Orderliness", "text": "I am perfectly comfortable working in a messy or unorganized environment.", "is_reverse": True},
    {"trait": "Conscientiousness", "facet": "Orderliness", "text": "I map out my tasks, schedules, and workflows in meticulous detail.", "is_reverse": False},
    {"trait": "Conscientiousness", "facet": "Orderliness", "text": "I prefer spontaneity over following a strict daily routine.", "is_reverse": True},
    {"trait": "Conscientiousness", "facet": "Orderliness", "text": "I meticulously organize my digital files, code repositories, or documents.", "is_reverse": False},
    
    {"trait": "Conscientiousness", "facet": "Duty and Achievement", "text": "I hold myself to exceptionally high standards and feel anxious if I don't meet them.", "is_reverse": False},
    {"trait": "Conscientiousness", "facet": "Duty and Achievement", "text": "I am satisfied with doing just enough to get by comfortably.", "is_reverse": True},
    {"trait": "Conscientiousness", "facet": "Duty and Achievement", "text": "I finish what I start, even when the initial excitement has completely faded.", "is_reverse": False},
    {"trait": "Conscientiousness", "facet": "Duty and Achievement", "text": "I frequently abandon projects midway when they become tedious or demanding.", "is_reverse": True},
    {"trait": "Conscientiousness", "facet": "Duty and Achievement", "text": "I prioritize my long-term career goals over short-term comfort or leisure.", "is_reverse": False},
    
    {"trait": "Conscientiousness", "facet": "Deliberation & Caution", "text": "I analyze risks thoroughly before making a significant life or career decision.", "is_reverse": False},
    {"trait": "Conscientiousness", "facet": "Deliberation & Caution", "text": "I frequently make major purchases or commitments on impulse.", "is_reverse": True},
    {"trait": "Conscientiousness", "facet": "Deliberation & Caution", "text": "I prefer having a backup plan ready before launching any new project.", "is_reverse": False},
    {"trait": "Conscientiousness", "facet": "Deliberation & Caution", "text": "I jump straight into execution and figure out the details as I go along.", "is_reverse": True},
    {"trait": "Conscientiousness", "facet": "Deliberation & Caution", "text": "I rarely say things I later regret during intense debates.", "is_reverse": False},

    # ─── EXTRAVERSION ────────────────────────────────────────────────────────
    {"trait": "Extraversion", "facet": "Sociability", "text": "Spending an evening surrounded by a large crowd of strangers sounds exhausting to me.", "is_reverse": True},
    {"trait": "Extraversion", "facet": "Sociability", "text": "I feel charged with energy after hosting or interacting at social gatherings.", "is_reverse": False},
    {"trait": "Extraversion", "facet": "Sociability", "text": "I prefer solitary deep-work sessions over collaborative brainstorming groups.", "is_reverse": True},
    {"trait": "Extraversion", "facet": "Sociability", "text": "I am naturally expressive and vocalize my thoughts easily in public settings.", "is_reverse": False},
    {"trait": "Extraversion", "facet": "Sociability", "text": "I systematically avoid networking events unless they are strictly mandatory.", "is_reverse": True},
    
    {"trait": "Extraversion", "facet": "Assertiveness", "text": "I naturally step up and take charge of a group when leadership is lacking.", "is_reverse": False},
    {"trait": "Extraversion", "facet": "Assertiveness", "text": "I prefer to let others make the final decisions and lead the strategy.", "is_reverse": True},
    {"trait": "Extraversion", "facet": "Assertiveness", "text": "I am highly comfortable asserting my opinions, even when the room disagrees.", "is_reverse": False},
    {"trait": "Extraversion", "facet": "Assertiveness", "text": "I keep my insights to myself if voicing them causes social friction.", "is_reverse": True},
    {"trait": "Extraversion", "facet": "Assertiveness", "text": "I command attention easily when presenting information to an audience.", "is_reverse": False},
    
    {"trait": "Extraversion", "facet": "Sensation Seeking", "text": "I crave fast-paced environments with high stakes and dynamic action.", "is_reverse": False},
    {"trait": "Extraversion", "facet": "Sensation Seeking", "text": "I prefer a predictable, calm environment over an unpredictable adventure.", "is_reverse": True},
    {"trait": "Extraversion", "facet": "Sensation Seeking", "text": "I am drawn to physical adrenaline sports, martial arts, or high-intensity tasks.", "is_reverse": False},
    {"trait": "Extraversion", "facet": "Sensation Seeking", "text": "I dislike chaotic environments where everything changes minute-by-minute.", "is_reverse": True},
    {"trait": "Extraversion", "facet": "Sensation Seeking", "text": "I enjoy testing the boundaries of what is considered safe or conventional.", "is_reverse": False},

    # ─── AGREEABLENESS ───────────────────────────────────────────────────────
    {"trait": "Agreeableness", "facet": "Compassion", "text": "I am deeply affected by the suffering, struggles, and emotions of others.", "is_reverse": False},
    {"trait": "Agreeableness", "facet": "Compassion", "text": "I tend to analyze people's issues logically rather than offering emotional empathy.", "is_reverse": True},
    {"trait": "Agreeableness", "facet": "Compassion", "text": "I frequently go out of my way to help colleagues or friends with their tasks.", "is_reverse": False},
    {"trait": "Agreeableness", "facet": "Compassion", "text": "I believe individuals should pull themselves up without relying on sympathy.", "is_reverse": True},
    {"trait": "Agreeableness", "facet": "Compassion", "text": "I place immense value on maintaining deep, supportive human relationships.", "is_reverse": False},
    
    {"trait": "Agreeableness", "facet": "Trust & Cooperation", "text": "I naturally assume that most people have good intentions unless proven otherwise.", "is_reverse": False},
    {"trait": "Agreeableness", "facet": "Trust & Cooperation", "text": "I am highly skeptical of hidden motives when someone offers unexpected help.", "is_reverse": True},
    {"trait": "Agreeableness", "facet": "Trust & Cooperation", "text": "I find immense value in collaborating closely with diverse teams.", "is_reverse": False},
    {"trait": "Agreeableness", "facet": "Trust & Cooperation", "text": "I work best when I am completely independent and don't rely on anyone.", "is_reverse": True},
    {"trait": "Agreeableness", "facet": "Trust & Cooperation", "text": "I value strict honesty and direct truth far above diplomatic politeness.", "is_reverse": True},
    
    {"trait": "Agreeableness", "facet": "Modesty & Deference", "text": "I dislike boasting about my personal achievements or professional success.", "is_reverse": False},
    {"trait": "Agreeableness", "facet": "Modesty & Deference", "text": "I make sure people know exactly what I contributed to a major victory.", "is_reverse": True},
    {"trait": "Agreeableness", "facet": "Modesty & Deference", "text": "I am willing to compromise my preferences to keep peace in a group.", "is_reverse": False},
    {"trait": "Agreeableness", "facet": "Modesty & Deference", "text": "I will cause an absolute scene if it means defending my core principles.", "is_reverse": True},
    {"trait": "Agreeableness", "facet": "Modesty & Deference", "text": "I welcome blunt constructive criticism without taking offense.", "is_reverse": False},

    # ─── NEUROTICISM ─────────────────────────────────────────────────────────
    {"trait": "Neuroticism", "facet": "Anxiety Proneness", "text": "I frequently worry about future scenarios or catastrophes that may never happen.", "is_reverse": False},
    {"trait": "Neuroticism", "facet": "Anxiety Proneness", "text": "I remain calm and relaxed even under immense professional pressure.", "is_reverse": True},
    {"trait": "Neuroticism", "facet": "Anxiety Proneness", "text": "I experience significant stress when unexpected changes disrupt my layout.", "is_reverse": False},
    {"trait": "Neuroticism", "facet": "Anxiety Proneness", "text": "I sleep soundly even when major business problems remain completely unresolved.", "is_reverse": True},
    {"trait": "Neuroticism", "facet": "Anxiety Proneness", "text": "I constantly scan my environment or data systems for potential hidden errors.", "is_reverse": False},
    
    {"trait": "Neuroticism", "facet": "Emotional Volatility", "text": "My mood can shift rapidly depending on how my current project is performing.", "is_reverse": False},
    {"trait": "Neuroticism", "facet": "Emotional Volatility", "text": "My emotional baseline is stable; very few events can throw me off balance.", "is_reverse": True},
    {"trait": "Neuroticism", "facet": "Emotional Volatility", "text": "I feel deeply frustrated and irritated when tools or code libraries break.", "is_reverse": False},
    {"trait": "Neuroticism", "facet": "Emotional Volatility", "text": "I treat setbacks as objective data points rather than personal failures.", "is_reverse": True},
    {"trait": "Neuroticism", "facet": "Emotional Volatility", "text": "I experience strong bouts of self-doubt regarding my long-term capabilities.", "is_reverse": False},
    
    {"trait": "Neuroticism", "facet": "Stress Vulnerability", "text": "I am easily overwhelmed when forced to balance multiple conflicting demands.", "is_reverse": False},
    {"trait": "Neuroticism", "facet": "Stress Vulnerability", "text": "I operate smoothly in high-pressure, chaotic environments.", "is_reverse": True},
    {"trait": "Neuroticism", "facet": "Stress Vulnerability", "text": "Minor criticisms or rejections can keep me awake thinking for hours.", "is_reverse": False},
    {"trait": "Neuroticism", "facet": "Stress Vulnerability", "text": "I bounce back almost immediately from failure or professional rejection.", "is_reverse": True},
    {"trait": "Neuroticism", "facet": "Stress Vulnerability", "text": "I feel a profound sense of pressure when responsible for high-stakes deliverables.", "is_reverse": False}
]

def seed_database():
    conn = get_connection()
    cur = conn.cursor()
    try:
        print("Cleaning old placeholder questions...")
        cur.execute("TRUNCATE TABLE responses CASCADE;")
        cur.execute("TRUNCATE TABLE questions CASCADE;")
        
        print(f"Injecting full psychometric battery ({len(PSYCHOMETRIC_BATTERY)} questions with facet mapping)...")
        for q in PSYCHOMETRIC_BATTERY:
            cur.execute("""
                INSERT INTO questions (trait, facet, text, is_reverse)
                VALUES (%s, %s, %s, %s)
            """, (q["trait"], q["facet"], q["text"], q["is_reverse"]))
            
        conn.commit()
        print("Successfully seeded all 75 advanced behavioural questions.")
    except Exception as e:
        conn.rollback()
        print(f"Migration Error: {e}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    seed_database()