from src.core.config import (
    AppConfig,
    EmbeddingConfig,
    ModelConfig,
    RetrievalConfig,
    VectorStoreConfig,
)


def test_model_config_normalizes_provider():
    config = ModelConfig(provider=" Aliyun ", model="qwen-plus", api_key_env="KEY")

    assert config.provider == "aliyun"
    assert config.model == "qwen-plus"
    assert config.api_key_env == "KEY"


def test_embedding_config_defaults_to_local_hash():
    config = EmbeddingConfig(provider=" Local ")

    assert config.provider == "local"
    assert config.model == "local-hash"


def test_vector_store_config_defaults_to_local_store():
    config = VectorStoreConfig(provider=" Local ")

    assert config.provider == "local"
    assert config.persist_dir == ".codebase_agent/vectorstores"


def test_retrieval_config_clamps_top_k():
    assert RetrievalConfig(top_k=0).top_k == 1
    assert RetrievalConfig(top_k=99).top_k == 20


def test_app_config_defaults_to_local_vector_store():
    config = AppConfig()

    assert config.vector_store.provider == "local"
