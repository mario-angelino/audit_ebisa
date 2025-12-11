"""
pages/9_test_connection.py - Página de teste de conexão com o Supabase
"""

import streamlit as st
import pandas as pd
from utils.auth import test_connection, list_tables, get_table_structure


# Configuração da página
st.set_page_config(
    page_title="Teste de Conexão - Audit Ebisa",
    page_icon="🔧",
    layout="wide"
)


def main():
    """
    Página principal de teste de conexão
    """
    st.title("🔧 Teste de Conexão com Banco de Dados")
    st.markdown("---")

    st.info("""
    Esta página permite testar a conexão com o Supabase e verificar as tabelas disponíveis.
    **Acesso livre** - não requer autenticação.
    """)

    # Seção 1: Teste de Conexão
    st.header("🧪 Teste de Conexão")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Testar Conexão Básica", use_container_width=True, type="primary"):
            with st.spinner("Testando conexão com o Supabase..."):
                result = test_connection()

                if result["success"]:
                    st.success("✅ " + result["message"])

                    # Mostrar informações sobre as credenciais (ocultando partes sensíveis)
                    try:
                        from utils.supabase_client import supabase
                        url = str(supabase.supabase_url)
                        # Ocultar parte da URL por segurança
                        safe_url = url[:30] + "..." + \
                            url[-20:] if len(url) > 50 else url
                        st.info(f"**URL do Supabase:** `{safe_url}`")
                    except:
                        pass
                else:
                    st.error("❌ " + result["message"])
                    st.warning("""
                    **Possíveis causas:**
                    - Credenciais incorretas no `.streamlit/secrets.toml`
                    - Problemas de rede/firewall
                    - Projeto Supabase não existe ou está desativado
                    """)

    with col2:
        if st.button("Listar Todas as Tabelas", use_container_width=True):
            with st.spinner("Buscando tabelas do schema público..."):
                result = list_tables()

                if result["success"]:
                    st.success("✅ " + result["message"])

                    if result["tables"]:
                        st.write(
                            f"**📊 {len(result['tables'])} tabelas encontradas:**")

                        # Criar DataFrame com as tabelas
                        df_tables = pd.DataFrame(result["tables"])

                        # Exibir tabela
                        st.dataframe(
                            df_tables,
                            use_container_width=True,
                            column_config={
                                "table_schema": st.column_config.TextColumn("Schema"),
                                "table_name": st.column_config.TextColumn("Nome da Tabela"),
                                "table_type": st.column_config.TextColumn("Tipo"),
                                "is_insertable_into": st.column_config.CheckboxColumn("Inserível")
                            }
                        )

                        # Verificar se a tabela 'users' existe
                        users_exists = any(
                            t["table_name"] == "users" for t in result["tables"])

                        if users_exists:
                            st.success("✅ Tabela 'users' encontrada!")
                        else:
                            st.error("❌ Tabela 'users' NÃO encontrada!")
                            st.info("""
                            **Solução:**
                            1. Acesse o Dashboard do Supabase
                            2. Vá para o SQL Editor
                            3. Execute o SQL para criar a tabela 'users'
                            """)
                    else:
                        st.warning(
                            "Nenhuma tabela encontrada no schema público")
                else:
                    st.error("❌ " + result["message"])

    st.markdown("---")

    # Seção 2: Verificar estrutura de tabela específica
    st.header("🔍 Verificar Estrutura de Tabela")

    col_a, col_b = st.columns([1, 3])

    with col_a:
        table_name = st.text_input(
            "Nome da tabela:",
            value="users",
            help="Digite o nome da tabela que deseja verificar"
        )

    with col_b:
        if st.button("Verificar Estrutura", use_container_width=True):
            if not table_name.strip():
                st.error("⚠️ Por favor, informe o nome da tabela!")
            else:
                with st.spinner(f"Buscando estrutura da tabela '{table_name}'..."):
                    structure = get_table_structure(table_name)

                    if structure["success"]:
                        st.success(
                            f"✅ Estrutura da tabela '{table_name}' encontrada")

                        if structure["columns"]:
                            # Criar DataFrame com a estrutura
                            df_structure = pd.DataFrame(structure["columns"])

                            # Exibir estrutura
                            st.dataframe(
                                df_structure,
                                use_container_width=True,
                                column_config={
                                    "column_name": st.column_config.TextColumn("Coluna"),
                                    "data_type": st.column_config.TextColumn("Tipo de Dado"),
                                    "is_nullable": st.column_config.TextColumn("Pode ser Nulo"),
                                    "column_default": st.column_config.TextColumn("Valor Padrão"),
                                    "character_maximum_length": st.column_config.NumberColumn("Tamanho Máximo")
                                }
                            )

                            # Verificar se a tabela 'users' tem a estrutura correta
                            if table_name.lower() == "users":
                                required_columns = {
                                    "id", "full_name", "fl_ativo", "nivel"}
                                actual_columns = {col["column_name"]
                                                  for col in structure["columns"]}

                                missing_columns = required_columns - actual_columns
                                extra_columns = actual_columns - required_columns

                                if missing_columns:
                                    st.error(
                                        f"❌ Colunas faltando na tabela 'users': {missing_columns}")
                                if extra_columns:
                                    st.warning(
                                        f"⚠️ Colunas extras na tabela 'users': {extra_columns}")
                                if not missing_columns and not extra_columns:
                                    st.success(
                                        "✅ Estrutura da tabela 'users' está correta!")
                        else:
                            st.warning(
                                f"A tabela '{table_name}' não possui colunas ou não foi encontrada")
                    else:
                        st.error(f"❌ {structure['message']}")

    st.markdown("---")

    # Seção 3: SQL para criar tabela 'users' se necessário
    st.header("📝 SQL para Criar Tabela 'users'")

    st.info("""
    Se a tabela 'users' não existir ou estiver com estrutura incorreta, 
    execute este SQL no **SQL Editor** do seu projeto Supabase.
    """)

    sql_code = """
-- Criar tabela users se não existir
CREATE TABLE IF NOT EXISTS public.users (
  id UUID NOT NULL,
  full_name TEXT NOT NULL DEFAULT '',
  avatar_url TEXT NULL,
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  fl_ativo BOOLEAN NULL DEFAULT FALSE,
  nivel INTEGER NOT NULL DEFAULT 1,
  CONSTRAINT profiles_pkey PRIMARY KEY (id),
  CONSTRAINT profiles_id_fkey FOREIGN KEY (id) REFERENCES auth.users (id) ON DELETE CASCADE,
  CONSTRAINT users_nivel_check CHECK (
    (nivel >= 1) AND (nivel <= 255)
  )
);

-- Criar trigger para atualizar updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_profiles_set_updated_at ON public.users;

CREATE TRIGGER trg_profiles_set_updated_at 
BEFORE UPDATE ON public.users 
FOR EACH ROW 
EXECUTE FUNCTION set_updated_at();

-- Garantir permissões
GRANT ALL ON public.users TO authenticated;
GRANT ALL ON public.users TO service_role;
"""

    st.code(sql_code, language="sql")

    # Botão para copiar o SQL
    if st.button("📋 Copiar SQL para Área de Transferência", use_container_width=True):
        st.session_state.copied_sql = sql_code
        st.success("SQL copiado! Cole no SQL Editor do Supabase.")

    st.markdown("---")

    # Seção 4: Instruções para uso
    st.header("📋 Instruções de Uso")

    with st.expander("🔧 Como usar esta página de diagnóstico"):
        st.markdown("""
        ### **Passo 1: Testar Conexão**
        1. Clique em **"Testar Conexão Básica"**
        2. Se der sucesso ✅, a conexão está funcionando
        3. Se der erro ❌, verifique suas credenciais no `.streamlit/secrets.toml`
        
        ### **Passo 2: Verificar Tabelas**
        1. Clique em **"Listar Todas as Tabelas"**
        2. Verifique se a tabela `users` aparece na lista
        3. Se não aparecer, você precisa criá-la
        
        ### **Passo 3: Criar Tabela (se necessário)**
        1. Copie o SQL acima
        2. Acesse seu projeto Supabase
        3. Vá para **SQL Editor**
        4. Cole o SQL e execute
        5. Volte aqui e teste novamente
        
        ### **Passo 4: Verificar Estrutura**
        1. Digite `users` no campo "Nome da tabela"
        2. Clique em **"Verificar Estrutura"**
        3. Confirme se todas as colunas necessárias estão presentes
        
        ### **Credenciais necessárias no `.streamlit/secrets.toml`:**
        ```toml
        SUPABASE_URL = "https://seu-projeto.supabase.co"
        SUPABASE_KEY = "sua-chave-anon-ou-service"
        ```
        """)

    st.markdown("---")

    # Seção 5: Botões de navegação
    st.header("🧭 Navegação")

    col_nav1, col_nav2 = st.columns(2)

    with col_nav1:
        if st.button("⬅️ Voltar para Login", use_container_width=True):
            st.switch_page("app.py")

    with col_nav2:
        if st.button("📝 Ir para Cadastro", use_container_width=True):
            st.session_state.show_register = True
            st.switch_page("app.py")

    st.markdown("---")

    # Rodapé
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 1rem 0;'>
        <small>Audit Ebisa - Página de Diagnóstico © 2026</small>
    </div>
    """, unsafe_allow_html=True)


# Executar página
if __name__ == "__main__":
    main()
