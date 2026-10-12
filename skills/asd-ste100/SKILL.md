---
name: asd-ste100
description: "Rewrite or check a long piece of English for our developers to ASD-STE100: an MR description, README, architecture document, runbook, or agent instructions. For a comment, docstring, commit message, or review finding, read references/card.md instead of loading this skill. Exclude user-facing text, public API documentation, and errors or exceptions shown to users."
metadata:
  version: "0.5.0"
---

<!-- Vendored into this repository from an MIT-licensed Claude Code skill, then adapted for
     this workflow. `LICENSE` holds the upstream copyright notice, which this copy
     keeps unchanged as the licence requires. -->

# Simplified Technical English (ASD-STE100)

ASD-STE100 is a controlled-language standard built by the aerospace and defense industry (ASD, the AeroSpace and Defense Industries Association of Europe) to stop maintenance technicians from misreading English instructions. The standard removes the two biggest sources of misreading: words with more than one meaning, and sentences with more than one possible structure.

This repository applies the same discipline to English for its developers and their agents. Use explicit subjects, clear instructions, and consistent terms.

## When to Use This Skill

The rules apply to all English you write or edit for our developers, even one comment.
For short text, read `references/card.md`. It is one page, and it carries the structural rules and the scan checklist.
Load this full skill for a long document, or when the developer asks for a rewrite or a rule table.

- Apply it to code comments, docstrings, MR titles and descriptions, review comments, and commit messages.
- Apply it to architecture documents, plans, READMEs, runbooks, and external documents that our developers read or use.
- Apply it to developer reports, messages, agent instructions, prompts, tool descriptions, and internal logs or errors.

Choose by audience, not by file type or storage location. In files with both audiences, apply the skill only to developer text.
Do not apply it to user-facing text, including creative or marketing copy. Use friendly, clear language for users.
Public API documentation for your product serves users and is excluded.
Exception messages and other errors that users receive or see are also excluded.

### Where This Repository Enforces It

`CLAUDE.md` requires this skill for all English written or edited for our developers. `AGENTS.md` links to that file for Codex.
Claude Code discovers this directory. Codex discovers `.agents/skills/asd-ste100/`, which links to this directory.
Keep the skill, references, examples, and license here so both agents use the same files.

The writing rule does not permit edits to `*.human.md` or `*.legacy.md` files. Follow the repository's ownership restrictions.
Preserve meaning, logic, conditions, identifiers, and behavior when you edit text.

The automated reviewer under `aidev/` also uses these rules. Its existing modes are:

| # | Surface | Who writes it | Where | Mode |
|---|---|---|---|---|
| 1 | Finding `body` | model | `aidev/prompts/phase_*.md` | STE-flavored |
| 2 | Finding `title` | model | `aidev/prompts/phase_*.md` | Strict |
| 3 | Severity chip, "To clear this", rule footer | template | `mr_gitlab_agent._finding_body` | Strict |
| 4 | The five thread-reply labels | template | `mr_gitlab_agent.THREAD_REPLY_LABELS` | Strict |
| 5 | Thread `reason`, posted after a label | model | `aidev/prompts/_partials/thread_verdicts.md` | STE-flavored |
| 6 | Per-phase `summary` | model | `aidev/prompts/_partials/output_contract.md` | STE-flavored |
| 7 | Summary-note boilerplate | template | `mr_gitlab_agent._build_summary_note` | Strict |
| 8 | Replies to an @-mention | model | `aidev/prompts/_partials/conversation.md` | STE-flavored |

The compact form the reviewing model is given is `aidev/prompts/_partials/wording.md`. It carries the structural rules and the modality rule only, because it ships on every phase call. This file is the full standard behind it.

Two rules in that partial are **this repository's, not ASD's**, and are stated as such: the finding title names the problem while the body proposes the fix, and posted text describes the developer's code rather than the reviewer's own machinery. STE itself favours imperatives for procedures.

## Two Modes

Choose a mode from the text type before writing. Keep the choice internal unless the user requests the rule analysis.

**Strict** - procedures, developer-only error messages, tool and function descriptions, inter-agent instructions, and safety text for developers.
Apply every rule below, including the length limits and consistent word meanings. User-facing errors remain excluded.

**STE-flavored** - READMEs, MR descriptions, architecture documents, changelogs, and explanatory comments or docstrings.
Apply the structural rules in full. Treat the lexical rules as advisory, as the official dictionary is not included.
Use Strict mode for instructions within these documents. Neither mode makes skill use optional.

The two modes and the structural/lexical split are the same distinction seen from two directions. The split says which rules this skill can verify without ASD's dictionary; the modes say which of them to enforce for a given kind of text.

## Source and Scope

This skill encodes the **rule categories** of ASD-STE100 Issue 9 (Jan 2025): 53 writing rules across 9 sections covering word choice, grammar, sentence structure, and style, backed by a dictionary of ~900 approved words (one meaning, one part of speech each) and ~1,200 words to avoid with suggested replacements. See `references/writing-rules.md` for the full rule summary and citations.

It does **not** reproduce ASD's ~900-word approved dictionary verbatim. ASD-STE100 is free to obtain, but it is not free to redistribute: Issue 9, page 2 states that "no reproduction or publication of it, in whole or in part, shall be made without the written authority of an officer of ASD," and grants free reproduction rights only to eight listed categories (ASD/AIA/AIAC member associations and their member companies and customers, member-state defence ministries, A4A, airworthiness authorities, and universities and research institutes for educational purposes). The `exchange` repository is in none of them, so the dictionary stays out of it.

Instead, this skill applies the *underlying principle* (pick the plainest, most common word available and use it the same way every time) rather than checking against a fixed word list. When exact ASD-approved wording matters (e.g. actual aircraft maintenance documentation), get the standard and check word-by-word against the real dictionary. Request it from the [official downloads page](https://www.asd-ste100.org/STE_downloads.html) — note that this is a request form that emails you a link, not a direct download.

## Core Rewrite Rules

STE's rules divide into two kinds, and this skill can only fully deliver one of them. **Structural rules** are self-contained: they describe sentence shape, and you can apply them from the description alone. **Lexical rules** are defined entirely by the official ~900-word dictionary, which this skill deliberately does not reproduce (see Source and Scope). Without that dictionary, the lexical rules degrade from a checkable standard into a preference for plain words.

Apply the structural rules with confidence. Apply the lexical rules as a direction of travel, and say so in your output rather than implying dictionary compliance you cannot verify.

### Structural rules — apply these

| Rule | Do | Don't |
|---|---|---|
| Active voice | "The agent deletes the file." | "The file is deleted (by the agent)." — unless the actor is genuinely unknown or irrelevant |
| No phrasal verbs (Rule 9.3) | "Remove the panel." / "Start the job." | "Take off the panel." / "Spin up the job." — a two-word verb has meanings the parts do not predict |
| One instruction per sentence | "Open the file. Read line 3." | "Open the file and read line 3, then check if it matches." |
| Sentence length | ≤20 words for instructions/procedures, ≤25 words for descriptions | Long compound/subordinate-clause sentences |
| No semicolons (Rule 8.1) | Split into separate sentences | Any semicolon at all — STE bans the mark outright, not only as a clause join. (Rule 8.1 permits every other standard punctuation mark; the em dash is *not* banned by STE, though it often signals a sentence that should be split.) |
| Noun clusters | ≤3 words stacked as a noun phrase ("fuel pump valve") | 4+ word noun stacks ("high pressure fuel pump inlet valve assembly") |
| No ellipsis | Keep the subject, verb, and article explicit even if it reads longer | Drop words to save space ("Files not backed up will be lost" → ambiguous which files) |
| Keep modality | "The request **may have** failed." stays "may have" | Promote a hedge to a fact ("The request failed.") or invent a certainty the source did not state |
| Paragraph limits | One topic per paragraph, ≤6 sentences | Multi-topic paragraphs |
| Lists for sequences | Use a numbered or bulleted list for 3+ steps or conditions | Bury a sequence inside one prose sentence |

### Lexical rules — direction of travel only

| Rule | Do | Don't | Why it is weaker here |
|---|---|---|---|
| One word, one meaning | Pick one verb for one action and reuse it every time (e.g. always "check", never mix "check"/"verify"/"confirm" for the same action) | Rotate synonyms for the same idea across a document | Consistency within a document is checkable. Which word is the *approved* one is not, without the dictionary. |
| One part of speech per word | "Apply oil to the valve" (oil = noun) | "Oil the valve" (oil = verb) | Whether "oil" is approved as a noun only is a dictionary fact. Prefer the noun form when both read equally well; do not claim compliance. |
| Verb, not noun (Rule 3.7) | "Analyze the log." | "Perform an analysis of the log." — a noun form of an action makes the sentence longer and hides who acts | Rule 3.7 says "use an **approved** verb to describe an action." Preferring the verb form is safe to apply anywhere; knowing which verb is the approved one needs the dictionary. |
| Domain terms | Keep necessary technical nouns/verbs, but define them once if not common English (STE allows a project-specific glossary beyond its base dictionary) | Use jargon without ever defining it | The glossary allowance is real STE, but the base dictionary it extends is absent. |

### Simple tenses — apply with one exception

STE permits infinitive, imperative, simple present, simple past, simple future, and past participle as adjective. It excludes present perfect and other compound forms: "we received the report", not "we have received the report".

Aircraft manuals never need present perfect, so the exclusion costs the standard nothing. Other text is not always so lucky. "The job has completed" (and its output is available now) and "the job completed" (at some past point) are different statements, and status text frequently needs the first. **Where the compound form carries information the simple form cannot — current relevance, or a hedge as in "may have failed" — keep it and flag the departure.** Elsewhere, follow the rule.

## Scan Checklist

These six habits cover most of what makes machine-written English hard to parse. Each one is mechanical: you can point at the exact word or punctuation mark that breaks the rule, with no judgment call. Scan for all six before you rewrite anything.

1. **Synonym rotation** — the same thing gets several names in one document ("the user", "the customer", "the client"). The reader cannot tell whether they are one thing or three. Fix: pick one name, use it every time.
2. **Hedge stacking** — helper verbs and qualifiers pile up until the sentence asserts nothing ("it is important to note that this may potentially help to improve"). Fix: state the claim, or delete it.
3. **Nominalization** — an action frozen into a noun ("perform an analysis of", "provides assistance to"). Fix: use the verb ("analyze", "helps").
4. **Marketing adjectives** — words that claim quality instead of showing it: seamless, robust, powerful, cutting-edge, effortless, blazing-fast. Fix: delete, or replace with the measurement that earns the claim.
5. **Run-on sentences** — several ideas joined by semicolons or em dashes. Fix: one idea per sentence.
6. **Soft phrasal verbs** — spin up, reach out, dive into, kick off. Fix: use the single plain verb (start, contact, read, begin).

## Process

1. Pick the mode (Strict or STE-flavored). Say which only when the user asked for the rule table — see Output Format.
2. Read the input text once for meaning — do not start rewriting before you understand what it must still say afterward.
3. Walk it sentence by sentence. Flag every rule violation from the Core Rewrite Rules tables and every habit from the Scan Checklist. In STE-flavored mode, flag the lexical rules but do not enforce them.
4. Rewrite each flagged sentence to fix the violation while preserving the original meaning exactly. If a rewrite would drop necessary precision (a safety condition, a scope qualifier, a number), keep the longer phrasing and flag it instead of silently simplifying.
   - **Check modality before you commit to a rewrite.** Hedges ("may", "could", "sometimes", "is likely to") carry the author's confidence, and confidence is content. A shorter sentence that upgrades a hedge to a fact is not a simplification — it is a different claim. This is the most common way a well-intentioned STE rewrite goes wrong, because hedges are exactly what a length cap tempts you to cut.
   - Never add a fact the source did not state. A rewrite that reads better because it supplies a cause, a frequency, or a mechanism has stopped being a rewrite.
5. Output the rewritten text (see Output Format). Keep the mode choice and the rule analysis internal unless the user asked to see them.
6. If the input already complies, say so — do not force changes onto compliant text.

For new text, establish the facts and audience before drafting. Apply the same rules and preservation checks to the draft.
Before delivery or publication, check all new or edited developer text against the Core Rewrite Rules and Scan Checklist.
Include comments, docstrings, and the MR description in this check. Check that user-facing text remains excluded.

## Output Format

**Default: the rewritten text, and nothing else.** Most callers want a result they can paste straight into a tool description, an error string, or a prompt. Print the simplified text on its own. Do not add a preamble about this skill, a mode announcement, a violation count, a summary of what changed, a rule table, or a closing offer to explain further.

This output format applies to text-only rewrite requests. For implementation tasks, complete the requested work and report its result in the required format.
Apply the writing rules to that report when its audience is our developers.

The one permitted addition: if step 4 kept a longer phrasing on purpose, add a single line after the text, prefixed `Kept as-is:`, naming the phrase and the precision that would have been lost. Omit the line when there is nothing to report.

**On request: the rule table.** When the user asks to see the reasoning — "show the diff", "which rules did it break", "explain the changes", "before/after" — output this table instead:

```markdown
| Rule violated | Original | Simplified |
|---|---|---|
| Present perfect tense | "We have received your request." | "We received your request." |
| Noun cluster (4+ words) | "the agent task queue priority handler" | "the handler that sets task-queue priority" |

Mode: Strict. 7 violations found.
```

Follow the table with a one-line note on anything you deliberately did **not** simplify, and why (usually: simplifying would lose required precision).

## Boundaries

**Will:**
- Rewrite ambiguous or dense English into short, single-meaning, active-voice sentences.
- Return the rewritten text alone by default, and name the rules it applied when the user asks.
- Preserve every fact, condition, and scope qualifier in the original.
- Preserve the strength of every hedge, and add no claim the source did not make.
- Suggest a one-line glossary entry for domain terms that must stay.

**Will not:**
- Reproduce ASD's official ~900-word dictionary as if it were memorized verbatim — always treat the official download as the source of truth for exact approved wording.
- Simplify creative, marketing, or persuasive copy where voice and nuance are the point.
- Silently drop a safety condition, exception, or scope qualifier to shorten a sentence — it will flag the trade-off instead.
- Convert "may have failed" into "failed", or "could be caused by X" into "X is the cause" — losing a hedge changes the claim.
- Guarantee an aerospace/defense-grade STE-compliant document; this is a general-purpose clarity tool inspired by STE, not a certified STE authoring tool.
- Make weak content true or useful. STE fixes the *form* of a text, not its substance. A hollow paragraph rewritten under these rules becomes a clean, short, well-punctuated hollow paragraph. If the text has nothing to say, no rewrite fixes that — say so instead of polishing it.
- Shorten past the point of clarity. Cutting words is not the goal; removing ambiguity is. Past a certain point compression starts costing the reader time rather than saving it, so stop when the sentence is unambiguous, not when it is shortest.

## Additional Resources

- **`references/writing-rules.md`** — fuller summary of the 9 rule sections and dictionary structure, with citations to the official standard.
- **`examples/before-after.md`** — worked examples: illustrations of the official STE rules, generic agent-output examples, and real before/after pairs from this repository's merge-request reviewer.
- **`LICENSE`** — the MIT licence of the upstream skill this one was vendored from. Keep it and its copyright line intact in every copy.
