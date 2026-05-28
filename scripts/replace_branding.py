"""Replace Hermes branding with Ghost branding in skin_engine.py"""
import pathlib

target = pathlib.Path(__file__).parent.parent / "hermes_cli" / "skin_engine.py"
content = target.read_text(encoding="utf-8")

replacements = [
    # response_label
    ('" \u2695 Hermes "', '" \U0001f47b Ghost "'),
    # agent_name
    ('"agent_name": "Hermes Agent"', '"agent_name": "Ghost"'),
    # welcome
    ('"welcome": "Welcome to Hermes Agent! Type your message or /help for commands."',
     '"welcome": "Welcome to Ghost! Type your message or /help for commands."'),
    # goodbye
    ('"goodbye": "Goodbye! \u2695"', '"goodbye": "Goodbye! \U0001f47b"'),
    # banner title in format_banner_version_label
    ("Hermes Agent v", "Ghost v"),
    # NOUS HERMES header
    ("\u2695 NOUS HERMES", "\U0001f47b Ghost"),
    ("\u2695 Hermes Agent", "\U0001f47b Ghost"),
]

for old, new in replacements:
    count = content.count(old)
    content = content.replace(old, new)
    print(f"  {count}x  {old!r} -> {new!r}")

target.write_text(content, encoding="utf-8")
print("Done:", target)
