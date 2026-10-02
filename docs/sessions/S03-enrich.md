# S03: Web lookup and fact enrichment
Read: docs/MAP-02 (cascade method 4, enrichment).
Build:
- Search client (Brave Search API or SerpAPI; key from env) with per-run cap.
- Fetch only result pages returned by search (max 5 per project), respect robots.txt, cache pages.
- LLM extraction (Claude API) to a strict JSON schema: address, landmark, towers, floors, units, possession, bhk_mix, size_range, each with quote-free evidence span and URL. Reject values without evidence.
- Geocode extracted address (LocationIQ/OpenCage) → candidate location with confidence medium.
- Write project_fact rows; never overwrite RERA fields.
- RERA document PDFs: extract floors from sanctioned plan / form text where available (priority over web).
Done when: SBR Horizon facts load with sources; run report shows cost and hit rate.
