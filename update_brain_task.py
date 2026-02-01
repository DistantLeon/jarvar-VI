import os
import re

file_path = 'jarvis_v3.3.py'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Define the old code block (regex to capture the entire _brain_task function)
old_code_pattern = re.compile(
    r'( +)def _brain_task\(rid, sys_inst\):\n'
    r'(?:\s+.+?\n)*?(?=\n\n|\Z)',
    re.MULTILINE
)

# Define the replacement code
new_code = """
    def _brain_task(rid, sys_inst):
        temp_file = Path(f"brain_{rid}.txt")
        try:
            full_prompt = f"{sys_inst}\n\nAnalise o objetivo e forneça a solução."
            temp_file.write_text(full_prompt, encoding='utf-8')
            
            # Detecção de SO para escolha do comando correto
            import platform
            sistema = platform.system().lower()
            
            if sistema == "windows":
                # Windows usa 'type' para exibir conteúdo
                cmd = f"type {temp_file} | gemini"
            else:
                # Linux/Unix/Mac usa 'cat'
                cmd = f"cat {temp_file} | gemini"

            proc = subprocess.Popen(
                cmd, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8"
            )
            stdout, stderr = proc.communicate()
            
            if proc.returncode != 0:
                raise RuntimeError(f"Exit {proc.returncode}: {stderr}")
                
            response_text = stdout.strip()
            
            with CEREBROS_LOCK:
                if rid in CEREBROS_ATIVOS:
                    CEREBROS_ATIVOS[rid]["status"] = "completed"
                    CEREBROS_ATIVOS[rid]["response"] = response_text
            print(f"\\n[🧠 BRAIN] Raciocínio {rid} CONCLUÍDO.")
            
        except Exception as e:
            with CEREBROS_LOCK:
                if rid in CEREBROS_ATIVOS:
                    CEREBROS_ATIVOS[rid]["status"] = "error"
                    CEREBROS_ATIVOS[rid]["error"] = str(e)
            print(f"\\n[🧠 BRAIN] Raciocínio {rid} FALHOU: {e}")
        finally:
            if temp_file.exists():
                try: temp_file.unlink()
                except: pass
"""

def replacement(match):
    return new_code

new_content, count = old_code_pattern.subn(replacement, content)

if count > 0:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"✅ Successfully updated {file_path}")
else:
    print(f"❌ Could not find the code block in {file_path}")