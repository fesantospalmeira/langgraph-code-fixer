import os
import uuid
import smtplib
from email.message import EmailMessage
from datetime import datetime
from dotenv import load_dotenv
from core.graph import build_graph

# Carrega as variáveis do ficheiro .env
load_dotenv()

def enviar_relatorio_bulldog(relatorio_lista: list):
    """Envia o relatório consolidado do Agente Bulldog por e-mail com template HTML."""
    if not relatorio_lista:
        print("Nenhum relatório para enviar.")
        return

    smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", 587))
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    to_emails = os.getenv("TO_EMAILS", "felipesantos7938@gmail.com").split(",")

    if not email_user or not email_password:
        print("❌ Credenciais de e-mail não configuradas no .env.")
        return

    texto_puro = "\n".join(relatorio_lista)
    data_atual = datetime.now().strftime("%d/%m/%Y às %H:%M")

    # Define a cor do cabeçalho baseada no status geral
    if any("[CRASH]" in item or "[FALHOU]" in item for item in relatorio_lista):
        cor_status = "#d9534f"  # Vermelho
        texto_status = "Atenção Necessária"
    elif any("[CORRIGIDO]" in item for item in relatorio_lista):
        cor_status = "#5bc0de"  # Azul
        texto_status = "Manutenção Realizada"
    else:
        cor_status = "#5cb85c"  # Verde
        texto_status = "Sistemas Saudáveis"

    subject = f"🐶 [{texto_status}] Bulldog: Relatório de Manutenção ETL"

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
              As correções bem-sucedidas foram aplicadas automaticamente nos módulos e validadas por testes unitários locais.
            </p>
          </div>
          <div style="background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #999; border-top: 1px solid #eee;">
            <p style="margin: 0;">Relatório gerado automaticamente pelo Agente Gemini (LangGraph).</p>
          </div>
        </div>
      </body>
    </html>
    """

    msg = EmailMessage()
    msg["From"] = email_user
    msg["To"] = ", ".join(to_emails)
    msg["Subject"] = subject
    msg.set_content(f"O Bulldog finalizou a ronda.\n\nResumo:\n{texto_puro}")
    msg.add_alternative(html_content, subtype='html')

    try:
        # Utilizando a porta 587 com TLS explícito
        with smtplib.SMTP(smtp_server, smtp_port) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(email_user, email_password)
            smtp.send_message(msg)

        print(f"📧 E-mail do Bulldog enviado com sucesso para: {', '.join(to_emails)}")
    except Exception as e:
        print(f"❌ Falha crítica ao enviar o e-mail: {e}")

def main():
    print("🐶 Acordando o Bulldog ETL... Iniciando patrulha.")

    # Adicione aqui todas as pastas dos seus ETLs que o Bulldog deve vigiar
    pastas_etl = [
        r"D:\Tree Solution\[ETL] Bom Controle",
        # r"D:\Tree Solution\[ETL] - Checklist_Facil",
        # r"D:\Tree Solution\[ETL] Jappa_Menew",
    ]

    # Inicializa o grafo do LangGraph (já compilado sem checkpointer)
    app = build_graph()
    relatorio = []

    # Pastas e diretórios que devem ser totalmente ignorados na busca recursiva
    pastas_excluidas = {"venv", ".venv", "__pycache__", ".git", "node_modules"}

    for etl_folder in pastas_etl:
        print(f"\n{'=' * 60}")
        print(f"🔎 Inspecionando: {etl_folder}")
        print(f"{'=' * 60}")

        if not os.path.exists(etl_folder):
            msg = f"⚠️ [IGNORADO] {os.path.basename(etl_folder)}: Diretório não encontrado no caminho."
            print(msg)
            relatorio.append(msg)
            continue

        # 🟢 Varredura recursiva inteligente ignorando venv, __pycache__, etc.
        ficheiros_log = []
        for root, dirs, files in os.walk(etl_folder):
            dirs[:] = [d for d in dirs if d not in pastas_excluidas]
            for file in files:
                if file.endswith(".log"):
                    ficheiros_log.append(os.path.join(root, file))

        if not ficheiros_log:
            msg = f"⚠️ [IGNORADO] {os.path.basename(etl_folder)}: Nenhum ficheiro .log encontrado nas pastas ou subpastas."
            print(msg)
            relatorio.append(msg)
            continue

        # Pega o primeiro log encontrado para análise
        log_file_path = ficheiros_log[0]
        print(f"📄 Log detetado para análise: {log_file_path}")

        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                error_log = f.read()
        except Exception as e:
            msg = f"❌ [ERRO DE LEITURA] {os.path.basename(etl_folder)}: Não foi possível ler o log ({e})."
            print(msg)
            relatorio.append(msg)
            continue

        if "ERROR" not in error_log:
            msg = f"🟢 [SAUDÁVEL] {os.path.basename(etl_folder)}: Nenhum erro detetado."
            print(msg)
            relatorio.append(msg)
            continue

        print("🚨 Erro detetado no log! A acionar o Agente de Manutenção...")

        initial_state = {
            "etl_name": etl_folder,
            "error_log": error_log,
            "loop_count": 0
        }

        thread_id = str(uuid.uuid4())
        config = {"configurable": {"thread_id": thread_id}}

        print(f"🧵 Iniciando Thread (ID: {thread_id})\n")
        print("-" * 60)

        estado_final = {}
        nome_ultimo_no = ""

        try:
            for output in app.stream(initial_state, config):
                for node_name, node_state in output.items():
                    estado_final = node_state
                    nome_ultimo_no = node_name

                    print(f"🟢 Nó concluído: [{node_name.upper()}]")

                    if node_name == "validator":
                        print(f"   ➤ Requer manutenção (código)? {node_state.get('requires_maintenance')}")
                        print(f"   ➤ Problema de API? {node_state.get('is_api_down')}")
                        print(f"   ➤ Raciocínio: {node_state.get('validation_reasoning')}")
                    elif node_name == "developer":
                        files = node_state.get('files_to_update', [])
                        print(f"   ➤ O Desenvolvedor sugeriu alterações nos seguintes ficheiros:")
                        for f in files:
                            print(f"      - {f}")
                    elif node_name == "tester":
                        passed = node_state.get('test_passed')
                        print(f"   ➤ O Teste passou? {'✅ SIM' if passed else '❌ NÃO'}")
                    elif node_name == "deploy":
                        print("   ➤ 🚀 Deploy realizado! Código atualizado na pasta de produção.")

                    print("-" * 60)

            nome_amigavel = os.path.basename(etl_folder)

            # Avalia o resultado de forma totalmente segura contra estados vazios (None)
            test_passed = estado_final and estado_final.get('test_passed', False)
            requires_maint = estado_final and estado_final.get('requires_maintenance', True)
            arquivos = estado_final.get('files_to_update', []) if estado_final else []
            resume_correction = estado_final.get('resume_correction', []) if estado_final else []

            if nome_ultimo_no == "deploy" or test_passed:
                if resume_correction:
                    relatorio.append(f"✅ [CORRIGIDO] {nome_amigavel}: Resumo da correção: {resume_correction}")
                else:
                    relatorio.append(f"✅ [CORRIGIDO] {nome_amigavel}: Nenhum resumo para a correção foi criado.")
                
                # # Esvazia especificamente o ficheiro de log detetado para evitar loops
                # with open(log_file_path, 'w', encoding='utf-8') as f:
                #     f.write("")
            elif not requires_maint:
                relatorio.append(f"🟡 [ALERTA] {nome_amigavel}: Erro detetado, mas o Validador indicou que não requer alteração de código.")
            else:
                relatorio.append(f"❌ [FALHOU] {nome_amigavel}: O agente não conseguiu concluir a correção.")

        except Exception as e:
            msg = f"💥 [CRASH] {os.path.basename(etl_folder)}: Erro crítico na execução do grafo ({e})."
            print(msg)
            relatorio.append(msg)

    print("\n🎉 Patrulha concluída! A gerar relatório final...")
    
    if relatorio:
        enviar_relatorio_bulldog(relatorio)

if __name__ == "__main__":
    main()