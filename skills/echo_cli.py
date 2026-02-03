
def echo_cli(texto: str) -> dict:
    """Ecoes via CLI Gemini."""
    import subprocess
    try:
        resultado = subprocess.run(['gemini', '-p', texto, 'ola'], capture_output=True, text=True, check=True)
        return {'output': resultado.stdout, 'error': resultado.stderr}
    except subprocess.CalledProcessError as e:
        return {'error': str(e)}
