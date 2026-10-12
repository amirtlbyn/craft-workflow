# Adjudication — for the main session, not for reviewers

Reviewers report to you. You report to the developer. Never forward a raw
reviewer transcript.

Verification costs tokens, so spend them where severity is:

1. **Critical and High: verify every one against the code.** Open the cited
   `file:line`. Confirm the failing scenario. Label it `Confirmed` when the code
   proves it, or `Plausible` when it is credible but you could not verify it,
   and say what you could not verify.
2. **Medium and Low: verify only when the cited line is not already in your
   context, or the fix is not obvious.** Otherwise label it `Plausible` and let
   the fix itself be the check.
3. **Drop findings the code contradicts.** Say how many, and why, in one line.
4. Merge duplicates across reviewers. Keep the best-evidenced one and the
   higher severity.
5. Present one ordered list: Critical → High → Medium → Low. One line per
   finding, plus the suggestion for Critical and High.
6. Recompute the decision:
   - **REQUEST_CHANGES** — any open Confirmed Critical or High.
   - **COMMENT** — Medium and Low only.
   - **APPROVE** — no Confirmed Critical or High, and every checklist item of
     every routed lens is answered.
7. Resolve every `unclear` item yourself, or carry it as an open question.
   Never drop one silently.
8. A `Spec delta needed` finding stops the work. Follow the `spec` skill's
   "Spec deltas" section before you fix anything else.

Append the round to `log.md`: the lenses that ran, the counts by severity, the
decision, and each Critical or High with its state.

Record the round as state too, so the status band, the board's Review tab, and
Gate B can read it without parsing `log.md`:

```bash
bin/craft-session record-finding --severity High --lens logic --where apps/wallet/ledger.py:88 \
    --title "The counter is read before the row lock" --state confirmed
bin/craft-session record-review --lenses spec,style,logic,security --decision REQUEST_CHANGES \
    --reviewers reviewer,deep-reviewer
```

One `record-finding` per Critical and High, and per Medium you will fix. After a
fix is verified: `bin/craft-session finding F1 --state fixed`. The developer can
confirm or reject a finding from the board instead, and that writes the same
file.
