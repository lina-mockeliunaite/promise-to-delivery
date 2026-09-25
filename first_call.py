import anthropic

client = anthropic.Anthropic() #reads ANTHROPIC_API_KEY

excerpt = """Sales: Yes, the connector will be ready for your October launch.
             Customer: Great, our go live depends on it."""

response = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=500,
    messages=[{
        "role": "user",
        "content": f"List every commitment the vendor makes here, with the exact quote:\n\n{excerpt}",
    }],
)

for block in response.content:
    if block.type=="text":
        print(block.text)

print(response.usage)
