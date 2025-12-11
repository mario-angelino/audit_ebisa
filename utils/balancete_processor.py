import streamlit as st
import pandas as pd
import csv
from io import StringIO
from utils.balancete_db import importar_balancete
from utils.auth import require_authentication, get_current_user

# Verificar autenticação
require_authentication()

# Obter usuário atual
user = get_current_user()


def _limpar_estado_pos_import():
    """Limpa keys relacionadas ao fluxo de import para evitar restos entre execuções."""
    keys = [
        "page",
        "empresa",
        "ano",
        "mes",
        "arquivo",
    ]
    for k in keys:
        if k in st.session_state:
            try:
                del st.session_state[k]
            except Exception:
                pass


def ajustar_valor_por_classe(cod_conta: str, valor: float, tipo_dc: str) -> float:
    """
    Ajusta o valor conforme a classe contábil e o tipo D/C.
    cod_conta: código contábil (ex: '1.1.10.20.016')
    valor: valor numérico já convertido
    tipo_dc: 'D' ou 'C'
    """
    if not isinstance(valor, (int, float)):
        return 0.0

    classe = str(cod_conta).strip()[0]  # primeiro caractere

    if classe == "1":  # Ativo
        return valor if tipo_dc == "D" else -valor

    elif classe == "2":  # Passivo
        return valor if tipo_dc == "C" else -valor

    elif classe == "3":  # Receita
        return valor if tipo_dc == "C" else -valor

    elif classe == "4":  # Custo/Despesa
        return -valor if tipo_dc == "D" else valor

    elif classe == "5":  # Outros
        return valor if tipo_dc == "C" else -valor

    else:  # Classes acima de 5
        return valor if tipo_dc == "C" else -valor


def normalizar_float(valor_str: str) -> float:
    """
    Converte números no formato brasileiro '1.234,56' para 1234.56.
    """
    if not valor_str or not isinstance(valor_str, str):
        return 0.0

    valor_str = valor_str.replace(".", "").replace(",", ".").strip()

    try:
        return float(valor_str)
    except:
        return 0.0


def ler_arquivo_texto_resiliente(file_obj):
    tentativas = ["utf-8", "latin-1", "cp1252"]

    for enc in tentativas:
        try:
            file_obj.seek(0)
            texto = file_obj.read().decode(enc)
            return texto
        except Exception:
            continue

    raise ValueError(
        "Não foi possível ler o arquivo em nenhum encoding conhecido.")


def run_processor():
    """
    Função que renderiza o 'processor' — essa função deve ser importada e chamada
    pela página principal quando st.session_state['page'] == 'processor'.
    """
    st.title("Importação do Balancete")

    # Ler dados salvos na sessão pela página anterior
    empresa = st.session_state.get("empresa")
    ano = st.session_state.get("ano")
    mes = st.session_state.get("mes")
    formato = st.session_state.get("formato")

    # Se não encontrar os dados essenciais — volta para a página anterior
    if not all([empresa, ano, mes, formato]):
        st.error(
            "Dados do fluxo não encontrados na sessão. Retorne à página anterior e clique em Avançar novamente.")
        if st.button("← Voltar"):
            st.session_state["page"] = None
            st.experimental_rerun()
        st.stop()

    st.markdown("### Confirmação dos dados")
    st.write(f"- **Empresa:** {empresa}")
    st.write(f"- **Ano de Vigência:** {ano}")
    st.write(f"- **Mês de Vigência:** {mes}")
    st.markdown("---")

    # Uploader
    arquivo = st.file_uploader(
        "Selecione o arquivo do Balancete (CSV, XLSX, XLS)",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=False,
        key="processor_file_uploader"
    )

    # persistir referência (opcional, facilita re-renders)
    if arquivo is not None:
        st.session_state["arquivo"] = arquivo

        texto = ler_arquivo_texto_resiliente(arquivo)
        linhas = texto.splitlines()

        reader = csv.reader(linhas, delimiter=';')

        registros = []

        centro_codigo = None
        centro_nome = None
        dentro_tabela = False

        for linha in reader:

            # -------------------------------------------
            # Detectar bloco: Empresa
            # -------------------------------------------
            if linha and linha[0].strip().lower() == "empresa":
                nome_empresa_csv = linha[1].split(" - ", 1)[-1].strip()

                # validação simples (você disse que assume como igual)
                if nome_empresa_csv != empresa:
                    raise ValueError(
                        f"Empresa divergente no arquivo: {nome_empresa_csv}")

                continue

            # -------------------------------------------
            # Detectar bloco: Período
            # -------------------------------------------
            if linha and linha[0].strip().lower() == "período":
                periodo = linha[1]
                data_ini = periodo.split(" a ")[0].strip()
                dia, mes_csv, ano_csv = data_ini.split("/")

                if int(ano_csv) != int(ano) or int(mes_csv) != int(mes):
                    raise ValueError(
                        f"Período divergente no arquivo: {periodo}")

                continue

            # -------------------------------------------
            # Detectar Centro de custo
            # -------------------------------------------
            if linha and linha[0].strip().lower() == "centro de custo":
                cc_raw = linha[1]
                centro_codigo = cc_raw.split(" - ")[0].strip()
                centro_nome = cc_raw.split(" - ")[1].strip()
                dentro_tabela = False
                continue

            # -------------------------------------------
            # Detectar cabeçalho da tabela de contas
            # -------------------------------------------
            if linha and len(linha) > 3 and linha[0].strip().lower() == "cód. contábil":
                dentro_tabela = True
                continue

            # -------------------------------------------
            # Processar linhas de contas
            # -------------------------------------------
            if dentro_tabela:
                # Quando achamos outra palavra-chave, saímos do modo tabela
                if linha[0].strip().lower() in ["empresa", "período", "centro de custo"]:
                    dentro_tabela = False
                    continue

                # Linhas com código contábil possuem algo na coluna 0
                cod_conta = linha[0].strip()
                if not cod_conta:
                    continue

                cod_reduzido = linha[1].strip() if len(linha) > 1 else ""
                nome_conta = linha[2].strip() if len(linha) > 2 else ""

                saldo_anterior = normalizar_float(
                    linha[3]) if len(linha) > 3 else 0
                tipo_saldo_anterior = linha[4].strip() if len(
                    linha) > 4 else "D"

                val_debito = normalizar_float(
                    linha[5]) if len(linha) > 5 else 0
                val_credito = normalizar_float(
                    linha[6]) if len(linha) > 6 else 0

                saldo_atual = normalizar_float(
                    linha[7]) if len(linha) > 7 else 0
                tipo_saldo_atual = linha[8].strip() if len(linha) > 8 else "D"

                # aplicar regra DC
                saldo_anterior = ajustar_valor_por_classe(
                    cod_conta, saldo_anterior, tipo_saldo_anterior)
                saldo_atual = ajustar_valor_por_classe(
                    cod_conta, saldo_atual, tipo_saldo_atual)

                registros.append({
                    "cod_conta": cod_conta,
                    "nome_conta": nome_conta,
                    "saldo_anterior": saldo_anterior,
                    "val_debito": val_debito,
                    "val_credito": val_credito,
                    "saldo_atual": saldo_atual,
                    "cod_reduzido": int(cod_reduzido) if cod_reduzido.isdigit() else None,
                    "cod_centro_custo": int(centro_codigo),
                    "nome_centro_custo": centro_nome,
                })

        # DataFrame final unificado
        df_preview = pd.DataFrame(registros)

        df_preview.columns = [str(c).strip() for c in df_preview.columns]
        st.write(f"Preview do arquivo ({len(df_preview)} linhas):")
        st.dataframe(df_preview.head(1000))

    st.markdown("---")

    col_imp, col_back = st.columns([1, 1])
    with col_imp:
        importar = st.button("📥 Importar Balancete", type="primary", disabled=(
            st.session_state.get("arquivo") is None))
    with col_back:
        voltar = st.button("← Voltar para seleção")

    if voltar:
        # Apenas voltar: limpar flags relacionadas à navegação, manter os campos para editar
        st.session_state["page"] = None
        st.rerun()

    if importar:
        uploaded_file = st.session_state.get("arquivo")
        if uploaded_file is None:
            st.error(
                "Nenhum arquivo encontrado. Selecione o arquivo antes de importar.")
            st.stop()

        # Chamar a função de importação (essa função deve existir em utils.balancete_db)
        try:
            with st.spinner("Importando plano de contas..."):
                resultado = importar_balancete(
                    razao_social=empresa if isinstance(
                        empresa, str) else str(empresa),
                    mes=int(mes),
                    ano=int(ano),
                    df_itens=df_preview,
                    user_email=user
                )

            if resultado.get("success"):
                st.success(
                    f"✅ Balancete importado com sucesso! Registros inseridos: {resultado.get('rows', 'N/D')}.")
                # Limpar estado do fluxo
                _limpar_estado_pos_import()
            else:
                st.error(
                    f"❌ Falha ao importar: {resultado.get('message', 'Erro desconhecido.')}")
        except Exception as e:
            st.exception(f"Erro inesperado durante importação: {e}")
