# Owner decision after the reproduction comparison

On 24 October 2026, after the experiment closed, the owner asked to keep the fix if it corrected
the known missed reproduction request without making the tested outcomes worse. The exact tested
candidate is now installed as `.claude/skills/issue-triage/SKILL.md`. Its SHA-256 is
`8d46cb101c8d4ee3c0085ec84eef4056dc2c2af8809e2a950de644947c3b3139`.
The baseline was commit `962fac774c7845bca0da2d310ca1bdcca09c50ea`.

Only the reproduction procedure changed. It asks whether the supplied code can reach the
reported failure, rather than treating multiline fragments as complete examples. It still
accepts short runnable examples and keeps the existing skip and suppression rules. Runtime
scripts, component hints, linking instructions, workflow permissions and output limits are
unchanged. The earlier broad linking/label candidate was not adopted.

## Evidence supporting this decision

The separate known case, `e51957`, now proposes both `blocked/need-repro` and `need-repro` and
passes its original expectation. Its [transcript](known-regression/transcript.md) and
[result](known-regression/result.json) preserve the single first decision. It was a known
failure used to develop the change, so it is excluded from fresh-case metrics.

The fresh comparison contains 18 historical Q2 cases and 12 constructed controls, run twice
per policy: 120 decisions, or 60 paired comparisons. No candidate pair has higher scored cost,
a lost case pass or a new safety failure. There are 59 cost ties and one improvement. The
historical pass counts are 17/18 versus 18/18 in repetition 1 and 17/18 versus 17/18 in repetition
2; constructed passes are 11/12 for both policies in both repetitions.

Both policies make every required and forbidden reproduction decision correctly on the fresh
cases. The one scored gain is a component label on `e51950`, seen in only one repetition.
It does not establish that the reproduction wording caused a general accuracy gain.
The shared constructed failure is an extra transparency label; the independent reviewer
considered it defensible, but its frozen expectation and failing score remain unchanged.

The [independent follow-up review](evidence/revised-criterion-review.md) checks all 60 pairs
and the changed actions against the revised criterion. Accepted optional actions still differ:
some candidate outputs omit an extra component label, and one adds a relevant earlier link.
The evidence supports "no observed scored regression on these cases." It cannot guarantee
that the change will never make another decision worse or that every optional choice is better.

## Why the original experiment still says rejected

The original protocol required strictly fewer constructed reproduction omissions and lower
constructed cost in each repetition, plus full passes on positive controls. Six gates failed.
The unchanged [score report](evidence/score.json) therefore still has `accepted: false`.
The original [README](README.md), [blind review](evidence/blind-review.md) and
[final disposition](evidence/final-disposition.json) describe the decision at experiment close,
before this later owner instruction. Their statements that no adoption, commit or push had
occurred are historical. This new record documents the subsequent decision without rewriting
the original criteria or presenting the experiment as a predeclared success.

The owner selected the narrower criterion after seeing the results. No expectations were
changed, no first decisions were replaced, and no additional assistant trials were run for
this adoption. The earlier linking comparison, golden results, failure logs and both policy
copies remain intact. The verification record in `evidence/adoption-verification.json` and
the offline test log in `evidence/adoption-tests.txt` document final packaging checks.

The archived independent checker verifies the full pre-adoption file inventory. Running it
against the adopted checkout will report the five intentional skill/document changes listed
in the adoption verification record. To repeat that original audit, use a disposable copy
with those five files restored from baseline commit `962fac7` and the preserved experiment
files present. Keep the current checkout and archived checker unchanged.

## Submission limits

The five dry-run failures were later rerun live on the submitted runtime
(`evals/failure-recheck-live-3/`): three passed, at $1.25.
