def check_js(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    stack = []
    in_str = None
    esc = False
    in_line_comment = False
    in_block_comment = False
    
    for i, c in enumerate(content):
        if in_line_comment:
            if c == '\n': in_line_comment = False
            continue
        if in_block_comment:
            if c == '/' and content[i-1] == '*': in_block_comment = False
            continue
        if in_str:
            if esc:
                esc = False
            elif c == '\\':
                esc = True
            elif c == in_str:
                in_str = None
            continue
        if c == '/' and i+1 < len(content) and content[i+1] == '/':
            in_line_comment = True
            continue
        if c == '/' and i+1 < len(content) and content[i+1] == '*':
            in_block_comment = True
            continue
        if c in ('"', "'", '`'):
            in_str = c
            continue
        if c in '({[':
            stack.append((c, i))
        elif c in ')}]':
            if not stack:
                print(f'Error in {path}: Unmatched closing {c} at index {i}')
                return False
            top, pos = stack.pop()
            matches = {')': '(', '}': '{', ']': '['}
            if matches[c] != top:
                print(f'Error in {path}: Mismatched {top} at {pos} closed by {c} at {i}')
                return False
    if stack:
        print(f'Error in {path}: Unclosed {stack[-1][0]} from index {stack[-1][1]}')
        return False
    print(f'OK: {path} has perfectly balanced syntax!')
    return True

check_js(r'C:\Hecos\hecos\modules\web_ui\static\js\config_audio\ca_core.js')
check_js(r'C:\Hecos\hecos\modules\web_ui\static\js\config_audio\ca_kokoro_inference.js')
check_js(r'C:\Hecos\hecos\modules\web_ui\static\js\config_audio\ca_tts_utils.js')
check_js(r'C:\Hecos\hecos\modules\web_ui\static\js\config_audio\ca_kokoro_clones.js')
