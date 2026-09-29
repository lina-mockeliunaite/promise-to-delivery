import json
import anthropic

DEAL = "data/harbour_bank"   # never data/coral_pay before 14 Oct

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY

# 1. Read every document in manifest order, labelled with its source ID
manifest = json.load(open(f"{DEAL}/docs/manifest.json"))
parts = []
for doc in manifest["documents"]:
    text = open(f"{DEAL}/docs/{doc['file']}").read()
    parts.append(f"=== {doc['source_id']} ({doc['doc_type']}, {doc['date']}) ===\n{text}")
documents = "\n\n".join(parts)

catalogue = open("data/catalogue.json").read()

# 2. The task: write this yourself, 3-5 lines
task = """Review this deal's paperwork before signature.
Find customer-facing promises that go beyond Elva's catalogue or approved scope, and firm, specific promises that are missing or changed in the draft agreement without being explicitly withdrawn.
For each problem, give the exact quote, its source ID, and why the supplied evidence makes it a problem."""

# 3. One call, everything in one prompt
response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=8000,
    messages=[{"role": "user",
               "content": f"{task}\n\nCATALOGUE:\n{catalogue}\n\nDOCUMENTS:\n{documents}"}],
)

answer = "".join(b.text for b in response.content if b.type == "text")
print(answer)
print(response.stop_reason, response.usage)
open("results/baseline_harbour_bank.md", "w").write(answer)