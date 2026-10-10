# Decision memo: does agent v2 run on Coral Pay? (due before the 12 Oct freeze)

*Prepared by Claude on 9 Oct for Lina to decide. Facts from DECISIONS.md (3 Oct, 12:24 and afternoon) and `config.py`. The choice is yours; nothing has been changed.*

## Where it stands

- **v1 result (3 Oct, pre-registered rule):** rules power the demo. The agent read all 5 paraphrased approval issues correctly *in substance*, but every verdict failed the evidence contract (condition 2), in all 6 runs. Cost and latency were inside bounds.
- **Part of that failure was the interface, not the model:** the tool schema didn't name the allowed term labels or require a phrase for the capability. **v2** (`AGENT_VERSION = 2`) fixes the schema. It has **never run with the real model** — only scripted fakes.
- The practice set is now seen, so re-running v2 on it would be tuning to the test (you rejected that on 3 Oct).
- The plan's headline result is "baseline vs rules vs agent" on Coral Pay, one run each.

## Options

| | What | For | Against | Cost |
| --- | --- | --- | --- | --- |
| **A** | Rules only on Coral Pay; agent reported from the practice set | Simplest; nothing untested touches the sealed set | The headline loses its third column; "where does the AI come in?" gets a weaker answer | $0 extra |
| **B** | Run agent v2 once on Coral Pay, rule unchanged | Matches the plan; a pre-registered result is honest whichever way it goes | The sealed run becomes v2's first real-model run, so a crash or interface bug would waste the one shot | ~$0.10 |
| **C** | Smoke-test v2 with the real model on Harbour Bank and hard cases first (one escalated commitment each, already seen, results not scored for the decision), then B | Catches crashes and interface bugs without tuning on anything; keeps the plan's headline | Development data barely exercises v2 (2 escalations); it proves it *runs*, not that it *works* | ~$0.02 + B |
| **D** | Write a fresh unseen practice deal, label it, validate v2 there, then decide | The scientifically clean answer | 2–3 hours of your labelling before 12 Oct, on top of the Part B and layout reviews; scope risk | ~$0.10 + your time |

## Claude's read (stress-test it)

**C is the strongest balance**: it protects the one sealed run from a silly failure for about two cents, without pretending the smoke test is evidence. The decision rule stays exactly as written on 4 Oct. The README should say v2 was smoke-tested only.

The case against C: if you're short on time, **A is perfectly defensible** and arguably easier to explain to a business audience ("the model reads; rules decide; here's why the agent didn't earn a place"). What isn't defensible is B without the smoke test, or changing anything about v2 after seeing Coral Pay.

## To record whichever you pick (DECISIONS.md, before the 12 Oct close)

Chose · rejected · why · the exact configuration that runs on 14 Oct (`AGENT_VERSION`, model, bounds from `config.py`) · that the decision rule is unchanged.
