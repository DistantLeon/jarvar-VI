import subprocess

def multi_agent_ping():
    try:
        result = subprocess.run(['gemini', '--version'], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return "Error: 'gemini' command not found. Ensure it is in your system's PATH."
