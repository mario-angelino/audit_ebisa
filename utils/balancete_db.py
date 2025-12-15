"""
balancete_db.py - Operações de banco de dados para balancetes
"""

from database import conectar, desconectar
import pandas as pd


def obter_empresa_id_por_razao_social(empresa):
    """
    Busca ID da empresa pelo nome da empresa

    Args:
        razao_social: razão social da empresa

    Returns:
        int com ID da empresa ou None
    """
    conn = None
    try:
        conn = conectar()
        cursor = conn.cursor()

        query = "SELECT cod_empresa FROM public.ebisa_empresa_sienge WHERE nome_empresa = %s"
        cursor.execute(query, (empresa,))

        resultado = cursor.fetchone()
        return resultado[0] if resultado else None

    except Exception as e:
        print(f"❌ Erro ao buscar empresa: {e}")
        return None
    finally:
        if conn:
            desconectar(conn)


def deletar_balancete_existente(empresa_id, mes, ano):
    """
    Deleta balancete existente (mesma empresa + mês + ano)
    Processo:
      1) Busca o id em ebisa_cont_balancete
      2) Deleta itens em ebisa_cont_balancete_itens
      3) Deleta o registro em ebisa_cont_balancete

    Args:
        empresa_id: ID da empresa
        mes: mês (1-12)
        ano: ano (ex: 2025)

    Returns:
        tuple (sucesso: bool, mensagem: str)
    """
    conn = None
    try:
        conn = conectar()
        cursor = conn.cursor()

        # --------------------------------------------------
        # 1) Buscar o balancete_id
        # --------------------------------------------------
        cursor.execute(
            """
            SELECT id
            FROM public.ebisa_cont_balancete
            WHERE empresa_id = %s
              AND mes = %s
              AND ano = %s
            LIMIT 1
            """,
            (empresa_id, mes, ano)
        )

        row = cursor.fetchone()

        if not row:
            conn.commit()
            return (True, "ℹ️ Nenhum balancete anterior encontrado")

        balancete_id = row[0]

        # --------------------------------------------------
        # 2) Deletar itens do balancete
        # --------------------------------------------------
        cursor.execute(
            """
            DELETE FROM public.ebisa_cont_balancete_itens
            WHERE balancete_id = %s
            """,
            (balancete_id,)
        )
        itens_deletados = cursor.rowcount

        # --------------------------------------------------
        # 3) Deletar balancete (cabeçalho)
        # --------------------------------------------------
        cursor.execute(
            """
            DELETE FROM public.ebisa_cont_balancete
            WHERE id = %s
            """,
            (balancete_id,)
        )

        conn.commit()

        return (
            True,
            f"🗑️ Balancete anterior deletado com sucesso "
            f"(itens removidos: {itens_deletados})"
        )

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Erro ao deletar balancete: {e}")
        return (False, f"❌ Erro ao deletar: {str(e)}")

    finally:
        if conn:
            desconectar(conn)


def inserir_balancete(empresa_id, mes, ano, df_itens, user):
    """
    Insere novo balancete (cabeçalho + itens)
    OTIMIZAÇÃO: Grava somente linhas com movimento (valores diferentes de zero)

    Args:
        empresa_id: ID da empresa
        mes: mês (1-12)
        ano: ano (ex: 2025)
        df_itens: DataFrame com os itens do balancete
        user: email do usuário que está importando

    Returns:
        tuple (sucesso: bool, mensagem: str, balancete_id: int ou None)
    """
    print(f"🔍 [DEBUG] inserir_balancete - Início")
    print(
        f"🔍 [DEBUG] empresa_id={empresa_id}, mes={mes}, ano={ano}, user={user}")
    print(f"🔍 [DEBUG] Total de linhas no DataFrame: {len(df_itens)}")

    conn = None
    try:
        conn = conectar()
        print(f"🔍 [DEBUG] Conexão estabelecida")
        cursor = conn.cursor()

        # 1. Inserir cabeçalho do balancete
        query_cabecalho = """
            INSERT INTO public.ebisa_cont_balancete (empresa_id, mes, ano, user_importacao)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """

        print(f"🔍 [DEBUG] Executando insert do cabeçalho...")
        cursor.execute(query_cabecalho, (empresa_id, mes, ano, user["email"]))
        balancete_id = cursor.fetchone()[0]
        print(f"🔍 [DEBUG] Cabeçalho inserido! balancete_id={balancete_id}")

        # 2. Inserir itens do balancete
        query_itens = """
            INSERT INTO public.ebisa_cont_balancete_itens (
                balancete_id, cod_conta, nome_conta,
                saldo_anterior, val_debito, val_credito, saldo_atual,
                cod_reduzido, cod_centro_custo, nome_centro_custo
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Preparar dados para inserção em lote
        itens_para_inserir = []
        linhas_ignoradas = 0

        print(f"🔍 [DEBUG] Iniciando processamento de itens...")
        for idx, row in df_itens.iterrows():
            # Converter valores para float
            saldo_anterior = float(row['saldo_anterior'])
            val_debito = float(row['val_debito'])
            val_credito = float(row['val_credito'])
            saldo_atual = float(row['saldo_atual'])

            # FILTRO: Gravar SOMENTE se pelo menos um valor for diferente de zero
            #if saldo_anterior != 0 or val_debito != 0 or val_credito != 0 or saldo_atual != 0:
            item = (
                balancete_id,
                row['cod_conta'],
                row['nome_conta'],
                saldo_anterior,
                val_debito,
                val_credito,
                saldo_atual,
                row['cod_reduzido'],
                row['cod_centro_custo'],
                row['nome_centro_custo']
            )
            itens_para_inserir.append(item)
            #else:
            #    linhas_ignoradas += 1

        print(
            f"🔍 [DEBUG] Itens processados: {len(itens_para_inserir)} para inserir")

        # Executar inserção em lote (somente linhas com movimento)
        if itens_para_inserir:
            print(
                f"🔍 [DEBUG] Executando insert em lote de {len(itens_para_inserir)} itens...")
            cursor.executemany(query_itens, itens_para_inserir)
            print(f"🔍 [DEBUG] Insert em lote concluído!")
        else:
            print(f"🔍 [DEBUG] Nenhum item para inserir!")

        print(f"🔍 [DEBUG] Executando commit...")
        conn.commit()
        print(f"🔍 [DEBUG] Commit realizado com sucesso!")

        mensagem = f"✅ Balancete importado! ID: {balancete_id}\n"
        mensagem += f"📊 {len(itens_para_inserir)} linhas gravadas"
        if linhas_ignoradas > 0:
            mensagem += f" | 🗑️ {linhas_ignoradas} linhas sem movimento ignoradas"

        print(f"🔍 [DEBUG] inserir_balancete - Sucesso! Retornando...")
        return (True, mensagem, balancete_id)

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ [DEBUG] ERRO em inserir_balancete: {e}")
        import traceback
        traceback.print_exc()
        return (False, f"❌ Erro ao inserir: {str(e)}", None)
    finally:
        if conn:
            desconectar(conn)
            print(f"🔍 [DEBUG] Conexão fechada")


def importar_balancete(empresa, mes, ano, df_itens, user):
    """
    Pipeline completo de importação:
    1. Buscar ID da empresa
    2. Deletar balancete existente
    3. Inserir novo balancete

    Args:
        razao_social: razão social da empresa
        mes: mês (1-12)
        ano: ano (ex: 2025)
        df_itens: DataFrame com os itens do balancete
        user_email: email do usuário que está importando

    Returns:
        tuple (sucesso: bool, mensagem: str)
    """
    print(f"🔍 [DEBUG] importar_balancete - Início")
    print(
        f"🔍 [DEBUG] empresa={empresa}, mes={mes}, ano={ano}, user={user}")

    # 1. Buscar ID da empresa
    print(f"🔍 [DEBUG] Buscando ID da empresa...")
    empresa_id = obter_empresa_id_por_razao_social(empresa)
    print(f"🔍 [DEBUG] empresa_id encontrado: {empresa_id}")

    if not empresa_id:
        print(f"❌ [DEBUG] Empresa não encontrada!")
        return (False, f"❌ Empresa '{empresa}' não encontrada no banco")

    # 2. Deletar balancete existente
    print(f"🔍 [DEBUG] Deletando balancete existente...")
    sucesso, msg_delete = deletar_balancete_existente(empresa_id, mes, ano)
    print(f"🔍 [DEBUG] Resultado delete: sucesso={sucesso}, msg={msg_delete}")

    if not sucesso:
        print(f"❌ [DEBUG] Erro ao deletar!")
        return (False, msg_delete)

    # 3. Inserir novo balancete
    print(f"🔍 [DEBUG] Chamando inserir_balancete...")
    sucesso, msg_insert, balancete_id = inserir_balancete(
        empresa_id, mes, ano, df_itens, user)
    print(
        f"🔍 [DEBUG] Resultado insert: sucesso={sucesso}, balancete_id={balancete_id}")

    if not sucesso:
        print(f"❌ [DEBUG] Erro ao inserir!")
        return (False, msg_insert)

    # Mensagem consolidada
    mensagem_final = f"{msg_delete}\n{msg_insert}"
    print(f"🔍 [DEBUG] importar_balancete_completo - Sucesso! Retornando...")

    return (True, mensagem_final)


def listar_balancetes(empresa="Todas", ano="Todos", mes="Todos"):
    """
    Lista balancetes com filtros opcionais

    Args:
        empresa: "Todas" ou razão social específica
        ano: "Todos" ou ano específico (ex: "2024")
        mes: "Todos" ou mês específico (ex: "11")

    Returns:
        DataFrame com colunas: nome_empresa, ano, mes, dt_importacao, user_importacao
    """
    conn = None
    try:
        conn = conectar()
        cursor = conn.cursor()

        # Query base
        query = """
            SELECT 
                nome_empresa,
                ano,
                mes,
                balancete_dt_importacao as dt_importacao,
                user_importacao
            FROM public.vw_cont_empresa_balancete
            WHERE 1=1
        """

        params = []

        # Aplicar filtros
        if empresa != "Todas":
            query += " AND nome_empresa = %s"
            params.append(empresa)

        if ano != "Todos":
            query += " AND ano = %s"
            params.append(int(ano))

        if mes != "Todos":
            query += " AND mes = %s"
            params.append(int(mes))

        # Ordenar
        query += " ORDER BY balancete_dt_importacao DESC, nome_empresa, ano DESC, mes DESC"

        cursor.execute(query, params)
        resultados = cursor.fetchall()

        # Converter para DataFrame
        df = pd.DataFrame(resultados, columns=[
            'Empresa',
            'Ano',
            'Mês',
            'Data Importação',
            'Usuário'
        ])

        return df

    except Exception as e:
        print(f"❌ Erro ao listar balancetes: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()
    finally:
        if conn:
            desconectar(conn)
