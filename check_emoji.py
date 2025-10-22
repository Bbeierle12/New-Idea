with open(r'glyphx\app\gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    for i, line in enumerate(lines[58:66], start=59):
        print(f"Line {i}: {repr(line)}")
