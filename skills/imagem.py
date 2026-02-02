import os
from typing import Optional

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

def converter_imagem(caminho_entrada: str, formato_saida: str = "png", redimensionar_fator: float = 1.0) -> str:
    """
    Converte uma imagem para outro formato e opcionalmente a redimensiona.

    Args:
        caminho_entrada (str): O caminho para o arquivo de imagem original.
        formato_saida (str, optional): A extensão/formato desejado para a nova imagem (ex: 'png', 'jpg', 'webp'). 
                                       Padrão é "png".
        redimensionar_fator (float, optional): Fator de escala. 1.0 mantém o tamanho original.
                                               0.5 reduz pela metade, 2.0 dobra o tamanho. Padrão é 1.0.

    Returns:
        str: O caminho absoluto do arquivo recém-criado, ou uma mensagem de erro caso falhe.
    """
    if not _HAS_PIL:
        return (
            "Erro: A biblioteca 'Pillow' não está instalada. "
            "Por favor, instale-a executando: pip install Pillow"
        )

    if not os.path.exists(caminho_entrada):
        return f"Erro: Arquivo de entrada não encontrado: {caminho_entrada}"

    try:
        # Normaliza o formato de saída (remove ponto se houver)
        ext = formato_saida.lower().replace('.', '')
        
        # Define o nome do arquivo de saída
        base_name = os.path.splitext(caminho_entrada)[0]
        caminho_saida = f"{base_name}_convertido.{ext}"

        with Image.open(caminho_entrada) as img:
            # Converter modo de cor se necessário (ex: RGBA para RGB se salvar como JPEG)
            if ext in ['jpg', 'jpeg'] and img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Redimensionamento
            if redimensionar_fator != 1.0:
                nova_largura = int(img.width * redimensionar_fator)
                nova_altura = int(img.height * redimensionar_fator)
                # Usando LANCZOS para alta qualidade (substituto do ANTIALIAS em versões novas do Pillow)
                img = img.resize((nova_largura, nova_altura), Image.Resampling.LANCZOS)
            
            img.save(caminho_saida)
            
        return os.path.abspath(caminho_saida)

    except Exception as e:
        return f"Erro ao converter imagem: {str(e)}"
