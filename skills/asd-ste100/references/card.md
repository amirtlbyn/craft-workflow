# ASD-STE100 card — the one page to read before you write developer English

Apply this to comments, docstrings, commit messages, merge-request text, review
findings, specs, and agent instructions. Do not apply it to user-facing text or
to errors users see. For a long rewrite, load the full `asd-ste100` skill.

## Structural rules — apply all of them

| Rule | Do | Do not |
|---|---|---|
| Active voice | "The service rejects the request." | "The request is rejected." |
| One instruction per sentence | "Open the file. Read line 3." | "Open the file and read line 3, then check it." |
| Sentence length | 20 words or fewer for instructions, 25 for descriptions | Long chains of clauses |
| No semicolons | Two sentences | Any semicolon |
| Noun clusters | 3 words or fewer | "withdrawal limit tier cache key builder" |
| No phrasal verbs | start, remove, contact, read | spin up, take off, reach out, dive into |
| Simple tenses | "The job failed." | "The job has failed." Keep the compound form only when it carries a hedge or current relevance, as in "may have failed" |
| Keep modality | "may have failed" stays "may have failed" | Upgrade a hedge to a fact |
| Lists for sequences | A numbered list for 3 or more steps | A sequence buried in one sentence |

## Scan checklist — six habits to remove

1. **Synonym rotation** — one thing, one name, every time.
2. **Hedge stacking** — "it may potentially help to improve". State it or cut it.
3. **Nominalization** — "perform an analysis of" becomes "analyze".
4. **Marketing adjectives** — seamless, robust, powerful, blazing-fast. Delete,
   or give the number.
5. **Run-on sentences** — one idea per sentence.
6. **Soft phrasal verbs** — spin up, reach out, kick off. Use the plain verb.

## Never

- Never drop a condition, a number, or a scope qualifier to make a sentence shorter.
- Never add a fact the source did not state.
- Never edit a `*.human.md` or `*.legacy.md` file to apply these rules.
