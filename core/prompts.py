from .state import AgentState

def generate_prompt_validator(state:AgentState) -> str:
    """Gera o prompt do validador"""
    prompt = f"""
        Você é um arquiteto de dados sênior responsável por validar uma falha no ETL        
        ETL: {state["etl_name"]}
        Log de Erro:
        {state["error_log"]}
        
        Histórico de Correções Anteriores:
        {state["history_summary"]}
        
        Determina se este erro requer alteração no código Python (requires_maintenance = True) 
        ou se é apenas uma falha de rede/API indisponível (is_api_down = True).

        Se o problema da API cair for recorrente, considere alterar o código apenas ser for um erro 429 Too Many Requests.
        Se for um problema de campos que não estão na database, considere remover estes campos dentro do df.
        Me diga também se esse erro já apareceu anteriormente e quantoas vezes apareceu.
        Sinalize também se esse erro pode ter sido gerado por uma correção anterior.
        """

    return prompt

def generate_prompt_developer(state:AgentState) -> str:
    """Gera o prompt do desenvolvedor"""


    prompt = f"""
    Você é um Engenheiro de dados Especialista (Python/Pandas/Polars)
    Ocorreu o seguinte erro no ETL '{state["etl_name"]}':
    
    {state["error_log"]}
    
    Aqui está o código fonte atual do projeto (em formato XML):
    {state["source_code"]}
    
    Aqui está o histórico de correções (EVITA REPETIR ERROS PASSADOS):
    {state["history_summary"]}
    
    TAREFA:
    1. Corrige o erro.
    2. REGRA CRÍTICA PARA TESTE: O código corrigido NÃO DEVE gravar na base de dados SQL Server real. 
       Comenta ou utiliza uma flag para saltar a inserção no banco e imprime o DataFrame (Pandas ou Polars) no final.
    3. Retorna APENAS os ficheiros modificados envolvidos em tags XML com o caminho exato. 
       Exemplo: <file path="modules/Empresa.py">CÓDIGO AQUI</file>
    """

    return prompt

def generate_prompt_deploy(state:AgentState) -> str:
    """Gera o prompt do deployer """


    prompt = f"""
    Você é o Agente Desenvolvedor e Engenheiro Sênior de DevOps do projeto Bulldog ETL.
    Sua missão é analisar o erro técnico que ocorreu no pipeline, a correção de código que você aplicou e gerar um resumo executivo claro e direto para ser enviado em um email e para sevir de contexto para as próximas correções.

    O resumo deve seguir estritamente o seguinte formato em Markdown:

    - Erro Original: [Descreva em uma frase curta o erro exato que apareceu no log, ex: AttributeError no pandas]
    - Causa Raiz: [Explique brevemente por que o erro aconteceu no código, ex: Uso incorreto do método no singular 'drop_duplicate' em vez de 'drop_duplicates']
    - Solução Aplicada: [Explique o que foi alterado e em qual arquivo, ex: Correção do método na linha 37 do arquivo modules/Empresa.py]

    Ocorreu o seguinte erro no ETL '{state["etl_name"]}':
    
    {state["error_log"]}
    
    Este era o código fonte do projeto:

    {state["source_code"]}

    Estes são os arquivos que devem ser atualizados:

    {state["files_to_update"]}

    Aqui está o resultado final:

    {state["proposed_code"]}
    
    Aqui está o histórico de correções (EVITA REPETIR ERROS PASSADOS):

    {state["history_summary"]}
    
    """

    return prompt