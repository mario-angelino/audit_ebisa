"""
empresa_db.py - Funções de banco de dados para gestão de empresas
"""

import pandas as pd
from database import conectar, desconectar


def listar_empresas(filtro_status=None):
    """
    Lista todas as empresas cadastradas

    Args:
        filtro_status: 'ativa', 'inativa' ou None (todas)

    Returns:
        DataFrame com as empresas
    """
    conn = None
    try:
        conn = conectar()
        cursor = conn.cursor()

        # Query base
        query = """
            SELECT 
                cod_empresa,
                nome_empresa,
                cnpj_empresa,
                fl_ativo,
                fl_controladora,
                fl_controlada,
                fl_sede,
                fl_csr,
                fl_scp
            FROM public.ebisa_empresa_sienge
        """

        # Aplicar filtro de status
        if filtro_status == "ativa":
            query += " WHERE fl_ativo = true"
        elif filtro_status == "inativa":
            query += " WHERE fl_ativo = false"

        query += " ORDER BY cod_empresa"

        cursor.execute(query)
        resultados = cursor.fetchall()

        # Criar DataFrame
        colunas = [
            "cod_empresa", "Empresa", "CNPJ", "Ativa",
            "Controladora", "Controlada", "Sede", "Consórcio", "SCP"
        ]

        df = pd.DataFrame(resultados, columns=colunas)

        # Formatar campos booleanos
        bool_cols = ["Ativa", "Controladora",
                     "Controlada", "Sede", "Consórcio", "SCP"]
        for col in bool_cols:
            df[col] = df[col].apply(lambda x: "✅ Sim" if x else "❌ Não")

        return df

    except Exception as e:
        print(f"❌ Erro ao listar empresas: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            desconectar(conn)


def buscar_empresa_por_cnpj(cnpj):
    """
    Busca empresa pelo CNPJ

    Args:
        cnpj: CNPJ da empresa (com ou sem formatação)

    Returns:
        dict com dados da empresa ou None
    """
    conn = None
    try:
        conn = conectar()
        cursor = conn.cursor()

        # Remover formatação do CNPJ
        cnpj_limpo = ''.join(filter(str.isdigit, cnpj))

        query = """
            SELECT 
                cod_empresa,
                nome_empresa,
                cnpj_empresa,
                fl_ativo,
                fl_controladora,
                fl_controlada,
                fl_sede,
                fl_csr,
                fl_scp
            FROM public.ebisa_empresa_sienge
            WHERE cnpj = %s
        """

        cursor.execute(query, (cnpj_limpo,))
        resultado = cursor.fetchone()

        if resultado:
            return {
                "cod_empresa": resultado[0],
                "nome_empresa": resultado[1],
                "cnpj_empresa": resultado[2],
                "fl_ativo": resultado[3],
                "fl_controladora": resultado[4],
                "fl_controlada": resultado[5],
                "fl_sede": resultado[6],
                "fl_csr": resultado[7],
                "fl_scp": resultado[8]
            }

        return None

    except Exception as e:
        print(f"❌ Erro ao buscar empresa: {e}")
        return None
    finally:
        if conn:
            desconectar(conn)


def buscar_empresas(termo, tipo_busca="nome_empresa"):
    """
    Busca empresas por termo

    Args:
        termo: termo de busca
        tipo_busca: 'razao_social', 'cnpj', 'abreviacao'

    Returns:
        DataFrame com resultados
    """
    conn = None
    try:
        conn = conectar()
        cursor = conn.cursor()

        query = """
            SELECT 
                cod_empresa,
                nome_empresa,
                cnpj_empresa,
                fl_ativo,
                fl_controladora,
                fl_controlada,
                fl_sede,
                fl_csr,
                fl_scp
            FROM public.ebisa_empresa_sienge
            WHERE
        """

        if tipo_busca == "nome_empresa":
            query += " nome_empresa ILIKE %s"
            parametro = f"%{termo}%"
        elif tipo_busca == "cnpj":
            cnpj_limpo = ''.join(filter(str.isdigit, termo))
            query += " cnpj_empresa LIKE %s"
            parametro = f"%{cnpj_limpo}%"
        # elif tipo_busca == "abreviacao":
        #    query += " abreviacao ILIKE %s"
        #    parametro = f"%{termo}%"

        query += " ORDER BY nome_empresa"

        cursor.execute(query, (parametro,))
        resultados = cursor.fetchall()

        colunas = [
            "cod_empresa", "Empresa", "CNPJ", "Ativa",
            "Controladora", "Controlada", "Sede", "Consórcio", "SCP"
        ]

        df = pd.DataFrame(resultados, columns=colunas)

        # Formatar campos booleanos
        bool_cols = ["Ativa", "Controladora",
                     "Controlada", "Sede", "Consórcio", "SCP"]
        for col in bool_cols:
            df[col] = df[col].apply(lambda x: "✅ Sim" if x else "❌ Não")

        return df

    except Exception as e:
        print(f"❌ Erro ao buscar empresas: {e}")
        return pd.DataFrame()
    finally:
        if conn:
            desconectar(conn)


def cadastrar_empresa(dados):
    """
    Cadastra nova empresa

    Args:
        dados: dict com dados da empresa

    Returns:
        tuple (sucesso: bool, mensagem: str, id_empresa: int ou None)
    """
    conn = None
    try:
        conn = conectar()
        cursor = conn.cursor()

        # Validar CNPJ único
        cnpj_limpo = ''.join(filter(str.isdigit, dados['cnpj']))
        cursor.execute(
            "SELECT id FROM public.empresa WHERE cnpj = %s", (cnpj_limpo,))
        if cursor.fetchone():
            return (False, "❌ CNPJ já cadastrado!", None)

        # Inserir empresa
        query = """
            INSERT INTO public.empresa (
                plano_contas_id, abreviacao, razao_social, cnpj, cnpj_form,
                fl_controladora, fl_controlada, fl_operacional, fl_patrimonial,
                fl_ativa, fl_inativa
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            ) RETURNING id
        """

        # Formatar CNPJ
        cnpj_formatado = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:14]}"

        valores = (
            dados.get('plano_contas_id'),
            dados['abreviacao'],
            dados['razao_social'],
            cnpj_limpo,
            cnpj_formatado,
            dados.get('fl_controladora', False),
            dados.get('fl_controlada', False),
            dados.get('fl_operacional', False),
            dados.get('fl_patrimonial', False),
            dados.get('fl_ativa', True),
            dados.get('fl_inativa', False)
        )

        cursor.execute(query, valores)
        id_empresa = cursor.fetchone()[0]

        conn.commit()

        return (True, "✅ Empresa cadastrada com sucesso!", id_empresa)

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Erro ao cadastrar empresa: {e}")
        return (False, f"❌ Erro ao cadastrar: {str(e)}", None)
    finally:
        if conn:
            desconectar(conn)


def atualizar_empresa(id_empresa, dados):
    """
    Atualiza dados da empresa

    Args:
        id_empresa: ID da empresa
        dados: dict com dados a atualizar

    Returns:
        tuple (sucesso: bool, mensagem: str)
    """
    conn = None
    try:
        conn = conectar()
        cursor = conn.cursor()

        # Construir query dinâmica
        campos = []
        valores = []

        campos_permitidos = [
            'plano_contas_id', 'abreviacao', 'razao_social',
            'fl_controladora', 'fl_controlada', 'fl_operacional',
            'fl_patrimonial', 'fl_ativa', 'fl_inativa'
        ]

        for campo in campos_permitidos:
            if campo in dados:
                campos.append(f"{campo} = %s")
                valores.append(dados[campo])

        if not campos:
            return (False, "❌ Nenhum campo para atualizar!")

        valores.append(id_empresa)

        query = f"""
            UPDATE public.empresa
            SET {', '.join(campos)}
            WHERE id = %s
        """

        cursor.execute(query, valores)
        conn.commit()

        if cursor.rowcount > 0:
            return (True, "✅ Empresa atualizada com sucesso!")
        else:
            return (False, "❌ Empresa não encontrada!")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Erro ao atualizar empresa: {e}")
        return (False, f"❌ Erro ao atualizar: {str(e)}")
    finally:
        if conn:
            desconectar(conn)


def deletar_empresa(id_empresa):
    """
    Deleta empresa (soft delete - marca como inativa)

    Args:
        id_empresa: ID da empresa

    Returns:
        tuple (sucesso: bool, mensagem: str)
    """
    conn = None
    try:
        conn = conectar()
        cursor = conn.cursor()

        query = """
            UPDATE public.empresa
            SET fl_ativa = false, fl_inativa = true
            WHERE id = %s
        """

        cursor.execute(query, (id_empresa,))
        conn.commit()

        if cursor.rowcount > 0:
            return (True, "✅ Empresa inativada com sucesso!")
        else:
            return (False, "❌ Empresa não encontrada!")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Erro ao deletar empresa: {e}")
        return (False, f"❌ Erro ao deletar: {str(e)}")
    finally:
        if conn:
            desconectar(conn)
