# Learning log

## Day 1 — Friday 25 September 2026

**Learned:** When my code calls the model, it sends a key, a model name and my message, and gets back an envelope of blocks — the model's thinking first, then the text answer. I pay per token for both, including the thinking I never see: about 65 in, 380 out, half a cent per run. The first real output also showed me the prompt decides what the system finds — it ignored "our go-live depends on it", the line that makes the promise risky.

**Stuck on:** Setup took most of the day — Claude Code not found (PATH), a placeholder API key, git not knowing who I was, GitHub refusing passwords. I followed the steps but couldn't yet explain all of them.

**Failure:** I pasted my real API key into the chat and had to revoke it. My script also crashed because it read the thinking block instead of the answer, and then printed nothing because of one stray colon — valid code that silently did the wrong thing.

**Still unclear:** Much of the setup felt too technical; I wouldn't yet know how to fix a PATH problem on my own. I spent time on three rounds of design changes after saying the design was frozen — worth watching tomorrow.
