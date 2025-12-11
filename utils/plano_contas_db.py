"""
plano_contas_db.py - Operações de banco de dados para planos de contas
"""

from database import conectar, desconectar
import pandas as pd
from psycopg2.extras import execute_values


def listar_planos_empresa(empresa="Todas"):
    """
    Lista planos de contas de todas as empresas, ou de uma empresa específica

    Args:
        empresa: Todas ou termo específico

    Returns:
        DataFrame com colunas: nome_empresa, ano_vigencia, plano_contas_id, nome, descricao
    """
    # print(f"[DEBUG-PLANO-CONTAS-DB] - PARAM empresa: {empresa}")
    conn = None
    try:
        conn = conectar()
        cursor = conn.cursor()

        # Query base
        query = """
            SELECT 
                empresa_id,
                nome_empresa,
                ano_vigencia,
                plano_contas_id,
                nome,
                descricao,
                fl_ativo
            FROM public.vw_cont_empresas_planocontas
            WHERE 1=1
        """

        params = []

        # Aplicar filtros
        if empresa != "Todas":
            query += " AND nome_empresa = %s"
            params.append(empresa)

        # Ordenar
        query += " ORDER BY nome_empresa DESC, ano_vigencia DESC"

        cursor.execute(query, params)
        resultados = cursor.fetchall()

        # Converter para DataFrame
        df = pd.DataFrame(resultados, columns=[
            'Código Empresa',
            'Nome Empresa',
            'Ano Vigência',
            'ID Plano',
            'Nome',
            'Descrição',
            'Ativo'
        ])

        # Formatar campos booleanos
        bool_cols = ["Ativo"]
        for col in bool_cols:
            df[col] = df[col].apply(lambda x: "✅ Sim" if x else "❌ Não")

        return df

    except Exception as e:
        print(f"❌ Erro ao listar planos de contas: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()
    finally:
        if conn:
            desconectar(conn)


def verificar_vigencia_empresa_ano(empresa_nome: str, ano_vigencia: int) -> dict:
    """
    Verifica se existe uma vigência ATIVA para a empresa e ano informados.
    Retorna: {"existe": bool, "vigencia_id": int|None, "plano_contas_id": int|None, "empresa_id": int|None}
    """
    conn = None
    try:
        conn = conectar()
        cur = conn.cursor()

        # Obter empresa_id a partir da view já utilizada no projeto
        print(
            f"[verificar_vigencia_empresa_ano] - empresa_nome: {empresa_nome}, ano_vigencia: {ano_vigencia}\n")
        cur.execute(
            """
            SELECT DISTINCT empresa_id
            FROM public.vw_cont_empresas_planocontas
            WHERE nome_empresa = %s
            LIMIT 1
            """,
            (empresa_nome,)
        )
        row_emp = cur.fetchone()
        empresa_id = row_emp[0] if row_emp else None

        if not empresa_id:
            return {"existe": False, "vigencia_id": None, "plano_contas_id": None, "empresa_id": None}

        # Verificar vigência ativa para o ano informado
        cur.execute(
            """
            SELECT id, plano_contas_id
            FROM public.ebisa_cont_plano_contas_vigencia
            WHERE empresa_id = %s
              AND ano_vigencia = %s
              AND fl_ativo = TRUE
            LIMIT 1
            """,
            (empresa_id, ano_vigencia)
        )
        print(
            f"[CONSULTA-TABELA-VIGENCIA] - empresa_id: {empresa_id}, ano_vigencia: {ano_vigencia}\n")
        row_vig = cur.fetchone()
        print(f"[RESULTADO-DA-CONSULTA] - row_vig: {row_vig}\n")

        if row_vig:
            return {
                "existe": True,
                "vigencia_id": row_vig[0],
                "plano_contas_id": row_vig[1],
                "empresa_id": empresa_id
            }

        return {"existe": False, "vigencia_id": None, "plano_contas_id": None, "empresa_id": empresa_id}

    except Exception as e:
        print(f"❌ Erro em verificar_vigencia_empresa_ano: {e}")
        return {"existe": False, "vigencia_id": None, "plano_contas_id": None, "empresa_id": None}
    finally:
        if conn:
            desconectar(conn)


def _coerce_bool(val):
    """
    Converte diferentes representações em boolean.
    Aceita: 'true','false','1','0','s','n','y','n','sim','nao','não', 1, 0, True, False
    """
    if val is None:
        return False
    if isinstance(val, bool):
        return val
    s = str(val).strip().lower()
    if s in ("true", "t", "1", "y", "yes", "s", "sim"):
        return True
    if s in ("false", "f", "0", "n", "no", "nao", "não"):
        return False
    return False


def _tentar_ler_csv(file_obj):
    """Leitura resiliente de CSV — retorna DataFrame ou None."""
    tentativas = [
        ("utf-8", ";"),
        ("utf-8", ","),
        ("latin-1", ";"),
        ("latin-1", ","),
        ("cp1252", ";"),
        ("cp1252", ","),
    ]
    for enc, sep in tentativas:
        try:
            file_obj.seek(0)
            df = pd.read_csv(file_obj, sep=sep, dtype=str,
                             encoding=enc, engine="python")
            return df
        except Exception:
            continue
    return None


def importar_plano_contas(
    empresa_nome: str,
    ano_vigencia: int,
    vigencia_id_atual: int | None,
    uploaded_file,
    nome_plano: str,
    descricao_plano: str
) -> dict:

    print(f"[DEBUG-IMPORTAR-PLANO] - Entrou")
    print(f"[DEBUG-IMPORTAR-PLANO] - vigencia_id_atual: {vigencia_id_atual}\n")
    empresa_nome_tmp = empresa_nome.split(" - ", 1)[1]

    conn = None
    try:
        # ------------------------------------------------------------------
        # 0) Ler arquivo para DF
        # ------------------------------------------------------------------
        if uploaded_file is None:
            return {"success": False, "message": "Arquivo não informado."}

        try:
            uploaded_file.seek(0)
        except Exception:
            pass

        # CSV com tentativas múltiplas
        df = None
        if uploaded_file.name.lower().endswith(".csv"):
            df = _tentar_ler_csv(uploaded_file)
            if df is None:
                return {
                    "success": False,
                    "message": "Erro ao ler CSV (codificações/sep testados sem sucesso)."
                }
        else:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file, sheet_name=0, dtype=str)

        df.columns = [str(c).strip() for c in df.columns]

        # ------------------------------------------------------------------
        # 1) Mapeamento inteligente dos nomes das colunas
        # ------------------------------------------------------------------
        MAP_COLS = {
            "cod_conta": ["Código Contábil", "cod_conta", "Código da Conta", "Conta", "CodConta", "Código"],
            "nome_conta": ["Descrição", "nome_conta", "Nome da Conta", "Descricao", "Conta Nome"],
            "cod_reduzido": ["cod_reduzido", "Código Reduzido", "Reduzido", "CodReduzido"],
            "grupo_contas": ["Grupo de conta", "grupo_contas", "Grupo", "Grupo Contábil", "GrupoConta"],
            "tipo_conta": ["Tipo de Conta"],
            "usar_no_balanco": ["Usar no balanço patrimonial"],
            "permite_rateio": ["Permite Rateio"],
            "redutora": ["Redutora"],
            "data_cadastramento": ["Data Cadastramento"],
            "conta_referencial": ["Conta referencial"],
            "codigo_evento": ["Código do evento"],
            "fl_ativa": ["fl_ativa", "Ativa", "Ativo", "Status", "Conta Ativa"],
        }

        # 1) Normalizar cabeçalhos via rotina externa
        df = normalizar_cabecalhos(df, MAP_COLS)

        # Garantir que campos essenciais existam
        obrigatorias = ["cod_conta", "nome_conta",
                        "cod_reduzido", "grupo_contas", "fl_ativa"]
        faltantes = [c for c in obrigatorias if c not in df.columns]

        if faltantes:
            return {
                "success": False,
                "message": (
                    "Arquivo inválido. Faltam colunas obrigatórias após normalização.\n"
                    f"Faltando: {', '.join(faltantes)}\n"
                    f"Colunas finais do DF: {', '.join(df.columns)}"
                )
            }

        # ------------------------------------------------------------------
        # 2) Normalizações internas
        # ------------------------------------------------------------------
        df["cod_conta"] = df["cod_conta"].astype(str).str.strip()
        df["nome_conta"] = df["nome_conta"].astype(str).str.strip()

        def _to_int_or_none(x):
            if x is None or (isinstance(x, str) and x.strip() == ""):
                return None
            try:
                return int(str(x).split(".")[0])
            except Exception:
                return None

        df["cod_reduzido"] = df["cod_reduzido"].apply(_to_int_or_none)
        df["grupo_contas"] = df["grupo_contas"].apply(_to_int_or_none)
        df["fl_ativa"] = df["fl_ativa"].apply(_coerce_bool)

        # Remover linhas inválidas
        df = df[
            df["cod_conta"].ne("") &
            df["nome_conta"].ne("") &
            df["cod_reduzido"].notna() &
            df["grupo_contas"].notna()
        ].copy()

        if df.empty:
            return {
                "success": False,
                "message": "Nenhuma linha válida encontrada após validação."
            }

        # Campos opcionais padronizados
        opt_cols = [
            "tipo_conta", "usar_no_balanco", "permite_rateio", "redutora",
            "conta_referencial", "data_cadastramento", "codigo_evento"
        ]
        for oc in opt_cols:
            if oc not in df.columns:
                df[oc] = None

        df["data_cadastramento"] = df["data_cadastramento"].apply(_to_date)

        # ------------------------------------------------------------------
        # 3) Conectar banco
        # ------------------------------------------------------------------
        conn = conectar()
        cur = conn.cursor()

        print(f"[DEBUG-OBTER-EMPRESA-ID] empresa_nome: {empresa_nome_tmp}\n")
        # Obter empresa_id
        cur.execute(
            """
            SELECT DISTINCT cod_empresa
            FROM public.ebisa_empresa_sienge
            WHERE nome_empresa = %s
            LIMIT 1
            """,
            (empresa_nome_tmp,)
        )
        row_emp = cur.fetchone()
        if not row_emp:
            return {"success": False, "message": f"Empresa '{empresa_nome_tmp}' não encontrada."}
        empresa_id = row_emp[0]

        # ------------------------------------------------------------------
        # 4) Inserir plano de contas (cabeçalho)
        # ------------------------------------------------------------------
        cur.execute(
            """
            INSERT INTO public.ebisa_cont_plano_contas (nome, descricao)
            VALUES (%s, %s)
            RETURNING id
            """,
            (nome_plano, descricao_plano)
        )
        plano_contas_id = cur.fetchone()[0]

        # ------------------------------------------------------------------
        # 5) Inserir itens com UPSERT
        # ------------------------------------------------------------------
        rows = []
        for _, r in df.iterrows():
            rows.append((
                r["cod_conta"],
                r["nome_conta"],
                int(r["cod_reduzido"]),
                int(r["grupo_contas"]),
                r.get("tipo_conta"),
                r.get("usar_no_balanco"),
                r.get("permite_rateio"),
                r.get("redutora"),
                r.get("conta_referencial"),
                bool(r["fl_ativa"]),
                plano_contas_id,
                r.get("data_cadastramento"),
                r.get("codigo_evento"),
            ))

        insert_sql = """
            INSERT INTO public.ebisa_cont_plano_contas_itens
            (cod_conta, nome_conta, cod_reduzido, grupo_contas,
             tipo_conta, usar_no_balanco, permite_rateio, redutora,
             conta_referencial, fl_ativa, plano_contas_id,
             data_cadastramento, codigo_evento)
            VALUES %s
            ON CONFLICT (plano_contas_id, cod_conta) DO UPDATE SET
                nome_conta = EXCLUDED.nome_conta,
                cod_reduzido = EXCLUDED.cod_reduzido,
                grupo_contas = EXCLUDED.grupo_contas,
                tipo_conta = EXCLUDED.tipo_conta,
                usar_no_balanco = EXCLUDED.usar_no_balanco,
                permite_rateio = EXCLUDED.permite_rateio,
                redutora = EXCLUDED.redutora,
                conta_referencial = EXCLUDED.conta_referencial,
                fl_ativa = EXCLUDED.fl_ativa,
                plano_contas_id = EXCLUDED.plano_contas_id,
                data_cadastramento = EXCLUDED.data_cadastramento,
                codigo_evento = EXCLUDED.codigo_evento
        """

        execute_values(cur, insert_sql, rows, page_size=500)

        # ------------------------------------------------------------------
        # 6) Inativar vigência anterior, se houver
        # ------------------------------------------------------------------
        if vigencia_id_atual:
            cur.execute(
                "UPDATE public.ebisa_cont_plano_contas_vigencia SET fl_ativo = FALSE WHERE id = %s",
                (vigencia_id_atual,)
            )

        # ------------------------------------------------------------------
        # 7) Criar nova vigência
        # ------------------------------------------------------------------
        cur.execute(
            """
            INSERT INTO public.ebisa_cont_plano_contas_vigencia
                (empresa_id, plano_contas_id, ano_vigencia, fl_ativo)
            VALUES (%s, %s, %s, TRUE)
            RETURNING id
            """,
            (empresa_id, plano_contas_id, ano_vigencia)
        )
        nova_vigencia_id = cur.fetchone()[0]

        conn.commit()

        return {
            "success": True,
            "message": "Plano importado e vigência atualizada com sucesso.",
            "rows": len(rows),
            "plano_contas_id": plano_contas_id,
            "vigencia_id": nova_vigencia_id
        }

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Erro em importar_plano_contas: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "message": str(e)}

    finally:
        if conn:
            desconectar(conn)


def normalizar_cabecalhos(df: pd.DataFrame, MAP_COLS: dict) -> pd.DataFrame:
    """
    Recebe um DataFrame recém lido e normaliza seus cabeçalhos usando MAP_COLS.
    - Renomeia para o nome padrão esperado pelo banco (ex: 'cod_conta').
    - Exclui colunas que não correspondem a nenhuma chave do MAP_COLS.
    - Imprime no terminal os nomes das colunas removidas.
    """

    # Normalizador interno
    def clean(s: str) -> str:
        return (
            str(s).strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
            .replace("ç", "c")
            .replace("ã", "a")
            .replace("â", "a")
            .replace("á", "a")
            .replace("é", "e")
            .replace("ê", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ô", "o")
            .replace("ú", "u")
        )

    # Mapeia as colunas do df já normalizadas -> original
    df_cols_clean = {clean(c): c for c in df.columns}

    # Agora criamos o rename_map (original → nome interno)
    rename_map = {}
    colunas_utilizadas = set()

    for nome_interno, alternativas in MAP_COLS.items():
        for alt in alternativas:
            alt_clean = clean(alt)
            if alt_clean in df_cols_clean:
                origem = df_cols_clean[alt_clean]
                rename_map[origem] = nome_interno
                colunas_utilizadas.add(origem)
                break

    # Identificar colunas que não entraram no mapeamento
    colunas_excluidas = [c for c in df.columns if c not in colunas_utilizadas]

    if colunas_excluidas:
        print("\n[INFO] Colunas ignoradas (não correspondem ao MAP_COLS):")
        for c in colunas_excluidas:
            print(f"  - {c}")

        # remover colunas desconhecidas
        df = df.drop(columns=colunas_excluidas)

    # Renomear as colunas restantes para o padrão interno
    df = df.rename(columns=rename_map)

    return df


def _to_date(x):
    if not x or str(x).strip() == "":
        return None
    try:
        return pd.to_datetime(x).date()
    except:
        return None
