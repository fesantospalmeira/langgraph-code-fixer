
import json
import base64
from dotenv import load_dotenv
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
from langchain_core.messages import AIMessage

load_dotenv()

def limpar_bytes(obj):
    """Varre recursivamente dicionários e listas para converter 'bytes' em Base64."""
    if isinstance(obj, dict):
        return {k: limpar_bytes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [limpar_bytes(v) for v in obj]
    elif isinstance(obj, tuple):
        return tuple(limpar_bytes(v) for v in obj)
    elif isinstance(obj, bytes):
        return base64.b64encode(obj).decode('utf-8')
    return obj

def sanitizador_seguro(obj):
            if isinstance(obj, bytes):
                return base64.b64encode(obj).decode("utf-8")
            return str(obj)

class LangGraphEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("utf-8")
        try:
            return str(obj)
        except Exception:
            return super().default(obj)


def enviar_relatorio_bulldog(relatorio_lista: list):
    """
    Envia o relatório consolidado do Agente Bulldog por e-mail com um template HTML.
    Baseado na estrutura testada e validada do usuário.
    """
    if not relatorio_lista:
        print("Nenhum relatório para enviar.")
        return

    # Usando as suas variáveis de ambiente
    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 465))
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    to_emails = os.getenv("TO_EMAILS", "felipesantos7938@gmail.com").split(",")

    if not email_user or not email_password:
        print("❌ Credenciais de e-mail não configuradas no .env.")
        return

    # Junta o relatório em texto puro para o fallback
    texto_puro = "\n".join(relatorio_lista)
    data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")

    # Define a cor do cabeçalho baseada no conteúdo do relatório
    if any("[CRASH]" in item or "[FALHOU]" in item for item in relatorio_lista):
        cor_status = "#d9534f"  # Vermelho (Teve falhas que precisam da sua atenção)
        texto_status = "Atenção Necessária"
    elif any("[CORRIGIDO]" in item for item in relatorio_lista):
        cor_status = "#5bc0de"  # Azul (O agente trabalhou e corrigiu código)
        texto_status = "Manutenção Realizada"
    else:
        cor_status = "#5cb85c"  # Verde (Tudo saudável)
        texto_status = "Sistemas Saudáveis"

    subject = f"🐶 [{texto_status}] Bulldog: Relatório de Manutenção ETL"

    # Transforma a lista de resultados em linhas HTML com cores
    linhas_html = ""
    for item in relatorio_lista:
        if "[CORRIGIDO]" in item:
            linhas_html += f"<p style='color: #28a745; margin: 5px 0;'>{item}</p>"
        elif "[FALHOU]" in item or "[CRASH]" in item:
            linhas_html += f"<p style='color: #dc3545; margin: 5px 0; font-weight: bold;'>{item}</p>"
        elif "[ALERTA]" in item:
            linhas_html += f"<p style='color: #ffc107; margin: 5px 0;'>{item}</p>"
        else:
            linhas_html += f"<p style='color: #6c757d; margin: 5px 0;'>{item}</p>"

    html_content = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #f4f4f9; padding: 20px; color: #333;">
        <div style="max-width: 700px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
          
          <div style="background-color: {cor_status}; color: white; padding: 20px; text-align: center;">
            <h2 style="margin: 0; font-size: 22px;">🐶 Relatório do Agente Bulldog</h2>
            <p style="margin: 5px 0 0 0; font-size: 14px;">Orquestrador de Manutenção Autônoma</p>
          </div>
          
          <div style="padding: 30px;">
            <p style="font-size: 16px;">A ronda pelas pastas de ETL foi finalizada em <strong>{data_atual}</strong>. Abaixo está o resumo das ações tomadas pela IA:</p>
            
            <div style="background-color: #f8f9fa; border-left: 4px solid {cor_status}; padding: 15px; margin-top: 20px; font-size: 14px; line-height: 1.6;">
              {linhas_html}
            </div>
            
            <p style="margin-top: 30px; font-size: 14px; color: #555;">
              As manutenções bem-sucedidas já foram aplicadas nos arquivos de origem e validadas por testes unitários locais. O histórico completo está guardado no BigQuery.
            </p>
          </div>
          
          <div style="background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #999; border-top: 1px solid #eee;">
            <p style="margin: 0;">Este é um e-mail automático gerado pelo Agente Gemini (LangGraph).</p>
          </div>
          
        </div>
      </body>
    </html>
    """

    msg = EmailMessage()
    msg["From"] = email_user
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    
    msg.set_content(f"O Bulldog finalizou a ronda.\n\nResumo:\n{texto_puro}") # Fallback de texto
    msg.add_alternative(html_content, subtype='html')

    try:
        # A sua ligação de sucesso, utilizando SMTP_SSL diretamente na porta correta (465)
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
            smtp.login(email_user, email_password)
            smtp.send_message(msg)

        print(f"📧 E-mail do Bulldog enviado com sucesso para: {', '.join(to_emails)}")

    except Exception as e:
        print(f"❌ Falha crítica ao enviar o log do Bulldog por e-mail: {e}")


# Supondo que result_raw seja a sua variável do tipo AIMessage

def extrair_texto_da_mensagem(mensagem:AIMessage) -> str:
    """Extrai o texto de um AIMessage, independentemente de ser string ou lista."""
    conteudo = mensagem.content
    
    # Se já for uma string (comportamento padrão de alguns modelos)
    if isinstance(conteudo, str):
        return conteudo
        
    # Se for uma lista de blocos (como no seu caso com o Gemini)
    elif isinstance(conteudo, list):
        for bloco in conteudo:
            # Verifica se o bloco é um dicionário e se é do tipo 'text'
            if isinstance(bloco, dict) and bloco.get("type") == "text":
                return bloco.get("text", "")
    
    return "" # Retorno de segurança caso não encontre nada