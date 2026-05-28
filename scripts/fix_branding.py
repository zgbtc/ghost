"""Fix all remaining Hermes branding -> Ghost in skin_engine.py"""
import pathlib
import re

target = pathlib.Path(__file__).parent.parent / "hermes_cli" / "skin_engine.py"
content = target.read_text(encoding="utf-8")

before = content

# All variants of response_label with Hermes
content = re.sub(r'"response_label":\s*"[^"]*Hermes[^"]*"', '"response_label": " \U0001f47b Ghost "', content)

# All variants of agent_name with Hermes
content = re.sub(r'"agent_name":\s*"Hermes Agent"', '"agent_name": "Ghost"', content)

# All variants of welcome with Hermes
content = re.sub(
    r'"welcome":\s*"Welcome to Hermes Agent! Type your message or /help for commands\."',
    '"welcome": "Welcome to Ghost! Type your message or /help for commands."',
    content
)

# All variants of goodbye with Hermes symbol
content = re.sub(r'"goodbye":\s*"Goodbye! [^\"]+"', '"goodbye": "Goodbye! \U0001f47b"', content)

changed = sum(1 for a, b in zip(before, content) if a != b)
print(f"Changed {changed} characters")
target.write_text(content, encoding="utf-8")

# Verify
remaining = re.findall(r'"[^"]*Hermes[^"]*"', content)
# Filter out non-branding ones
branding_remaining = [r for r in remaining if any(k in r for k in ['agent_name', 'response_label', 'welcome', 'goodbye'])]
if branding_remaining:
    print("Still remaining:", branding_remaining)
else:
    print("All branding replaced successfully!")
