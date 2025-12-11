from database import conectar, desconectar

def testar_conexao():
    """Testa a conexão com o Supabase (PostgreSQL)"""
    
    try:
        print("🔄 Tentando conectar ao Supabase...")
        
        # Conectar
        conn = conectar()
        
        # Testar a conexão
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        versao = cursor.fetchone()
        
        print("✅ Conexão estabelecida com sucesso!")
        print(f"📊 Versão do PostgreSQL: {versao[0]}")
        
        # Fechar cursor e conexão
        cursor.close()
        desconectar(conn)
        
        print("🔒 Conexão fechada.")
        
    except Exception as e:
        print(f"❌ Erro: {e}")


if __name__ == "__main__":
    testar_conexao()