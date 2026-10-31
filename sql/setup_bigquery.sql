-- Tabela principal para armazenar o estado global de cada Thread
CREATE TABLE `logger-agent-512518.dm_prod.langgraph_checkpoints` (
    thread_id STRING NOT NULL,
    checkpoint_ns STRING NOT NULL,
    checkpoint_id STRING NOT NULL,
    parent_checkpoint_id STRING,
    type STRING,
    checkpoint BYTES NOT NULL,
    metadata BYTES NOT NULL
);

-- Tabela de writes assíncronos/paralelos para gerenciar canais do LangGraph
CREATE TABLE `logger-agent-512518.dm_prod.langgraph_checkpoint_writes` (
    thread_id STRING NOT NULL,
    checkpoint_ns STRING NOT NULL,
    checkpoint_id STRING NOT NULL,
    task_id STRING NOT NULL,
    idx INT64 NOT NULL,
    channel STRING NOT NULL,
    type STRING,
    blob BYTES NOT NULL
);

-- Tabela de memória semântica do seu ETL (Consultada antes do LLM atuar)
CREATE TABLE `logger-agent-512518.dm_prod.etl_corrections_log` (
    id STRING NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP(),
    etl_name STRING NOT NULL,
    files_changed STRING NOT NULL,
    original_error STRING NOT NULL,
    fix_summary STRING NOT NULL
);