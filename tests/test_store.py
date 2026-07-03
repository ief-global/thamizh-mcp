import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from thamizh_mcp.store.knowledge import Claim, KnowledgeStore


def test_roundtrip_with_provenance(tmp_path):
    async def go():
        store = KnowledgeStore(tmp_path / "k.sqlite3")
        claim = Claim(field="meaning", value={"senses": [{"gloss_ta": "நூல்"}]},
                      source="Tamil Wiktionary", tier="evolving", retrieved="2026-07-02")
        await store.put_claims("புத்தகம்", [claim])
        got = await store.get_claims("புத்தகம்", "meaning")
        assert len(got) == 1
        c = got[0]
        assert c.value["senses"][0]["gloss_ta"] == "நூல்"
        assert (c.source, c.tier, c.retrieved) == ("Tamil Wiktionary", "evolving", "2026-07-02")
        assert await store.get_claims("மரம்") == []          # miss is empty, not invented
        # upsert, not duplicate
        await store.put_claims("புத்தகம்", [claim])
        assert len(await store.get_claims("புத்தகம்")) == 1
        store.close()
    asyncio.run(go())
