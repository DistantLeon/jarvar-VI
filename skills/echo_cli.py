import os
import subprocess

def echo_cli(texto: str) -> dict:
    """Echos texto via gemini CLI."""
    try:
        command = ['gemini']
        if os.name == 'nt':
            command = ['gemini.cmd']
        prompt = f"{texto} ola"
        resultado = subprocess.run(
            command + ['-p', prompt],
            capture_output=True,
            text=True
        )
        return {
            'exit_code': resultado.returncode,
            'output': resultado.stdout,
            'error': resultado.stderr
        }
    except subprocess.CalledProcessError as e:
        return {'error': str(e)}
