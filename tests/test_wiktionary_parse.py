"""Gloss extraction across the entry styles seen on ta.wiktionary."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from thamizh_mcp.adapters.wiktionary import extract_glosses

EN_STYLE = """==தமிழ்==
===பெயர்ச்சொல்===
# [[நூல்]]; எழுதப்பட்ட ஏடுகளின் தொகுப்பு
#: உதாரண வாக்கியம் — skipped
# {{த}} அச்சிடப்பட்ட வெளியீடு
"""

PORUL_HEADING_STYLE = """==தமிழ்==
'''புத்தகம்'''
===பொருள்===
* [[நூல்]]
* ஏடுகளின் தொகுப்பு
===மொழிபெயர்ப்பு===
* English: book   <!-- outside பொருள் — must NOT become a sense -->
"""

PORUL_DT_STYLE = """;பொருள்
: நூல், ஏடு
;தொடர்புடைய சொற்கள்
: நூலகம்   <!-- outside பொருள் -->
"""


def test_hash_lines_taken_examples_skipped():
    g = extract_glosses(EN_STYLE)
    assert g[0].startswith("நூல்") and len(g) == 2
    assert not any("உதாரண" in x for x in g)


def test_bullets_only_inside_porul_section():
    g = extract_glosses(PORUL_HEADING_STYLE)
    assert g == ["நூல்", "ஏடுகளின் தொகுப்பு"]      # translation bullet excluded


def test_definition_list_style():
    g = extract_glosses(PORUL_DT_STYLE)
    assert g == ["நூல், ஏடு"]                       # related-words line excluded


def test_no_definitions_is_empty():
    assert extract_glosses("== வார்ப்புரு ==\nவெறும் உரை\n") == []


# Real ta.wiktionary page for புத்தகம், captured 2026-07-03 from Saran's server (template style).
REAL_PUTHAGAM = """{{ஒலிப்பு}}{{audio|ta-{{PAGENAME}}.ogg|[[File:Flag of India.svg|24px]]}}
{{படம்|File:Books 10.jpg|ta}}
{{பொருள்}}
'''{{PAGENAME}}'''
:* [[நூல்]], [[பனுவல்]].
:* [[பொத்தகம்]] என்ற தமிழ்ச் சொல்லின் திரிபு.
*[[book]]'''([[ஆங்கிலம்|ஆங்]])
{{விளக்கம்}}([[வாக்கியம்|வாக்கியப் பயன்பாடு]])
::* இந்த நூல் மிகவும் பயனுள்ளது (This book is usefull)
([[இலக்கியம்|இலக்கியப் பயன்பாடு]]) -
::* நல்ல நூல்கள், நல்ல நண்பன் - [[பழமொழி]] (Good books, good friend - proverb)
{{சொல்வளம்7|நூல்|பனுவல்|ஏடு|சுவடி|#|#|#}}
[[பகுப்பு:கருவச் சொற்கள்]]
[[பகுப்பு:பெயர்ச்சொற்கள்]]"""


def test_real_puthagam_template_style():
    g = extract_glosses(REAL_PUTHAGAM)
    assert g == ["நூல், பனுவல்", "பொத்தகம் என்ற தமிழ்ச் சொல்லின் திரிபு"]
    joined = " ".join(g)
    assert "book" not in joined          # English translation line excluded
    assert "இந்த நூல்" not in joined      # example sentences (after {{விளக்கம்}}) excluded
