from typing import TypedDict, Annotated, Optional
import operator

class AgentState(TypedDict):
    """
    Define a estrutura de dados que transita entre os nós do LangGraph.
    As chaves representam a memória compartilhada durante uma única execução.
    """
    
    # 1. Inputs Iniciais
    etl_name: str
    error_log: str
    
    # 2. Contexto de Leitura 
    history_summary: str
    source_code: str
    
    # 3. Decisões do Agente Validador (Orquestrador)
    requires_maintenance: bool
    is_api_down: bool
    validation_reasoning: str
    
    # 4. Ciclo de Desenvolvimento e Teste
    proposed_code: str
    files_to_update: list[str] 
    test_output: str
    test_passed: bool

    #5. Resumo do deploy
    resume_correction: str
    
    # 5. Controle de Loop
    loop_count: Annotated[int, operator.add]