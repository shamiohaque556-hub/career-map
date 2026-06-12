from database import get_connection

# The Master Taxonomy with Psychometric Vectors
# Manufacturing and Skilled Trades are now TWO separate sectors.
SECTORS_DATA = [
    {
        "name": "Academics, Education & Scientific Research",
        "driver": "The pursuit of objective truth, generation and preservation of knowledge.",
        "roles": [
            {"title": "The Frontier Explorer (Pure Researcher)", "al": 4.9, "sh": 2.0, "pe": 2.5, "rt": 4.0, "as": 3.5},
            {"title": "The Mind Catalyst (Teacher/Mentor)", "al": 3.8, "sh": 4.9, "pe": 4.0, "rt": 2.0, "as": 3.8}
        ]
    },
    {
        "name": "Creative, Cultural, Media & Design Arts",
        "driver": "The translation of human psychological states into structural or visual artifacts.",
        "roles": [
            {"title": "The Atmospheric Director (Filmmaker)", "al": 3.5, "sh": 4.0, "pe": 3.5, "rt": 4.5, "as": 4.9},
            {"title": "The World Builder (Game/Sequential Artist)", "al": 4.2, "sh": 2.5, "pe": 1.5, "rt": 4.0, "as": 5.0}
        ]
    },
    {
        "name": "Government, The Army & Jurisprudence",
        "driver": "The maintenance of civil order, defense, and constitutional justice.",
        "roles": [
            {"title": "The Sovereign Guardian (Military/Tactical)", "al": 4.0, "sh": 3.5, "pe": 4.5, "rt": 4.5, "as": 2.0},
            {"title": "The Systemic Arbiter (Judge/Administrator)", "al": 4.5, "sh": 3.8, "pe": 2.0, "rt": 2.5, "as": 2.5}
        ]
    },
    {
        "name": "Finance, Insurance, Real Estate & Corporate Strategy",
        "driver": "The optimization, protection, pricing, and structural deployment of capital and assets.",
        "roles": [
            {"title": "The Quantitative Maximizer (Investment Banker)", "al": 4.8, "sh": 2.5, "pe": 1.5, "rt": 4.5, "as": 2.0},
            {"title": "The Asset Strategist (Real Estate Developer)", "al": 4.5, "sh": 3.8, "pe": 1.8, "rt": 4.0, "as": 3.0}
        ]
    },
    {
        "name": "Entrepreneurship, Innovation & Consultative Agencies",
        "driver": "The rapid synthesis of market opportunities and venture construction under extreme ambiguity.",
        "roles": [
            {"title": "The Market Catalyst (Founder/Agency Owner)", "al": 4.5, "sh": 4.0, "pe": 2.5, "rt": 4.9, "as": 3.5},
            {"title": "The Automation Architect (Systems Consultant)", "al": 4.6, "sh": 2.5, "pe": 1.5, "rt": 3.5, "as": 3.0}
        ]
    },
    {
        "name": "Healthcare, Longevity & Healing Sciences",
        "driver": "The biological preservation, surgical repair, and psychological restoration of living systems.",
        "roles": [
            {"title": "The Crisis Restorer (Surgeon/ER Physician)", "al": 4.6, "sh": 3.5, "pe": 4.0, "rt": 4.2, "as": 2.5},
            {"title": "The Empathetic Harmonizer (Psychotherapist)", "al": 4.3, "sh": 4.9, "pe": 3.0, "rt": 2.5, "as": 3.0}
        ]
    },
    {
        "name": "Digital Technology, Software Engineering & Systems Architecture",
        "driver": "The construction, securing, and maintenance of virtual infrastructure and automated logic.",
        "roles": [
            {"title": "The System Architect (Backend/DevOps Engineer)", "al": 4.9, "sh": 1.5, "pe": 1.0, "rt": 3.0, "as": 3.0},
            {"title": "The Intelligence Engineer (AI/Data Scientist)", "al": 4.7, "sh": 2.0, "pe": 1.0, "rt": 3.5, "as": 4.0}
        ]
    },
    {
        "name": "Agriculture, Food Systems & Natural Resources",
        "driver": "The optimization of biological production, food security, and natural resource management.",
        "roles": [
            {"title": "The Planetary Cultivator (Agrotech Engineer)", "al": 4.2, "sh": 3.5, "pe": 4.5, "rt": 3.5, "as": 3.2},
            {"title": "The Preservationist (Conservation Biologist)", "al": 3.9, "sh": 4.0, "pe": 4.2, "rt": 3.0, "as": 4.0}
        ]
    },

    # ─── SPLIT: Manufacturing is now its own world ──────────────────────────
    {
        "name": "Industrial Manufacturing & Automation",
        "driver": "The systemic transformation of raw materials into finished goods through optimized, increasingly automated production lines.",
        "roles": [
            {"title": "The Operations Orchestrator (Plant / Production Manager)", "al": 4.0, "sh": 3.8, "pe": 4.5, "rt": 3.0, "as": 2.5},
            {"title": "The Automation Architect (Robotics / Process Engineer)", "al": 4.7, "sh": 2.5, "pe": 3.2, "rt": 3.0, "as": 2.5}
        ]
    },

    # ─── SPLIT: Skilled Trades is now its own world ─────────────────────────
    {
        "name": "Skilled Trades & Technical Craft",
        "driver": "The hands-on installation, diagnosis, and repair of the physical systems that keep the built world running.",
        "roles": [
            {"title": "The Kinetic Diagnostician (Mechanic / HVAC Technician)", "al": 4.2, "sh": 2.5, "pe": 4.8, "rt": 3.5, "as": 2.0},
            {"title": "The Master Craftsman (Electrician / Plumber / Welder)", "al": 3.7, "sh": 2.8, "pe": 4.9, "rt": 3.2, "as": 2.6}
        ]
    },

    {
        "name": "Retail, Wholesale & Omnichannel Commerce",
        "driver": "The transactional matching of global supply to consumer demand through distribution.",
        "roles": [
            {"title": "The Distribution Orchestrator (Logistics Manager)", "al": 4.0, "sh": 3.2, "pe": 2.5, "rt": 3.5, "as": 2.5},
            {"title": "The Brand Custodian (Luxury Merchandiser)", "al": 3.8, "sh": 4.0, "pe": 2.5, "rt": 3.2, "as": 4.5}
        ]
    },
    {
        "name": "Hospitality, Global Tourism & Human Services",
        "driver": "The management of physical travel experiences, community support, and high-touch service.",
        "roles": [
            {"title": "The Experience Curator (Executive Chef/Director)", "al": 3.5, "sh": 4.8, "pe": 4.2, "rt": 3.5, "as": 4.5},
            {"title": "The Humanitarian Coordinator (NGO Lead)", "al": 3.5, "sh": 4.9, "pe": 3.5, "rt": 3.0, "as": 3.5}
        ]
    },
    {
        "name": "Sustainability, Climate Tech & Utilities",
        "driver": "The preservation of planetary habitability, clean energy transition, and baseline resource provision.",
        "roles": [
            {"title": "The Grid Engineer (Renewable Energy/Utilities)", "al": 4.6, "sh": 3.2, "pe": 4.0, "rt": 3.0, "as": 2.5},
            {"title": "The Climate Compliance Architect (ESG Analyst)", "al": 4.5, "sh": 4.2, "pe": 2.0, "rt": 2.8, "as": 2.8}
        ]
    },
    {
        "name": "Athletics, Sports & Physical Performance",
        "driver": "The pursuit of peak human physical optimization and competitive kinetic strategy.",
        "roles": [
            {"title": "The Tactical Kinetic (Athlete/Coach)", "al": 3.8, "sh": 3.5, "pe": 5.0, "rt": 4.8, "as": 2.5},
            {"title": "The Biomechanical Optimizer (Sports Scientist)", "al": 4.5, "sh": 4.0, "pe": 4.5, "rt": 3.5, "as": 2.5}
        ]
    },
    {
        "name": "Core Engineering & Hardware Architecture",
        "driver": "The mathematical design, structural integrity, and physical creation of advanced technological infrastructure.",
        "roles": [
            {"title": "The Structural Innovator (Civil/Mechanical)", "al": 4.6, "sh": 3.0, "pe": 3.5, "rt": 3.0, "as": 2.5},
            {"title": "The Electrical Systems Architect", "al": 4.8, "sh": 2.5, "pe": 2.5, "rt": 3.5, "as": 2.0}
        ]
    }
]

def seed_world():
    conn = get_connection()
    cur = conn.cursor()

    try:
        print("Wiping old taxonomy tables...")
        cur.execute("""
            DROP TABLE IF EXISTS archetypal_roles CASCADE;
            DROP TABLE IF EXISTS economic_sectors CASCADE;

            CREATE TABLE economic_sectors (
                id SERIAL PRIMARY KEY,
                sector_name VARCHAR(150) UNIQUE NOT NULL,
                core_driver TEXT NOT NULL
            );

            CREATE TABLE archetypal_roles (
                id SERIAL PRIMARY KEY,
                sector_id INTEGER REFERENCES economic_sectors(id) ON DELETE CASCADE,
                role_title VARCHAR(150) NOT NULL,
                target_al NUMERIC(3,2),
                target_sh NUMERIC(3,2),
                target_pe NUMERIC(3,2),
                target_rt NUMERIC(3,2),
                target_as NUMERIC(3,2),
                role_description TEXT,
                honest_reality TEXT
            );
        """)

        print(f"Seeding {len(SECTORS_DATA)} sectors...")
        for sector in SECTORS_DATA:
            cur.execute(
                "INSERT INTO economic_sectors (sector_name, core_driver) VALUES (%s, %s) RETURNING id",
                (sector["name"], sector["driver"])
            )
            sector_id = cur.fetchone()["id"]

            for role in sector["roles"]:
                cur.execute("""
                    INSERT INTO archetypal_roles
                        (sector_id, role_title, target_al, target_sh, target_pe, target_rt, target_as,
                         role_description, honest_reality)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (sector_id, role["title"], role["al"], role["sh"], role["pe"], role["rt"], role["as"],
                      role.get("desc"), role.get("reality")))

        conn.commit()
        role_count = sum(len(s["roles"]) for s in SECTORS_DATA)
        print(f"Success! {len(SECTORS_DATA)} sectors and {role_count} roles are live.")
    except Exception as e:
        conn.rollback()
        print(f"Error during seeding: {str(e)}")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    seed_world()