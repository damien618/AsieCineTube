## 2026-10-28T17:11:17Z
You are teamwork_worker_m2, the Harvester & Catalog Purge Worker for Milestone 2.
Working directory: /Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/.agents/teamwork/teamwork_worker_m2/
Orchestrator conversation ID: 26e83ea2-1d4b-4b7d-bac9-8e059647d86e

MANDATORY FIRST STEPS:
1. Read /Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/.agents/teamwork/ORIGINAL_REQUEST.md
2. Read /Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/PROJECT.md
3. Read the technical analysis and exact specifications from Explorer 2:
   - /Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/.agents/teamwork/teamwork_explorer_survey_2/analysis.md
   - /Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/.agents/teamwork/teamwork_explorer_survey_2/handoff.md
4. Read reference material at /Users/damienferrion/.gemini/antigravity/brain/d2c9165f-7146-4bfe-9ee6-78622957ed76/implementation_plan.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE FILE OWNERSHIP:
You own `updater.py`, `cache_movies.json`, and `movies.json` exclusively. Do NOT modify `server.py` or frontend files.

TASKS FOR MILESTONE 2:
1. **Update `SEARCH_QUERIES` in `updater.py`**:
   Replace the 5 obsolete martial arts / generic B-movie queries with the 24 targeted auteur & heritage queries detailed in Explorer 2's analysis.md (Kurosawa, Ozu, Mizoguchi, Kobayashi, Wong Kar-wai, Edward Yang, Hou Hsiao-hsien, Hong Sang-soo, Bong Joon-ho, Lee Chang-dong, Park Chan-wook, Kim Ki-duk, Sooner patrimoine, KOFA classic, etc., with French subtitles / vostfr).
2. **Implement in-memory cache purge in `run_harvest()`**:
   In `updater.py` `run_harvest()`:
   ```python
   # Purge in-memory cache of non-compliant movies using server.is_strictly_asian_movie
   cache_map = {
       vid: m for vid, m in cache_map.items()
       if isinstance(m, dict) and server.is_strictly_asian_movie(
           m.get("title", ""),
           m.get("channelName", ""),
           m.get("description", ""),
           m.get("channelUrl", ""),
       )
   }
   ```
3. **Candidate slice enlargement**:
   Increase enrichment slice from 30 to 60 (`new_candidates[:60]`).
4. **Catalogue purge execution and refresh**:
   Execute the active purge and synchronization so that `cache_movies.json` and `movies.json` are fully purged of all 144 excluded movies/B-movies while preserving 100% of KOFA (>=140) and Sooner (>=50) films, with all movies sorted descending by date on static export.
5. **Execute verification**:
   - `python3 -m py_compile updater.py`
   - Run tests:
     `python3 -m unittest tests.test_tier1_features.TestF6YouTubeHarvesterQueries tests.test_tier1_features.TestF7CatalogPurge tests.test_tier1_features.TestF8KofaAndSoonerPreservation tests.test_tier1_features.TestF9SortByDateDescending`
   - Run catalog purity script from Explorer 2's handoff.

OUTPUT REQUIREMENTS:
- Write `changes.md` to `/Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/.agents/teamwork/teamwork_worker_m2/changes.md`.
- Write your 5-component handoff report to `/Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/.agents/teamwork/teamwork_worker_m2/handoff.md`.
- Send completion message to orchestrator (`26e83ea2-1d4b-4b7d-bac9-8e059647d86e`).
