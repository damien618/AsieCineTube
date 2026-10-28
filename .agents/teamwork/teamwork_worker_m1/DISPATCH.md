## 2026-10-28T16:30:00Z
You are teamwork_worker_m1, the Backend Implementation Worker for AsieCinéTube.
Working directory: /Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/.agents/teamwork/teamwork_worker_m1/
Orchestrator conversation ID: 26e83ea2-1d4b-4b7d-bac9-8e059647d86e

MANDATORY FIRST STEPS:
1. Read /Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/.agents/teamwork/ORIGINAL_REQUEST.md
2. Read /Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/PROJECT.md
3. Read the technical analysis and exact specifications from Explorer 1:
   - /Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/.agents/teamwork/teamwork_explorer_survey_1/analysis.md
   - /Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/.agents/teamwork/teamwork_explorer_survey_1/handoff.md
4. Read reference material at /Users/damienferrion/.gemini/antigravity/brain/d2c9165f-7146-4bfe-9ee6-78622957ed76/implementation_plan.md

MANDATORY INTEGRITY WARNING:
DO NOT CHEAT. All implementations must be genuine. DO NOT hardcode test results, create dummy/facade implementations, or circumvent the intended task. A teamwork_auditor will independently verify your work. Integrity violations WILL be detected and your work WILL be rejected.

EXCLUSIVE FILE OWNERSHIP:
You own `server.py` exclusively. Do NOT modify any other source files (`updater.py`, `app.js`, etc.).

TASKS FOR MILESTONE 1 (Backend Core & Filter Engine):
1. Add `EXCLUDED_CHANNELS` (35 channels listed in Explorer 1's analysis.md).
2. Add `BMOVIE_MARTIAL_ARTS_EXCLUSIONS` (17 terms from analysis.md).
3. Expand `SPAM_EXCLUSION_KEYWORDS` (add short-drama, summary, western clickbait terms).
4. Remove `"ciné nanar"` from `VERIFIED_ASIAN_CHANNELS`.
5. Remove `"wuxia"`, `"shaolin"`, `"kung fu"`, `"kung-fu"` from `AUTHENTIC_ASIAN_MARKERS`.
6. Define `AUTEUR_DIRECTORS_TABLE` with word-bounded regexes (`\b`) covering Korean, Japanese, Chinese/Taiwanese/HK masters and festival/heritage markers.
7. Refactor `is_strictly_asian_movie`:
   - Strip URLs from description (`re.sub(r"https?://\S+", "", desc)`) before scanning short director names.
   - Decode URL-encoded channel handles (`urllib.parse.unquote`).
   - Strict precedence: Immediate Exclusions (Western, Spam, Excluded Channels) -> B-Movie Filter with Auteur/SOONER/KOFA Whitelist Exception -> Asian Authenticity Validation.
8. Update `enrich_movie_fields`:
   - Add `isAuteur: bool` and `auteurLabel: Optional[str]`.
   - Support category `"auteur"`.
9. Update `get_movies` & API endpoints:
   - Handle `category == "auteur"`.
10. Update `SEED_MOVIES`:
   - Replace seed entry #5 (`IgY-P7pO0x4` from Ciné Nanar) with an auteur master classic.
11. Update `save_cached_movies`:
   - Clean `cache_map` through `is_strictly_asian_movie` before writing `cache_movies.json`.
12. Run verification:
   - `python3 -m py_compile server.py`
   - Run verification checks documented in Explorer 1's handoff.

OUTPUT REQUIREMENTS:
- Write `changes.md` with file diffs/summary to `/Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/.agents/teamwork/teamwork_worker_m1/changes.md`.
- Write your 5-component handoff report to `/Users/damienferrion/Documents/AppleDevelopper/AsieCineTube/.agents/teamwork/teamwork_worker_m1/handoff.md`.
- Send a completion message to orchestrator (`26e83ea2-1d4b-4b7d-bac9-8e059647d86e`).
