# Relatório Técnico: Refatoração da Comunicação via Subprocess (v3.9.1)

**Data:** 2026-02-03
**Componente:** `skills/cerebro.py` (Interface Hand-Brain)
**Contexto:** O projeto utiliza o `gemini` CLI como motor de inteligência isolado ("Brain"), invocado pelo script Python `jarvis.py` ("Hand").

---

## 1. O Problema: "Shell Pipes" e `shell=True`

### Código Original (Fragilidade)
```python
# Abordagem v3.9.0 e anteriores
cmd = f"type {log_path_safe} | gemini" # Windows
# ou
cmd = f"cat {log_path_safe} | gemini" # Linux

proc = subprocess.Popen(cmd, shell=True, stdout=PIPE, ...)
```

### Por que era frágil?
Esta abordagem dependia do shell do sistema operacional (`cmd.exe` ou `/bin/sh`) para criar um "pipe" (`|`) que conectava a saída de um comando (`type`/`cat`) à entrada do `gemini`.

1.  **Dependência de OS:** Exigia lógica condicional (`if os.name == 'nt'`) para escolher entre `type` e `cat`.
2.  **Codificação de Texto (Encoding Hell):**
    *   No Windows, o comando `type` e o próprio pipe do PowerShell/CMD muitas vezes operam em `cp1252` (padrão local), enquanto o Python e o Gemini esperam `utf-8`. Isso causava corrupção de caracteres especiais (acentos, emojis) antes mesmo de chegarem ao Brain.
3.  **Limite de Caracteres do Shell:**
    *   O `cmd.exe` no Windows tem um limite rígido de ~8191 caracteres para a linha de comando. Prompts longos (com contexto de arquivos ou memória) causavam o erro silencioso ou crash do comando.
4.  **Risco de Injeção:**
    *   O uso de `shell=True` é inerentemente perigoso. Se o caminho do arquivo de log contivesse caracteres não tratados (apesar das aspas), poderia haver execução arbitrária de código.
5.  **Performance:**
    *   Criar dois processos (`type` + `gemini`) e um shell intermediário é mais pesado do que invocar o alvo diretamente.

---

## 2. A Tentativa Falha: Substituição por SDK

Em uma tentativa inicial de otimização, tentei remover o CLI e usar a biblioteca `google.genai` diretamente.

**Por que foi rejeitado?**
*   **Violação Arquitetural:** O projeto define explicitamente `Brain-CLI` como componente core.
*   **Perda de Multi-Agente:** O CLI é um processo independente. Manter essa arquitetura facilita escalar para múltiplos agentes rodando em containers ou máquinas diferentes, comunicando-se via STDIN/STDOUT padrão do sistema (princípio UNIX), ao invés de acoplar tudo numa única runtime Python.

---

## 3. A Solução: `stdin` Programático

### Código Novo (Robustez)
```python
# Abordagem v3.9.1
proc = subprocess.Popen(
    ["gemini"],          # Executável direto
    stdin=subprocess.PIPE, # Canal de entrada direto na memória
    stdout=subprocess.PIPE,
    text=True,
    encoding="utf-8"     # Força UTF-8 no canal
)

# Envia o prompt DIRETAMENTE para o processo, sem passar pelo shell
stdout, stderr = proc.communicate(input=sys_inst)
```

### Vantagens Técnicas
1.  **Agnóstico de Sistema Operacional:** Não importa se é Windows, Linux ou Mac. O Python gerencia a criação do processo.
2.  **Sem Limite de Tamanho:** O prompt é passado via stream de memória (STDIN), não como argumento de linha de comando. O limite agora é apenas a RAM e a janela de contexto do LLM.
3.  **Encoding Garantido:** Definimos explicitamente `encoding='utf-8'` na criação do Popen. O Python faz a ponte correta bytes <-> texto.
4.  **Segurança (Shell=False):** Removemos `shell=True`. O sistema operacional executa apenas o binário `gemini`, sem interpretar metacaracteres perigosos.
5.  **Preservação da Arquitetura:** Mantém o Gemini CLI como o "cérebro" independente, respeitando a documentação do projeto, mas invocando-o de maneira profissional e estável.

---

## 4. Conclusão
A refatoração transformou uma "gambiarra" de shell script (que funcionava por sorte em cenários simples) em uma integração de sistemas robusta. O CLI agora é tratado como um **microsserviço local**, recebendo payloads via STDIN e respondendo via STDOUT, garantindo a fundação para os futuros sistemas multi-agente do Jarvis.
