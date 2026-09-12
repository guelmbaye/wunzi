"""
Multilingual lexicon for the Kinyarwanda ⇄ English ⇄ French configuration.

Scope note: this is a demo-grade lexicon covering the Rental Deposit MVP. It is
deliberately narrow and is documented as a limitation — it is not a general
morphological analyser for Kinyarwanda.
"""

from __future__ import annotations

# ── Negation ───────────────────────────────────────────────────────────────
NEGATION_MARKERS: dict[str, tuple[str, ...]] = {
    "en": (
        "not", "n't", "never", "no ", "did not", "didn't", "won't", "wasn't",
        "isn't", "haven't", "hasn't", "refused", "denies", "denied", "without",
    ),
    "fr": (
        "ne ", "n'", "pas", "jamais", "aucun", "aucune", "rien", "refuse",
        "refusé", "nie", "nié", "sans",
    ),
    # Kinyarwanda negative morphology / particles.
    "rw": (
        "nta", "ntabwo", "ntibyo", "ntiya", "ntiba", "sinzi", "si ",
        "ntacyo", "ntawe", "ntiyigeze", "yanze",
    ),
}

# Explicit double-negation traps that must NOT flip polarity twice.
NEGATION_EXCEPTIONS: tuple[str, ...] = ("not only", "no doubt", "pas seulement")

# ── Reported speech ────────────────────────────────────────────────────────
REPORTED_SPEECH_MARKERS: dict[str, tuple[str, ...]] = {
    "en": ("he said", "she said", "they said", "told me", "telling me",
           "he promised", "she promised", "they promised", "promised me",
           "said that", "says that", "he says", "she says", "claims that"),
    "fr": ("il a dit", "elle a dit", "m'a dit", "il a promis", "elle a promis",
           "m'a promis", "disait que", "prétend que", "il dit que", "elle dit que"),
    "rw": ("yambwiye", "yavuze", "yaransezeranije", "baravuze", "yansezeranije",
           "aravuga ko", "avuga ko", "yansezeranyije"),
}

# ── Self-correction ────────────────────────────────────────────────────────
CORRECTION_MARKERS: tuple[str, ...] = (
    "no,", "no.", "sorry", "i mean", "actually", "rather",
    "non,", "pardon", "je veux dire", "plutôt",
    "oya", "ni ukuvuga", "mbabarira",
)

# ── Domain predicates ──────────────────────────────────────────────────────
DEPOSIT_MARKERS: tuple[str, ...] = (
    "deposit", "caution", "garantie", "ingwate", "avansi",
)
REFUND_MARKERS: tuple[str, ...] = (
    "refund", "return the money", "give back", "pay me back", "rembours", "restituer",
    "kunsubiza", "gusubiza", "gusubizwa", "nzamusubiza", "amafaranga yanjye",
)
COMMITMENT_MARKERS: tuple[str, ...] = (
    "promised", "agreed", "committed", "guaranteed", "would refund",
    "would return", "would pay", "told me he would", "told me she would",
    "promis", "accepté", "convenu", "s'est engagé",
    "yasezeranye", "yemeye", "yansezeranije", "namusezeranyije", "yansezeranyije",
    "sezeran",
)
DAMAGE_MARKERS: tuple[str, ...] = (
    "damage", "damaged", "broken", "crack", "wall", "door",
    "dégât", "dommage", "abîmé", "cassé",
    "kwangiza", "byangiritse", "urukuta", "nangije", "wangije", "yangije",
    "icyumba", "yangiritse",
)
REPAIR_MARKERS: tuple[str, ...] = (
    "repair", "fix", "réparation", "réparer", "gusana", "kubaka",
)
MOVE_OUT_MARKERS: tuple[str, ...] = (
    "moved out", "move-out", "left the house", "vacated", "handed the keys",
    "contract ended", "tenancy ended", "end of the contract", "lease ended",
    "déménagé", "quitté", "rendu les clés", "fin du contrat",
    "navuye", "nasize inzu", "kuva mu nzu", "narangije contract",
    "narangije amasezerano", "narangije",
)

# "Deduct the repair cost before refunding" is not "refund everything".
# Collapsing the two would erase the disagreement the mediator needs to see.
DEDUCTION_MARKERS: tuple[str, ...] = (
    "deduct", "subtract", "take out of", "withhold", "keep part",
    "déduire", "retenir", "soustraire",
    "gukata", "gufata kuri", "nkatemo",
)
EVIDENCE_MARKERS: dict[str, tuple[str, ...]] = {
    "repair_invoice": ("invoice", "receipt for the repair", "facture", "fagitire"),
    "payment_receipt": ("receipt", "proof of payment", "reçu", "inyemezabwishyu"),
    "rental_agreement": ("contract", "agreement", "lease", "contrat", "amasezerano"),
    "property_photos": ("photo", "picture", "photos", "amafoto"),
}
REQUESTED_OUTCOME_MARKERS: tuple[str, ...] = (
    "i want", "i am asking", "i request", "i expect", "i would like",
    "je veux", "je demande", "je souhaite",
    "ndashaka", "nashaka", "nsaba", "ndasaba",
)

# ── First person ───────────────────────────────────────────────────────────
# MVP-scoped list of Kinyarwanda first-person verb forms seen in rental-deposit
# accounts. Deliberately explicit rather than a broad prefix rule: a wrong
# subject invents an accusation, so guessing is not an acceptable default.
FIRST_PERSON_RW: tuple[str, ...] = (
    "nishyuye", "narangije", "ndashaka", "nashaka", "nangije", "mfite",
    "nasize", "navuye", "nsaba", "ndasaba", "namusezeranyije", "nzamusubiza",
    "njye", "nanjye", "yanjye",
)

# ── Currency ───────────────────────────────────────────────────────────────
CURRENCY_MARKERS: dict[str, tuple[str, ...]] = {
    "RWF": ("rwf", "frw", "francs", "franc", "amafaranga", "rwandan francs"),
}

# ── Numbers ────────────────────────────────────────────────────────────────
EN_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
EN_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50,
    "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90,
}
EN_SCALES = {"hundred": 100, "thousand": 1_000, "million": 1_000_000}

FR_UNITS = {
    "zéro": 0, "zero": 0, "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4,
    "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
    "onze": 11, "douze": 12, "treize": 13, "quatorze": 14, "quinze": 15,
    "seize": 16,
}
FR_TENS = {
    "vingt": 20, "trente": 30, "quarante": 40, "cinquante": 50,
    "soixante": 60, "quatre-vingts": 80, "quatre-vingt": 80,
}
FR_SCALES = {"cent": 100, "cents": 100, "mille": 1_000, "million": 1_000_000, "millions": 1_000_000}

# Kinyarwanda numerals — narrow subset sufficient for MVP amounts.
RW_UNITS = {
    "rimwe": 1, "kimwe": 1, "imwe": 1,
    "ebyiri": 2, "kabiri": 2, "bibiri": 2, "ibiri": 2,
    "gatatu": 3, "bitatu": 3, "itatu": 3,
    "kane": 4, "bine": 4, "ine": 4,
    "gatanu": 5, "bitanu": 5, "itanu": 5,
    "gatandatu": 6, "itandatu": 6,
    "karindwi": 7, "irindwi": 7,
    "umunani": 8, "inani": 8,
    "icyenda": 9, "icumi": 10,
}
RW_SCALES = {
    "magana": 100,        # hundreds
    "igihumbi": 1_000,
    "ibihumbi": 1_000,    # thousands
    "miliyoni": 1_000_000,
}
RW_TENS_MARKER = "mirongo"  # tens

MONTHS = {
    "january": 1, "janvier": 1, "mutarama": 1,
    "february": 2, "février": 2, "fevrier": 2, "gashyantare": 2,
    "march": 3, "mars": 3, "werurwe": 3,
    "april": 4, "avril": 4, "mata": 4,
    "may": 5, "mai": 5, "gicurasi": 5,
    "june": 6, "juin": 6, "kamena": 6,
    "july": 7, "juillet": 7, "nyakanga": 7,
    "august": 8, "août": 8, "aout": 8, "kanama": 8,
    "september": 9, "septembre": 9, "nzeri": 9,
    "october": 10, "octobre": 10, "ukwakira": 10,
    "november": 11, "novembre": 11, "ugushyingo": 11,
    "december": 12, "décembre": 12, "decembre": 12, "ukuboza": 12,
}
