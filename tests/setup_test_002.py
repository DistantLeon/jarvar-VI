# Test Scenario: Hot Reload & Multi-Agent Consistency
# Purpose: Verify that fixing jarvis.py allows the new skill to be used IMMEDIATELY after creation.

inputs = [
    "Crie uma skill chamada 'echo_cli' que recebe um texto e usa 'gemini -p <texto> ola' para retornar um eco. Quero testar a integracao.",
    "Use a skill echo_cli com o texto 'Teste de Echo' e me mostre o resultado.",
    "sair"
]

with open('tests/run_002/input_script.txt', 'w', encoding='utf-8') as f:
    f.write('\n'.join(inputs))
