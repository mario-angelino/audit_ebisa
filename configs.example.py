
class Settings:
    """Configurações do projeto - EXEMPLO"""
    
    # Dados de acesso ao Supabase (Conexão PostgreSQL)
    DB_HOST = "aws-1-sa-east-1.pooler.supabase.com"
    DB_PORT = 5432
    DB_NAME = "..."
    DB_USER = "postgres...."
    DB_PASSWORD = "COLOQUE_SUA_SENHA_AQUI"
    
    # String de conexão completa
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    
    # Configurações da aplicação
    TABELA_CONTABILIDADE = "contabilidade"
    PASTA_DADOS = "dados"
    SEPARADOR_CSV = ";"
    ENCODING = "utf-8"