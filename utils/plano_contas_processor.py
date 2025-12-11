# utils/plano_contas_processor.py

import streamlit as st
import pandas as pd

# IMPORTS DO SEU DB (ajuste se o nome for diferente)
from utils.plano_contas_db import importar_plano_contas


def _limpar_estado_pos_import():
    """Limpa keys relacionadas ao fluxo de import para evitar restos entre execuções."""
    keys = [
        "page",
        "empresa",
        "ano",
        "plano_nome",
        "plano_descricao",
        "arquivo_plano",
        "vigencia_verif",
        "confirmar_overwrite",
        "forcar_sobrescrita",
        "confirmar_required_for_vigencia",
    ]
    for k in keys:
        if k in st.session_state:
            try:
                del st.session_state[k]
            except Exception:
                pass


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


def run_processor():
    """
    Função que renderiza o 'processor' — essa função deve ser importada e chamada
    pela página principal quando st.session_state['page'] == 'processor'.
    """
    st.title("Importação do Plano de Contas")

    # Ler dados salvos na sessão pela página anterior
    empresa = st.session_state.get("empresa")
    ano = st.session_state.get("ano")
    nome = st.session_state.get("plano_nome")
    descricao = st.session_state.get("plano_descricao")
    # vigencia_id = st.session_state.get("vigencia_id")

    # Se não encontrar os dados essenciais — volta para a página anterior
    if not all([empresa, ano, nome, descricao]):
        st.error(
            "Dados do fluxo não encontrados na sessão. Retorne à página anterior e clique em Avançar novamente.")
        if st.button("← Voltar"):
            st.session_state["page"] = None
            st.experimental_rerun()
        st.stop()

    st.markdown("### Confirmação dos dados")
    st.write(f"- **Empresa:** {empresa}")
    st.write(f"- **Ano de Vigência:** {ano}")
    st.write(f"- **Nome do Plano:** {nome}")
    st.write(f"- **Descrição:** {descricao}")
    st.markdown("---")

    # controlar possível flag que indica que o usuário confirmou sobrescrita via diálogo
    forcar = st.session_state.get(
        "confirmar_overwrite", False) or st.session_state.get("forcar_sobrescrita", False)

    if forcar:
        st.info("Você confirmou sobrescrita da vigência existente.")

    # Uploader
    arquivo = st.file_uploader(
        "Selecione o arquivo do Plano de Contas (CSV, XLSX, XLS)",
        type=["csv", "xlsx", "xls"],
        accept_multiple_files=False,
        key="processor_file_uploader"
    )

    # persistir referência (opcional, facilita re-renders)
    if arquivo is not None:
        st.session_state["arquivo_plano"] = arquivo

    # mostrar preview (opcional)
    if arquivo is not None:
        try:
            if arquivo.name.lower().endswith(".csv"):
                df_preview = _tentar_ler_csv(arquivo)
                if df_preview is None:
                    st.error(
                        "Não foi possível ler o CSV automaticamente. Verifique encoding/separador.")
                else:
                    df_preview.columns = [str(c).strip()
                                          for c in df_preview.columns]
                    st.write(f"Preview do arquivo ({len(df_preview)} linhas):")
                    st.dataframe(df_preview.head(50))
            else:
                arquivo.seek(0)
                df_preview = pd.read_excel(arquivo, sheet_name=0, dtype=str)
                df_preview.columns = [str(c).strip()
                                      for c in df_preview.columns]
                st.write(f"Preview do arquivo ({len(df_preview)} linhas):")
                st.dataframe(df_preview.head(50))
        except Exception as e:
            st.warning(f"Preview não disponível: {e}")

    st.markdown("---")

    col_imp, col_back = st.columns([1, 1])
    with col_imp:
        importar = st.button("📥 Importar Plano", type="primary", disabled=(
            st.session_state.get("arquivo_plano") is None))
    with col_back:
        voltar = st.button("← Voltar para seleção")

    if voltar:
        # Apenas voltar: limpar flags relacionadas à navegação, manter os campos para editar
        st.session_state["page"] = None
        # opcional: manter plano/empresa/ano — não removo aqui
        st.rerun()
#        st.experimental_rerun()

    if importar:
        uploaded_file = st.session_state.get("arquivo_plano")
        if uploaded_file is None:
            st.error(
                "Nenhum arquivo encontrado. Selecione o arquivo antes de importar.")
            st.stop()

        # Vigência atual (se existia) — compatibilidade com o que a página anterior gravou
        vigencia_verif = st.session_state.get("vigencia_id", {})
        vigencia_id_atual = vigencia_verif.get(
            "vigencia_id") if vigencia_verif.get("existe") else None

        # vigencia_verif = st.session_state.get("vigencia_verif", {})
        # vigencia_id_atual = vigencia_verif.get(
        #    "vigencia_id") if vigencia_verif.get("existe") else None

        # Determinar se força sobrescrita
        forcar_sobrescrita = st.session_state.get(
            "confirmar_overwrite", False) or st.session_state.get("forcar_sobrescrita", False)

        # Chamar a função de importação (essa função deve existir em utils.plano_contas_db)
        try:
            with st.spinner("Importando plano de contas..."):
                resultado = importar_plano_contas(
                    empresa_nome=empresa if isinstance(
                        empresa, str) else str(empresa),
                    ano_vigencia=int(ano),
                    vigencia_id_atual=vigencia_id_atual,
                    uploaded_file=uploaded_file,
                    nome_plano=nome,
                    descricao_plano=descricao
                    # forcar_sobrescrita=forcar_sobrescrita
                )

            if resultado.get("success"):
                st.success(
                    f"✅ Plano importado com sucesso! Registros inseridos: {resultado.get('rows', 'N/D')}.")
                # Limpar estado do fluxo
                _limpar_estado_pos_import()
            else:
                st.error(
                    f"❌ Falha ao importar: {resultado.get('message', 'Erro desconhecido.')}")
        except Exception as e:
            st.exception(f"Erro inesperado durante importação: {e}")
