import os
import re

file_path = 'jarvis_v3.3.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the old code block (regex to capture whitespace)
old_code_pattern = re.compile(
    r'( +)with open\(temp_file, "r", encoding="utf-8"\) as f:\s+'
    r'\1    # Modificado para usar subprocess e gemini CLI\s+'
    r'\1    proc = subprocess.Popen\(\s+'
    r'\1        "gemini", \s+'
    r'\1        shell=True, \s+'
    r'\1        stdin=f, \s+'
    r'\1        stdout=subprocess.PIPE, \s+'
    r'\1        stderr=subprocess.PIPE,\s+'
    r'\1        text=True,\s+'
    r'\1        encoding=\'utf-8\'\s+'
    r'\1    \)\s+'
    r'\1    stdout, stderr = proc.communicate\(\)',
    re.MULTILINE
)

# Define the replacement code generator
def replacement(match):
    indent = match.group(1)
    return (
        f'{indent}# Modificado para usar pipe via shell conforme OS\n'
        f'{indent}if os.name == "nt":\n'
        f'{indent}    cmd = f"type {{temp_file}} | gemini"\n'
        f'{indent}else:\n'
        f'{indent}    cmd = f"cat {{temp_file}} | gemini"\n'
        f'\n'
        f'{indent}proc = subprocess.Popen(\n'
        f'{indent}    cmd, \n'
        f'{indent}    shell=True, \n'
        f'{indent}    stdout=subprocess.PIPE, \n'
        f'{indent}    stderr=subprocess.PIPE,\n'
        f'{indent}    text=True,\n'
        f'{indent}    encoding="utf-8"\n'
        f'{indent})\n'
        f'{indent}stdout, stderr = proc.communicate()'
    )

new_content, count = old_code_pattern.subn(replacement, content)

if count > 0:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"✅ Successfully updated {file_path}")
else:
    print(f"❌ Could not find the code block in {file_path}")