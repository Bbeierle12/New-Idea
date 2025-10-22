import re

with open(r'glyphx\app\gui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the sections list
old_sections = '''        sections = [
            ("📁 File", "file"),
            ("🏷️ Glyphs", "glyphs"),
            ("💬 Chat", "chat"),
            ("🤖 Agent", "agent"),
            ("\ufffd Terminal", "terminal"),
            ("\ufffd📊 Console", "console"),
            ("⚙️ Settings", "settings"),
            ("📦 Data Archive", "archive"),
        ]'''

new_sections = '''        sections = [
            ("📁 File", "file"),
            ("🏷️ Glyphs", "glyphs"),
            ("💬 AI Chat", "chat"),
            ("💻 Terminal", "terminal"),
            ("📊 Console", "console"),
            ("⚙️ Settings", "settings"),
            ("📦 Data Archive", "archive"),
        ]'''

if old_sections in content:
    content = content.replace(old_sections, new_sections)
    with open(r'glyphx\app\gui.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✅ Successfully updated sidebar sections!")
else:
    print("❌ Could not find the sections list to replace")
    print("Searching for alternative pattern...")
    # Try to find it with regex
    pattern = r'sections = \[\s+\("📁 File", "file"\),.*?\]'
    match = re.search(pattern, content, re.DOTALL)
    if match:
        print(f"Found at position {match.start()}-{match.end()}")
        print(f"Content: {repr(match.group()[:100])}")
    else:
        print("Pattern not found")
