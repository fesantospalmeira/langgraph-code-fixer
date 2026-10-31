import os
import re
import json
import sys
import subprocess
import shutil
import tempfile
import datetime
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI
from google.cloud import bigquery
from rich.console import Console
from rich.panel import Panel
from .state import AgentState
from .tools import get_project_files, get_correction_history
from .prompts import generate_prompt_validator,generate_prompt_developer,generate_prompt_deploy
from dotenv import load_dotenv
from utils.utils import sanitizador_seguro,extrair_texto_da_mensagem

load_dotenv()

console = Console()

llm_validator = ChatGoogleGenerativeAI(model=os.getenv("MODEL_ORCHESTRATOR", "gemini-3.6-flash"),api_key= os.getenv("GOOGLE_API_KEY"),max_retries=6)
llm_developer = ChatGoogleGenerativeAI(model=os.getenv("MODEL_DEVELOPER", "gemini-3.8-flash"),api_key= os.getenv("GOOGLE_API_KEY"),max_retries=6)
llm_deploy = ChatGoogleGenerativeAI(model=os.getenv("MODEL_DEVELOPER", "gemini-3.6-flash"),api_key= os.getenv("GOOGLE_API_KEY"),max_retries=6)

# Estrutura de saída para o Validator
class ValidatorOutput(BaseModel):
    requires_maintenance: bool = Field(description="True se o erro precisar de correção no código.")
    is_api_down: bool = Field(description="True se o erro for apenas uma instabilidade temporária ou Rate Limit (ex: 429, 500).")
    validation_reasoning: str = Field(description="O raciocínio que levou a esta decisão.")

def gather_context_node(state: AgentState) -> dict:
    """Nó 1: Prepara o terreno recolhendo ficheiros e o histórico do BigQuery."""
    etl_name = state["etl_name"]
    base_path = etl_name
    
    history = get_correction_history(etl_name)
    console.print(f"[bold cyan]{history}")
    source_code = get_project_files(base_path)
    console.print(f"[bold cyan]Contexto Carregado:[/bold cyan] Encontrados {len(source_code.split('<file path=')) - 1} arquivos para análise.")
    return {
        "history_summary": history,
        "source_code": source_code
    }

def validator_node(state: AgentState) -> dict:
    """Nó 2: Analisa o log de erro e o histórico para decidir a rota """
    prompt = generate_prompt_validator(state)
    
    structured_llm = llm_validator.with_structured_output(ValidatorOutput)
    result = structured_llm.invoke(prompt)
    
    return {
        "requires_maintenance": result.requires_maintenance,
        "is_api_down": result.is_api_down,
        "validation_reasoning": result.validation_reasoning
    }

def developer_node(state: AgentState) -> dict:
    """Nó 3: Resolve o problema do código."""

    prompt = generate_prompt_developer(state)
    
    result = llm_developer.invoke(prompt)
    
    if isinstance(result.content, list):
        proposed_code = "".join([str(b.get("text", b)) if isinstance(b, dict) else str(b) for b in result.content])
    else:
        proposed_code = str(result.content)
    
    console.print(Panel(proposed_code[:500] + "\n\n... [TRUNCADO]", title="[blue]Resposta Bruta do Agente Desenvolvedor[/blue]"))
    
    # Extrai os caminhos dos ficheiros a partir das tags <file path="...">
    files_to_update = re.findall(r'<file path="(.*?)">', proposed_code)
    
    if files_to_update:
        console.print(f"[bold magenta]Arquivos que o LLM quer alterar:[/bold magenta] {files_to_update}")
    else:
        console.print("[bold red]ALERTA:[/bold red] O LLM não devolveu nenhuma tag <file path=...> válida.")
    return {
        "proposed_code": proposed_code,
        "files_to_update": files_to_update
    }

def tester_node(state: AgentState) -> dict:
    """Nó 4: Executa o código proposto isoladamente para garantir que não tem erros de sintaxe."""
    proposed_code = state["proposed_code"]
    etl_name = state["etl_name"]
    base_path = etl_name
    
    test_passed = False
    test_output = ""

    with tempfile.TemporaryDirectory() as temp_dir:
        shutil.copytree(base_path, temp_dir, dirs_exist_ok=True)
        
        # 2. Extrai e sobrescreve os ficheiros com a proposta do LLM
        file_blocks = re.finditer(r'<file path="(.*?)">(.*?)</file>', proposed_code, re.DOTALL)
        for block in file_blocks:
            rel_path = block.group(1).strip()
            content = block.group(2).strip()
            
            full_path = os.path.join(temp_dir, rel_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
        
        # 3. Executa o ficheiro principal
        main_script = os.path.join(temp_dir, "main.py")
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        try:
            process = subprocess.run(
                # ["python", main_script], 
                [sys.executable, main_script], 
                capture_output=True, 
                text=True, 
                encoding="utf-8",
                env=env,
                timeout=60 
            )
            
            if process.returncode == 0:
                test_passed = True
                test_output = "Sucesso: O script correu e gerou o DataFrame.\n" + process.stdout
                console.print(Panel(process.stdout[:500], title="[green]Teste Passou - Stdout[/green]"))
            else:
                test_passed = False
                test_output = "Erro na execução de teste:\n" + process.stderr
                console.print(Panel(process.stderr, title="[red]Teste Falhou - Stderr[/red]"))
                
        except subprocess.TimeoutExpired:
            test_passed = False
            test_output = "Timeout: O script demorou mais de 60 segundos a executar."
            console.print("[bold red]Timeout:[/bold red] O script de teste ficou em loop infinito ou pendurado.")
            
    return {
        "test_passed": test_passed,
        "test_output": test_output,
        "loop_count": 1 
    }

def deploy_node(state: AgentState) -> dict:
    """Nó 5: Se o teste passou, sobrescreve os ficheiros de produção e regista no BigQuery."""
    proposed_code = state["proposed_code"]
    etl_name = state["etl_name"]
    base_path = etl_name
    
    # 1. Aplicar a versão final (Aviso: numa versão robusta, pediríamos ao LLM para remover a flag de teste nesta fase)
    file_blocks = re.finditer(r'<file path="(.*?)">(.*?)</file>', proposed_code, re.DOTALL)
    for block in file_blocks:
        rel_path = block.group(1).strip()
        content = block.group(2).strip()
        
        full_path = os.path.join(base_path, rel_path)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
            
    # 2. Registar a correção no BigQuery
    project_id = os.getenv("GCP_PROJECT_ID")
    dataset_id = os.getenv("GCP_DATASET_ID")
    client = bigquery.Client(project=project_id)
    table_ref = f"{project_id}.{dataset_id}.etl_corrections_log"
    
    prompt = generate_prompt_deploy(state)
    result_raw = llm_deploy.invoke(prompt)

    result = extrair_texto_da_mensagem(result_raw)
    print('> result - ',result)

    row_to_insert = [
        {
            "id": f"{etl_name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "timestamp": datetime.datetime.now().isoformat(),
            "etl_name": etl_name,
            "files_changed": ", ".join(state["files_to_update"]),
            "original_error": state["error_log"][:500], # Limitar o tamanho do log
            "fix_summary": result
        }
    ]
    data_to_load = row_to_insert if isinstance(row_to_insert, list) else [row_to_insert]
    
    safe_data = json.loads(json.dumps(data_to_load, default=sanitizador_seguro))
    
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND
    )
    job = client.load_table_from_json(safe_data, table_ref, job_config=job_config)
    job.result()


    return {"resume_correction": result}