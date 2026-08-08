#!/usr/bin/env python3
"""100-word everyday sweep — origin + formation. Read-only; no network, no writes.

Expected origins are MY assessment, not an authority's. They are used only to surface candidates
for Saran to verify. The interesting column is CONFIDENT-WRONG: a high-confidence answer that
contradicts a well-documented etymology. `unknown` is NOT an error — it is the design rule working.
"""
import asyncio
import os
import sys
from pathlib import Path

os.environ["THAMIZH_TXN_LOG"] = "0"          # never pollute the gold log with a sweep
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from thamizh_mcp.core.engine import default_engine

# (word, expected class, note) — "?" where I am not confident enough to call it.
WORDS = [
    # --- native everyday (இயற்சொல்) --------------------------------------------------------
    ("மரம்", "இயற்சொல்", ""), ("வீடு", "இயற்சொல்", ""), ("நீர்", "இயற்சொல்", ""),
    ("கை", "இயற்சொல்", ""), ("கால்", "இயற்சொல்", ""), ("கண்", "இயற்சொல்", ""),
    ("தலை", "இயற்சொல்", ""), ("மண்", "இயற்சொல்", ""), ("கல்", "இயற்சொல்", ""),
    ("நெல்", "இயற்சொல்", ""), ("பால்", "இயற்சொல்", ""), ("தீ", "இயற்சொல்", ""),
    ("வான்", "இயற்சொல்", ""), ("மலை", "இயற்சொல்", ""), ("ஆறு", "இயற்சொல்", ""),
    ("கடல்", "இயற்சொல்", ""), ("மகன்", "இயற்சொல்", ""), ("மகள்", "இயற்சொல்", ""),
    ("தந்தை", "இயற்சொல்", ""), ("தாய்", "இயற்சொல்", ""), ("ஊர்", "இயற்சொல்", ""),
    ("நாடு", "இயற்சொல்", ""), ("சொல்", "இயற்சொல்", ""), ("நூல்", "இயற்சொல்", ""),
    ("வழி", "இயற்சொல்", ""), ("பெயர்", "இயற்சொல்", ""), ("நிலம்", "இயற்சொல்", ""),
    ("மழை", "இயற்சொல்", ""), ("பூ", "இயற்சொல்", ""), ("இலை", "இயற்சொல்", ""),
    ("வேர்", "இயற்சொல்", ""), ("விதை", "இயற்சொல்", ""), ("உணவு", "இயற்சொல்", ""),
    ("உடை", "இயற்சொல்", ""), ("பசு", "இயற்சொல்", ""), ("நாய்", "இயற்சொல்", ""),
    ("பறவை", "இயற்சொல்", ""), ("மீன்", "இயற்சொல்", ""), ("விளக்கு", "இயற்சொல்", ""),
    ("கதவு", "இயற்சொல்", ""), ("சாலை", "இயற்சொல்", ""), ("பள்ளி", "இயற்சொல்", ""),
    ("அலுவலகம்", "இயற்சொல்", "modern native coinage"),
    ("கணினி", "இயற்சொல்", "modern native coinage"),
    ("தொலைபேசி", "இயற்சொல்", "modern native coinage"),

    # --- Sanskrit (வடசொல்) ------------------------------------------------------------------
    ("ஜோதி", "வடசொல்", ""), ("புத்தகம்", "வடசொல்", "Skt pustaka"),
    ("ஆசிரியர்", "வடசொல்", "Skt ācārya"), ("ராஜா", "வடசொல்", ""),
    ("சந்திரன்", "வடசொல்", ""), ("சூரியன்", "வடசொல்", ""), ("காலம்", "வடசொல்", ""),
    ("தானம்", "வடசொல்", ""), ("யோகம்", "வடசொல்", ""), ("பக்தி", "வடசொல்", ""),
    ("மந்திரம்", "வடசொல்", ""), ("சாஸ்திரம்", "வடசொல்", ""), ("ரூபம்", "வடசொல்", ""),
    ("சுகம்", "வடசொல்", ""), ("துக்கம்", "வடசொல்", ""), ("மனிதன்", "வடசொல்", "Skt manuṣya"),
    ("சமுத்திரம்", "வடசொல்", ""), ("வித்தை", "வடசொல்", ""),

    # --- English loans ----------------------------------------------------------------------
    ("பஸ்", "loanword", "English bus"),
    ("கார்", "இயற்சொல்", "HOMOGRAPH, ruled 2026-08-05: native கார் (blackness/monsoon, "
              "dra-pro *kār) LEADS over English car. Was expected `loanword`. The English sense "
              "is cited under origin.senses[] and hands back மகிழுந்து/சீருந்து/தானுந்து."),
    ("ரயில்", "loanword", "English rail"), ("ஸ்கூல்", "loanword", "English school"),
    ("ஹோட்டல்", "loanword", "English hotel"), ("காபி", "loanword", "English coffee"),
    ("டீ", "loanword", "English tea"), ("சைக்கிள்", "loanword", "English cycle"),
    ("லாரி", "loanword", "English lorry"), ("டிக்கெட்", "loanword", "English ticket"),
    ("கம்ப்யூட்டர்", "loanword", "English computer"), ("போன்", "loanword", "English phone"),
    ("ரேடியோ", "loanword", "English radio"), ("பேங்க்", "loanword", "English bank"),
    ("ஆபீஸ்", "loanword", "English office"), ("டாக்டர்", "loanword", "English doctor"),
    ("நர்ஸ்", "loanword", "English nurse"), ("பென்சில்", "loanword", "English pencil"),
    ("பட்டன்", "loanword", "English button"), ("ஸ்டேஷன்", "loanword", "English station"),
    ("பேப்பர்", "loanword", "English paper"), ("கிளாஸ்", "loanword", "English class/glass"),
    ("ஹாஸ்பிட்டல்", "loanword", "English hospital"),

    # --- Portuguese loans (the trap: NOT Sanskrit, but often Grantha-spelled) ----------------
    ("ஜன்னல்", "loanword", "Portuguese janela"),
    ("அலமாரி", "loanword", "Portuguese armário"),
    ("மேசை", "loanword", "Portuguese mesa"),
    ("சாவி", "loanword", "Portuguese chave"),
    ("துவாய்", "loanword", "Portuguese toalha"),
    ("கோப்பை", "?", "disputed — possibly Portuguese copa"),

    # --- Urdu / Persian / Arabic loans -------------------------------------------------------
    ("வக்கீல்", "loanword", "Arabic/Urdu wakīl"),
    ("ஜாமீன்", "loanword", "Urdu zamānat"),
    ("கடிதம்", "?", "disputed"),
    ("சர்க்கார்", "loanword", "Persian sarkār"),
    ("தபால்", "loanword", "Persian/Urdu ḍāk-pāl"),
    ("ஜில்லா", "loanword", "Urdu zila"),

    # --- verbs (base forms) ------------------------------------------------------------------
    ("வா", "இயற்சொல்", ""), ("போ", "இயற்சொல்", ""), ("செய்", "இயற்சொல்", ""),
    ("உண்", "இயற்சொல்", ""), ("பார்", "இயற்சொல்", ""), ("நட", "இயற்சொல்", ""),
    ("படி", "இயற்சொல்", ""), ("எழுது", "இயற்சொல்", ""), ("கொடு", "இயற்சொல்", ""),
    ("ஓடு", "இயற்சொல்", ""),
]

# Forms the பகுபத decoder deliberately does NOT own. Saran's ruling 2026-08-08: a split that turns
# on a சாரியை/உருபு புணர்ச்சி belongs to the புணர்ச்சி engine, so these are reported separately and
# excluded from the in-scope denominator rather than counted as decoder failures.
PUNARCHI_SCOPE = {"வீட்டிற்கு"}

# Inflected forms for the formation sweep — everyday shapes a real user types.
FORMS = [
    "வந்தான்", "வருகிறான்", "வருவான்", "வந்தனன்", "வந்தார்கள்", "வந்தீர்கள்",
    "படித்தான்", "படிக்கிறான்", "படிப்பான்", "நடந்தன", "வாழ்க", "செய்வித்தான்",
    "மரத்தில்", "மரத்தை", "மரங்கள்", "வீட்டில்", "வீட்டிற்கு", "கையால்",
    "கொடுத்தான்", "கொடுக்கிறான்", "கொடுப்பான்", "கொடுக்க", "கொடுத்து", "கொடுக்கும்",
    "போனான்", "சொன்னான்", "தூங்கினான்", "எழுதினான்", "ஓடினான்", "பார்த்தான்",
]


async def main():
    # MUST use default_engine(): a hand-built Engine omits morph_fallback=VerbParadigmAdapter(),
    # which is what covers irregular verbs (போனான், சொன்னான், கொடுத்தான்). Building the engine by
    # hand made 12 covered words look like FST gaps.
    eng = default_engine()

    print("=" * 100)
    print("ORIGIN SWEEP")
    print("=" * 100)
    confident_wrong, unknowns, ok, arguable, homographs = [], [], [], [], []
    for word, exp, note in WORDS:
        a = await eng.analyze(word, word, include=["origin"])
        o = a.origin
        got, conf = (o.class_ if o else "?"), (o.confidence if o else 0.0)
        if o is not None and o.senses:
            homographs.append((word, got, o.senses))
        if exp == "?":
            arguable.append((word, got, conf, note))
        elif got == "unknown":
            unknowns.append((word, exp, conf, note))
        elif got == exp:
            ok.append((word, got, conf))
        else:
            confident_wrong.append((word, exp, got, conf, note))

    print(f"\ncorrect            : {len(ok):3}/{len(WORDS)}")
    print(f"honest unknown     : {len(unknowns):3}  (design rule working, not an error)")
    print(f"WRONG              : {len(confident_wrong):3}")
    print(f"my label uncertain : {len(arguable):3}")

    print("\n--- WRONG, ordered by confidence (the release blocker) ---")
    for w, exp, got, conf, note in sorted(confident_wrong, key=lambda r: -r[3]):
        flag = "‼️ " if conf >= 0.8 else "   "
        print(f"{flag}{w:<16} expected {exp:<10} got {got:<10} conf {conf:.2f}   {note}")

    print("\n--- honest unknown (not errors, but coverage) ---")
    print("   " + ", ".join(w for w, *_ in unknowns))

    print("\n--- my label uncertain, for Saran ---")
    for w, got, conf, note in arguable:
        print(f"   {w:<16} got {got:<10} conf {conf:.2f}   {note}")

    # D-015 / Session 3: origin is per-SENSE. A homograph is not a coverage gap — it is a headword
    # carrying more than one word. These used to be reported as bare `unknown`.
    print("\n--- HOMOGRAPHS: per-sense origin (headword leads with the Tamil sense) ---")
    if not homographs:
        print("   none")
    for word, got, senses in homographs:
        print(f"   {word:<16} headword {got}")
        for sn in senses:
            eq = ", ".join(c.equivalent for c in sn.tamil_alternatives)
            print(f"       {str(sn.sense):<34} {sn.class_:<10} {sn.evidence}")
            if eq:
                print(f"       {'':<34} {'':<10} → Tamil alternatives for this sense: {eq}")

    print("\n" + "=" * 100)
    print("FORMATION SWEEP")
    print("=" * 100)
    gaps, decoded = [], []
    for word in FORMS:
        a = await eng.analyze(word, word, include=["formation"])
        comps = a.formation.components if a.formation else []
        if not comps or len(comps) == 1:
            gaps.append(word)
        else:
            decoded.append((word, " + ".join(f"{c.form}({c.part})" for c in comps)))

    # Saran's ruling 2026-08-08: forms whose split turns on a சாரியை/உருபு புணர்ச்சி (வீட்டிற்கு)
    # belong to the **புணர்ச்சி engine**, not to பகுபத உறுப்பிலக்கணம். They are not decoder gaps, so
    # counting them as failures made this metric measure something it does not claim to measure.
    out_of_scope = [w for w in gaps if w in PUNARCHI_SCOPE]
    real_gaps = [w for w in gaps if w not in PUNARCHI_SCOPE]
    in_scope = len(FORMS) - len(out_of_scope)
    print(f"\ndecoded: {len(decoded)}/{in_scope} in-scope   "
          f"no-analysis gaps: {len(real_gaps)}   "
          f"out of scope (புணர்ச்சி engine): {len(out_of_scope)}\n")
    for w, s in decoded:
        print(f"   {w:<16} {s}")
    if real_gaps:
        print("\n--- NO ANALYSIS (genuine coverage gap) ---")
        print("   " + ", ".join(real_gaps))
    if out_of_scope:
        print("\n--- OUT OF SCOPE for பகுபத உறுப்பிலக்கணம் (புணர்ச்சி engine owns these) ---")
        print("   " + ", ".join(out_of_scope))


asyncio.run(main())
