"""Seeded demo care providers. All fictional (is_synthetic) and shown as such in the API.

One source of truth: scripts/migrate.py upserts these into the `providers` table, and mock mode
(no database) serves this list directly. Ids are fixed so bookings survive a re-seed.
Keep the wording plain: this is what a new parent reads when choosing who to see.
"""
from uuid import UUID

PROVIDERS: list[dict] = [
    {
        "id": UUID("00000000-0000-4000-8000-0000000000a1"),
        "name": "Dr. Amara Okafor",
        "specialty": "Obstetrician-gynecologist",
        "kind": "obstetrics",
        "bio": "Postpartum checkups, recovery after a C-section, and anything that feels off after birth.",
        "modes": ["in_person", "virtual"],
        "clinic": "Harbor Women's Health",
        "address": "100 Harbor Street, College Park, MD",
        "hours": [9, 10, 14, 15],
    },
    {
        "id": UUID("00000000-0000-4000-8000-0000000000a2"),
        "name": "Dr. Daniel Reyes",
        "specialty": "Blood pressure and heart health after pregnancy",
        "kind": "blood_pressure",
        "bio": "Checks rising blood pressure, reviews your home readings and adjusts the plan with you.",
        "modes": ["in_person", "virtual"],
        "clinic": "Harbor Women's Health",
        "address": "100 Harbor Street, College Park, MD",
        "hours": [10, 11, 14, 16],
    },
    {
        "id": UUID("00000000-0000-4000-8000-0000000000a3"),
        "name": "Nina Patel, CNM",
        "specialty": "Certified nurse-midwife",
        "kind": "midwifery",
        "bio": "Longer visits for recovery, feeding, sleep and the questions that come up at home.",
        "modes": ["in_person", "virtual"],
        "clinic": "Tidewater Midwifery",
        "address": "42 Bayview Avenue, Hyattsville, MD",
        "hours": [9, 11, 13, 15],
    },
    {
        "id": UUID("00000000-0000-4000-8000-0000000000a4"),
        "name": "Grace Lin, IBCLC",
        "specialty": "Lactation consultant",
        "kind": "lactation",
        "bio": "Help with latch, pain, supply and pumping, by video from your couch.",
        "modes": ["virtual"],
        "clinic": "Tidewater Midwifery",
        "address": None,
        "hours": [10, 13, 16],
    },
    {
        "id": UUID("00000000-0000-4000-8000-0000000000a5"),
        "name": "Dr. Marcus Webb",
        "specialty": "Perinatal mental health",
        "kind": "mental_health",
        "bio": "Support for low mood, anxiety and overwhelm after birth. No judgment, no rush.",
        "modes": ["virtual", "in_person"],
        "clinic": "Calm Harbor Counseling",
        "address": "7 Lighthouse Lane, Greenbelt, MD",
        "hours": [11, 14, 17],
    },
]

PROVIDERS_BY_ID = {p["id"]: p for p in PROVIDERS}
