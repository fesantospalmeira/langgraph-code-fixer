import os
from google.cloud import bigquery

def get_project_files(base_path: str) -> str:
    """
    Lê os ficheiros do projeto e formata-os em tags XML para o contexto do LLM.
    Ignora diretórios e ficheiros que não são relevantes para a análise de código.
    """
    ignore_dirs = {'.git', '__pycache__', '.venv', 'venv', 'node_modules'}
    ignore_exts = {'.pyc', '.pyo', '.log', '.zip', '.sample'}
    ignore_files = {'app.log', 'app_pedidos (1).log'} 

    xml_output = ["<project_files>"]
    
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        
        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in ignore_exts or file in ignore_files:
                continue
                
            file_path = os.path.join(root, file)
            
            try:
    
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                rel_path = os.path.relpath(file_path, base_path)
                
                xml_output.append(f'  <file path="{rel_path}">\n{content}\n  </file>')
            except Exception:
                continue
                
    xml_output.append("</project_files>")
    return "\n".join(xml_output)


def get_correction_history(etl_name: str) -> str:
    """
    Busca no BigQuery as últimas correções aplicadas ao ETL com falha.
    Garante que o Agente Validador tenha o contexto do que já foi tentado no passado.
    """
    project_id = os.getenv("GCP_PROJECT_ID")
    dataset_id = os.getenv("GCP_DATASET_ID")
    
    if not project_id or not dataset_id:
        return "Aviso: Credenciais GCP ausentes. Histórico não carregado."
        
    try:
        client = bigquery.Client(project=project_id)
        table_ref = f"{project_id}.{dataset_id}.etl_corrections_log"
        
        query = f"""
            SELECT timestamp, files_changed, original_error, fix_summary
            FROM `{table_ref}`
            WHERE etl_name = @etl_name
            ORDER BY timestamp DESC
            LIMIT 5
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("etl_name", "STRING", etl_name),
            ]
        )
        
        results = client.query(query, job_config=job_config).result()
        
        history = []
        for row in results:
            history.append(
                f"Data: {row.timestamp}\n"
                f"Ficheiros Modificados: {row.files_changed}\n"
                f"Erro Registado: {row.original_error}\n"
                f"Solução Aplicada: {row.fix_summary}\n"
                "---"
            )
            
        # tirar isso depois
        history = []
        if not history:
            return "Nenhum histórico de correções encontrado para este ETL. Esta é a primeira falha registada ou a base de dados foi limpa."
            
        return "\n".join(history)
        
    except Exception as e:
        return f"Aviso: Erro ao aceder ao histórico do BigQuery: {str(e)}"