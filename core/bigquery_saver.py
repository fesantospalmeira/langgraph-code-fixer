import json
import base64
import pickle
from typing import Optional, List, Tuple, Any, Dict
from google.cloud import bigquery
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from utils.utils import LangGraphEncoder,limpar_bytes

        
class BigQuerySaver(BaseCheckpointSaver):
    """
    Checkpointer customizado do LangGraph utilizando Google BigQuery.
    Requer a variável de ambiente GOOGLE_APPLICATION_CREDENTIALS apontando para o JSON da Service Account.
    """
    
    def __init__(self, project_id: str, dataset_id: str):
        super().__init__()
        self.client = bigquery.Client(project=project_id)
        self.dataset_id = dataset_id
        
        # Referências completas das tabelas
        self.checkpoints_table = f"{project_id}.{dataset_id}.langgraph_checkpoints"
        self.writes_table = f"{project_id}.{dataset_id}.langgraph_checkpoint_writes"

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """Recupera o último checkpoint salvo de uma thread."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id")
        
        query = f"""
            SELECT checkpoint, metadata, parent_checkpoint_id, checkpoint_id
            FROM `{self.checkpoints_table}`
            WHERE thread_id = @thread_id AND checkpoint_ns = @checkpoint_ns
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("thread_id", "STRING", thread_id),
                bigquery.ScalarQueryParameter("checkpoint_ns", "STRING", checkpoint_ns),
            ]
        )
        
        if checkpoint_id:
            query += " AND checkpoint_id = @checkpoint_id"
            job_config.query_parameters.append(
                bigquery.ScalarQueryParameter("checkpoint_id", "STRING", checkpoint_id)
            )
        else:
            query += " ORDER BY checkpoint_id DESC LIMIT 1"
            
        result = list(self.client.query(query, job_config=job_config).result())
        
        if not result:
            return None
            
        row = result[0]
        
        # Deserializa os binários do banco para objetos Python
        checkpoint = pickle.loads(row.checkpoint)
        metadata = pickle.loads(row.metadata)
        
        return CheckpointTuple(
            config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": row.checkpoint_id,
                }
            },
            checkpoint=checkpoint,
            metadata=metadata,
            parent_config={
                "configurable": {
                    "thread_id": thread_id,
                    "checkpoint_ns": checkpoint_ns,
                    "checkpoint_id": row.parent_checkpoint_id,
                }
            } if row.parent_checkpoint_id else None,
        )

    def put(self, config: RunnableConfig, checkpoint: Checkpoint, metadata: CheckpointMetadata, new_versions: dict = None, **kwargs) -> RunnableConfig:      
        """Salva o estado atual da thread no BigQuery."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")

        checkpoint_bytes = self.serde.dumps(checkpoint)
        metadata_bytes = self.serde.dumps(metadata)
        rows_to_insert = [
            {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
                "parent_checkpoint_id": config["configurable"].get("checkpoint_id"),
                "type": "checkpoint",
                "checkpoint": base64.b64encode(checkpoint_bytes).decode('utf-8'),
                "metadata": base64.b64encode(metadata_bytes).decode('utf-8'),
            }
        ]
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_APPEND
        )
        
        job = self.client.load_table_from_json([row], self.checkpoints_table, job_config=job_config)
        job.result()
            
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint["id"],
            }
        }

    def put_writes(self, config: RunnableConfig, writes: List[Tuple[str, Any]], task_id: str) -> None:
        """Salva writes assíncronos (utilizados internamente pelo LangGraph para gerenciar as rotas)."""
        thread_id = config["configurable"]["thread_id"]
        checkpoint_ns = config["configurable"].get("checkpoint_ns", "")
        checkpoint_id = config["configurable"].get("checkpoint_id", "")
        
        rows_to_insert = []
        for idx, (channel, value) in enumerate(writes):
            rows_to_insert.append({
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
                "task_id": task_id,
                "idx": idx,
                "channel": channel,
                "type": "write",
                "blob": pickle.dumps(value)
            })
            
        if rows_to_insert:
            errors = self.client.insert_rows_json(self.writes_table, rows_to_insert)
            if errors:
                raise RuntimeError(f"Erro ao inserir writes no BigQuery: {errors}")

    def list(self, config: Optional[RunnableConfig], filter: Optional[Dict[str, Any]] = None, before: Optional[RunnableConfig] = None, limit: Optional[int] = None) -> Any:
        """Método obrigatório do BaseCheckpointSaver. Para o escopo deste agente, podemos deixá-lo com pass ou implementar uma busca simples se necessário no futuro."""
        pass