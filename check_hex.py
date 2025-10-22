with open(r'glyphx\app\gui.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
    
    # Line 63 - Terminal
    line63 = lines[62]
    start = line63.find('"') + 1
    end = line63.find(' Terminal')
    emoji63 = line63[start:end]
    print(f"Terminal emoji: {repr(emoji63)}, bytes: {[hex(ord(c)) for c in emoji63]}")
    
    # Line 64 - Console
    line64 = lines[63]
    start = line64.find('"') + 1
    end = line64.find('📊')
    emoji64_1 = line64[start:end]
    print(f"Console first emoji: {repr(emoji64_1)}, bytes: {[hex(ord(c)) for c in emoji64_1]}")
