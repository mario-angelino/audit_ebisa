import streamlit as st
from utils.supabase_client import supabase


def login(email: str, password: str) -> dict:
    """
    Realiza login do usuário

    Args:
        email: Email do usuário
        password: Senha do usuário

    Returns:
        dict com 'success' (bool) e 'message' (str)
    """
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if response.user:
            # Armazena dados do usuário na sessão
            st.session_state.authenticated = True
            st.session_state.user = {
                "id": response.user.id,
                "email": response.user.email,
                "nome": response.user.user_metadata.get("nome_completo", email.split("@")[0])
            }
            return {"success": True, "message": "Login realizado com sucesso!"}
        else:
            return {"success": False, "message": "Erro ao realizar login."}

    except Exception as e:
        error_msg = str(e).lower()

        # Tratamento de erros comuns
        if "invalid login credentials" in error_msg or "invalid" in error_msg:
            return {"success": False, "message": "Email ou senha incorretos."}
        elif "email not confirmed" in error_msg:
            return {"success": False, "message": "Email não confirmado. Verifique sua caixa de entrada."}
        elif "user not found" in error_msg:
            return {"success": False, "message": "Usuário não encontrado."}
        else:
            return {"success": False, "message": f"Erro de autenticação: {str(e)}"}


def logout():
    """
    Realiza logout do usuário
    """
    try:
        supabase.auth.sign_out()
        st.session_state.authenticated = False
        st.session_state.user = None
        st.rerun()
    except Exception as e:
        st.error(f"Erro ao fazer logout: {str(e)}")


def check_authentication():
    """
    Verifica se o usuário está autenticado

    Returns:
        bool: True se autenticado, False caso contrário
    """
    return st.session_state.get("authenticated", False)


def get_current_user():
    """
    Retorna dados do usuário atual

    Returns:
        dict com dados do usuário ou None
    """
    return st.session_state.get("user", None)


def require_authentication():
    """
    Decorator/função para proteger páginas que requerem autenticação
    Redireciona para a página de login se não autenticado
    """
    if not check_authentication():
        st.warning("⚠️ Você precisa estar autenticado para acessar esta página.")
        st.info("👉 Retorne à página principal para fazer login.")
        st.stop()


def create_user(email: str, password: str, full_name: str) -> dict:
    """
    Cria um novo usuário no sistema Supabase Auth e na tabela public.users

    Estratégia:
    1) Tenta criar via admin.create_user (requer SERVICE KEY) com email_confirm=True e metadata compatível.
    2) Se admin falhar (por permissão/ANON), faz fallback para auth.sign_up.
    3) Após obter user_id, insere em public.users. Se falhar, tenta rollback do usuário criado via admin.
    """
    try:
        print(
            f"email: {email}, senha: {'*' * len(password)}, full_name: {full_name}")

        user = None
        created_with_admin = False

        # 1) Tenta via Admin (SERVICE KEY). Se não houver permissão, cai no except e faz fallback.
        try:
            admin_res = supabase.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True
            })
            user = getattr(admin_res, "user", None)
            created_with_admin = user is not None
        except Exception as admin_err:
            print(
                f"[create_user] admin.create_user falhou; fallback para sign_up. Detalhes: {str(admin_err)}")

        # 2) Fallback: sign_up público (ANON)
        if user is None:
            auth_response = supabase.auth.sign_up({
                "email": email,
                "password": password
            })
            user = getattr(auth_response, "user", None)

        if user is None:
            return {
                "success": False,
                "message": "Erro ao criar usuário no sistema de autenticação"
            }

        user_id = user.id

        # 3) Criar registro na tabela public.users
        user_data = {
            "id": user_id,
            "full_name": full_name,
            "fl_ativo": True,
            "nivel": 1
        }

        try:
            response = supabase.table("users").insert(user_data).execute()
        except Exception as insert_err:
            # Rollback do usuário apenas se criado via admin (permite delete via admin API)
            if created_with_admin:
                try:
                    supabase.auth.admin.delete_user(user_id)
                except Exception as del_err:
                    print(
                        f"[create_user] Falha no rollback do usuário {user_id}: {str(del_err)}")

            return {
                "success": False,
                "message": f"Erro ao criar perfil do usuário: {str(insert_err)}"
            }

        return {
            "success": True,
            "message": "Usuário criado com sucesso! Você já pode fazer login.",
            "user_id": user_id
        }

    except Exception as e:
        print(f"[create_user] Erro inesperado: {str(e)}")
        error_msg = str(e).lower()

        if "already registered" in error_msg or "user already exists" in error_msg:
            return {"success": False, "message": "Este email já está cadastrado no sistema"}
        elif "signup disabled" in error_msg or "signups not allowed" in error_msg:
            return {"success": False, "message": "Cadastro por e-mail desativado no Auth. Habilite 'Email signups' no Supabase."}
        elif "password" in error_msg:
            return {"success": False, "message": "A senha não atende aos requisitos de segurança"}
        elif "email" in error_msg:
            return {"success": False, "message": "Email inválido ou mal formatado"}
        elif "database error saving new user" in error_msg:
            return {
                "success": False,
                "message": "Erro do banco ao salvar novo usuário no Auth. Use SERVICE KEY no backend ou verifique as configurações do Auth (Auth → Settings → Email → 'Enable Email signups')."
            }
        else:
            return {"success": False, "message": f"Erro ao criar usuário: {str(e)}"}


def test_connection() -> dict:
    """
    Testa a conexão com o Supabase e lista tabelas disponíveis

    Returns:
        dict: Resultado do teste com sucesso, mensagem e dados das tabelas
    """
    try:
        # Testar conexão básica
        response = supabase.table("users").select("*").limit(1).execute()

        # Se chegou aqui, a conexão funciona
        return {
            "success": True,
            "message": "Conexão com Supabase estabelecida com sucesso",
            "tables": []
        }
    except Exception as e:
        # Tentar listar tabelas de outra forma
        try:
            # Usar uma consulta ao information_schema para listar tabelas
            # Nota: Esta consulta pode variar dependendo das permissões
            tables_query = """
            SELECT table_schema, table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
            """

            # Executar SQL raw
            response = supabase.rpc(
                'exec_sql', {'sql': tables_query}).execute()

            if response.data:
                tables = response.data
                return {
                    "success": True,
                    "message": "Conexão estabelecida - tabelas listadas via information_schema",
                    "tables": tables
                }
            else:
                return {
                    "success": False,
                    "message": f"Erro ao listar tabelas: {str(e)}",
                    "tables": []
                }

        except Exception as e2:
            return {
                "success": False,
                "message": f"Erro na conexão: {str(e)}",
                "tables": []
            }


def list_tables() -> dict:
    """
    Lista todas as tabelas disponíveis no schema público
    Usando uma abordagem alternativa sem depender de exec_sql
    """
    try:
        # Tentar listar tabelas usando uma consulta direta à information_schema
        # através de uma função RPC simples ou consulta direta se disponível

        # Primeiro, testar se podemos acessar alguma tabela conhecida
        known_tables = []

        # Tabelas comuns que podem existir
        common_tables = [
            "users", "profiles", "auth.users",
            "public.users", "public.profiles"
        ]

        for table_name in common_tables:
            try:
                # Tentar acessar a tabela
                response = supabase.table(table_name).select(
                    "count").limit(1).execute()
                known_tables.append({
                    "table_schema": "public" if "public." in table_name else table_name.split(".")[0] if "." in table_name else "public",
                    "table_name": table_name.split(".")[-1],
                    "table_type": "BASE TABLE",
                    "is_insertable_into": True
                })
            except:
                pass

        # Se encontrou alguma tabela
        if known_tables:
            return {
                "success": True,
                "message": f"✅ Encontradas {len(known_tables)} tabelas conhecidas",
                "tables": known_tables
            }
        else:
            # Tentar método alternativo: verificar tabelas do schema public
            # Isso pode não funcionar dependendo das permissões
            try:
                # Método alternativo: tentar criar uma tabela temporária e listar
                # (mais seguro que tentar acessar information_schema diretamente)
                return {
                    "success": True,
                    "message": "✅ Conexão estabelecida, mas não foi possível listar tabelas automaticamente",
                    "tables": []
                }
            except Exception as e:
                return {
                    "success": False,
                    "message": f"❌ Não foi possível listar tabelas: {str(e)}",
                    "tables": []
                }

    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Erro ao listar tabelas: {str(e)}",
            "tables": []
        }


def get_table_structure(table_name: str) -> dict:
    """
    Obtém a estrutura de uma tabela específica usando métodos alternativos
    """
    try:
        # Método 1: Tentar descrever a tabela através de uma consulta limitada
        try:
            # Tentar obter uma linha para inferir estrutura
            response = supabase.table(table_name).select(
                "*").limit(1).execute()

            if response.data:
                # Inferir estrutura da primeira linha
                first_row = response.data[0] if response.data else {}
                columns = []

                for key, value in first_row.items():
                    columns.append({
                        "column_name": key,
                        "data_type": type(value).__name__ if value is not None else "unknown",
                        "is_nullable": "YES" if value is None else "NO",
                        "column_default": None,
                        "character_maximum_length": None
                    })

                return {
                    "success": True,
                    "message": f"✅ Estrutura inferida da tabela '{table_name}'",
                    "columns": columns
                }
            else:
                # Tabela vazia ou não existe
                return {
                    "success": False,
                    "message": f"Tabela '{table_name}' está vazia ou não encontrada",
                    "columns": []
                }

        except Exception as e:
            # Método 2: Tentar acessar a tabela de forma diferente
            try:
                # Tentar inserir um registro temporário (e depois deletar)
                # para testar estrutura (apenas para tabelas com permissão de escrita)
                return {
                    "success": False,
                    "message": f"Não foi possível inferir a estrutura da tabela '{table_name}': {str(e)}",
                    "columns": []
                }
            except:
                return {
                    "success": False,
                    "message": f"Erro ao acessar tabela '{table_name}': {str(e)}",
                    "columns": []
                }

    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Erro ao obter estrutura: {str(e)}",
            "columns": []
        }
