import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from rich import print
from core.state import AgentState
from core.nodes import gather_context_node, validator_node, developer_node, tester_node, deploy_node
from core.bigquery_saver import BigQuerySaver

load_dotenv()

def build_graph():
    """Constrói, liga os nós e compila o grafo com o BigQuery Saver."""
    

    workflow = StateGraph(AgentState)

    # 2. Regista os nós (As funções definidas no nodes.py)
    workflow.add_node("gather_context", gather_context_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("developer", developer_node)
    workflow.add_node("tester", tester_node)
    workflow.add_node("deploy", deploy_node)

    # 3. Define as arestas lineares 
    workflow.add_edge(START, "gather_context")
    workflow.add_edge("gather_context", "validator")

    # 4. Roteamento Condicional: O erro precisa mesmo de código?
    def route_validation(state: AgentState):
        if state.get("requires_maintenance"):
            return "developer"
        return END

    workflow.add_conditional_edges("validator", route_validation)

    # 5. O Desenvolvedor entrega sempre o código ao Testador
    workflow.add_edge("developer", "tester")

    # 6. Roteamento Condicional: O Loop Iterativo (A Mágica do Agente)
    def route_tester(state: AgentState):
        max_loops = int(os.getenv("MAX_TEST_LOOPS", "3"))
        
        if state.get("test_passed"):

            return "deploy"
        elif state.get("loop_count", 0) >= max_loops:
            print(f"⚠️ Limite de loops atingido ({max_loops}). O Agente não conseguiu resolver o problema sozinho.")
            return END
        else:
            print(f"🔄 Teste falhou (Tentativa {state.get('loop_count')}). A devolver ao Desenvolvedor...")
            
            state["error_log"] = state.get("test_output")
            return "developer"

    workflow.add_conditional_edges("tester", route_tester)

    # 7. O Deploy é a última etapa antes do fim
    workflow.add_edge("deploy", END)

    # 8. Instancia o Checkpointer do BigQuery
    project_id = os.getenv("GCP_PROJECT_ID")
    dataset_id = os.getenv("GCP_DATASET_ID")
    
    # memory_saver = BigQuerySaver(project_id=project_id, dataset_id=dataset_id)
    
    # Compila o grafo completo associando a memória a longo prazo
    # app = workflow.compile(checkpointer=memory_saver)
    
    return  workflow.compile()
