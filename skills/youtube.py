import json
import logging
from typing import Optional

try:
    import yt_dlp
    _HAS_YTDLP = True
except ImportError:
    _HAS_YTDLP = False

def ler_transcricao_youtube(url_video: str) -> str:
    """
    Baixa e retorna a transcrição completa (legendas) de um vídeo do YouTube usando yt-dlp.
    Prioriza legendas em Português, depois Inglês. Suporta legendas automáticas.

    Args:
        url_video (str): A URL completa do vídeo do YouTube.

    Returns:
        str: O texto completo da transcrição ou mensagem de erro.
    """
    if not _HAS_YTDLP:
        return "Erro: A biblioteca 'yt-dlp' não está instalada. Execute: pip install yt-dlp"

    # Configuração para não baixar vídeo, apenas metadados e legendas
    ydl_opts = {
        'skip_download': True,
        'writeautomaticsub': True,
        'writesubtitles': True,
        'subtitleslangs': ['pt', 'pt-BR', 'en', 'en-US'],
        'quiet': True,
        'no_warnings': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extrai informações
            info = ydl.extract_info(url_video, download=False)
            
            video_id = info.get('id', 'desconhecido')
            title = info.get('title', 'Sem título')
            
            # Procura legendas disponíveis
            subtitles = info.get('subtitles', {})
            auto_subs = info.get('automatic_captions', {})
            
            # Prioridade de idiomas
            langs = ['pt', 'pt-BR', 'en', 'en-US']
            selected_sub_url = None
            
            # Tenta legendas manuais
            for lang in langs:
                if lang in subtitles:
                    # Pega o formato JSON3 ou VTT
                    for fmt in subtitles[lang]:
                        if fmt['ext'] == 'json3':
                            selected_sub_url = fmt['url']
                            break
                    if selected_sub_url: break
            
            # Se não achou, tenta automáticas
            if not selected_sub_url:
                for lang in langs:
                    if lang in auto_subs:
                        for fmt in auto_subs[lang]:
                            if fmt['ext'] == 'json3':
                                selected_sub_url = fmt['url']
                                break
                        if selected_sub_url: break
            
            if not selected_sub_url:
                return f"Erro: Nenhuma legenda (PT/EN) encontrada para o vídeo: {title} (ID: {video_id})"

            # Baixa o conteúdo da legenda
            # Como yt-dlp não baixa direto para string, usamos requests interno ou urllib
            import urllib.request
            
            with urllib.request.urlopen(selected_sub_url) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            # Parseia o JSON3 do YouTube
            full_text = []
            if 'events' in data:
                for event in data['events']:
                    # Alguns eventos são metadados sem 'segs'
                    if 'segs' in event:
                        for seg in event['segs']:
                            text = seg.get('utf8', '').strip()
                            if text and text != '\n':
                                full_text.append(text)
            
            transcript_text = " ".join(full_text)
            
            return (
                f"--- Transcrição: {title} (ID: {video_id}) ---\n\n"
                f"{transcript_text}"
            )

    except Exception as e:
        return f"Erro ao processar vídeo com yt-dlp: {str(e)}"