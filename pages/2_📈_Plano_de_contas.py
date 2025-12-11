import streamlit as st
import pandas as pd
from utils.auth import require_authentication, get_current_user
from utils.plano_contas_db import listar_planos_empresa
from utils.plano_contas_processor import run_processor
from utils.empresa_db import (
    listar_empresas,
    buscar_empresas,
    cadastrar_empresa,
    buscar_empresa_por_cnpj
)

# ------------------------------------
# Navegação interna manual
# ------------------------------------
if st.session_state.get("page") == "processor":
    run_processor()  # executa sua "página interna"
    st.stop()        # impede o restante da página de carregar


# ---------------------------------------------------------
# Diálogo de confirmação — só é chamado quando necessário
# ---------------------------------------------------------
@st.dialog("⚠ Vigência existente")
def confirmar_sobrescrita():
    st.write("Já existe um plano de contas para esta empresa e ano.")
    st.write("Deseja sobrescrever os dados existentes?")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✔ Confirmar"):
            st.session_state["confirmar_overwrite"] = True
            st.session_state["page"] = "processor"
            st.rerun()

    with col2:
        if st.button("✖ Cancelar"):
            st.session_state["confirmar_overwrite"] = False
            st.rerun()


# Configuração da página
st.set_page_config(
    page_title="Plano de Contas - Audit Ebisa",
    page_icon="🏢",
    layout="wide"
)

# Verificar autenticação
require_authentication()

# Obter usuário atual
user = get_current_user()

# Header
st.title("🏢 Gestão de Planos de Contas")
st.markdown(f"**Usuário:** {user['nome']}")
st.markdown("---")

# Abas
tab1, tab2, tab3 = st.tabs(
    ["📋 Lista de Planos", "➕ Upload de Plano", "🔍 Buscar"])

# Tab 1: Lista de Planos
with tab1:
    st.subheader("📋 Planos de Contas Cadastrados")

    # Buscar empresas
    with st.spinner("Carregando empresas..."):

        # Buscar todas as empresas para o filtro
        df_empresas = listar_empresas()
        if not df_empresas.empty:
            df_empresas = df_empresas.copy()
            df_empresas["label"] = df_empresas["cod_empresa"].astype(
                str) + " - " + df_empresas["Empresa"].astype(str)
            empresas_lista = ["Todas"] + sorted(df_empresas["label"].tolist())
        else:
            empresas_lista = ["Todas"]

    # Filtros
    col1, col2, col3 = st.columns(3)

    with col1:
        filtro_empresa = st.selectbox(
            "Empresa",
            empresas_lista
        )

    with col2:
        pass

    with col3:
        pass

    st.markdown("---")

    # Ajustar valor a enviar para o filtro (manter lógica original de 'Todas')
    empresa_param = filtro_empresa if filtro_empresa == "Todas" else filtro_empresa.split(
        " - ", 1)[1]

    # Buscar balancetes com filtros aplicados
    df_planos = listar_planos_empresa(
        empresa=empresa_param
    )

    if df_planos.empty:
        st.warning(
            "⚠️ Nenhum plano de contas encontrado com os filtros selecionados.")
    else:
        # Formatar data de importação
        # df_balancetes["Data Importação"] = pd.to_datetime(
        #    df_balancetes["Data Importação"]
        # ).dt.strftime("%d/%m/%Y %H:%M")

        # Formatar mês com zero à esquerda
        # df_balancetes["Mês"] = df_balancetes["Mês"].apply(
        #    lambda x: str(x).zfill(2))

        # Exibir tabela
        st.dataframe(df_planos, width="stretch", hide_index=True)

        # Botões de ação
        col1, col2 = st.columns([1, 5])
        with col1:
            st.button("📥 Exportar", width="stretch")

# Tab 2: Novo Plano de Contas
with tab2:
    st.subheader("📤 Novo Plano de Contas")

    # Carregar empresas
    with st.spinner("Carregando empresas..."):
        df_emp_up = listar_empresas()

    if df_emp_up.empty:
        st.warning("⚠ Nenhuma empresa cadastrada.")
        st.stop()

    # Preparar labels
    df_emp_up = df_emp_up.copy()
    df_emp_up["label"] = df_emp_up["cod_empresa"].astype(
        str) + " - " + df_emp_up["Empresa"].astype(str)
    empresas_upload = sorted(df_emp_up["label"].tolist())

    col1, col2 = st.columns(2)

    with col1:
        empresa_sel = st.selectbox("Empresa", empresas_upload)
    
    with col2:
        ano_sel = st.selectbox("Ano de Vigência", [2025, 2024, 2023])

    # Nome e descrição
    c1, c2 = st.columns(2)
    with c1:
        nome_plano = st.text_input(
            "Nome do Plano", placeholder="Ex: Plano Contábil 2025")
    with c2:
        descricao_plano = st.text_input(
            "Descrição", placeholder="Breve descrição")

    st.markdown("---")

    # Botão Avançar
    avancar = st.button("➡️ Avançar", type="primary")

    if avancar:

        if not nome_plano or not descricao_plano:
            st.error("Informe nome e descrição do plano.")
            st.stop()

        # Salvar dados base no session_state
        st.session_state["empresa"] = empresa_sel
        st.session_state["ano"] = ano_sel
        st.session_state["plano_nome"] = nome_plano
        st.session_state["plano_descricao"] = descricao_plano

        # Consultar vigência existente
        from utils.plano_contas_db import verificar_vigencia_empresa_ano

        empresa_nome_tmp = empresa_sel.split(" - ", 1)[1]

        with st.spinner("Verificando vigência existente..."):
            existe = verificar_vigencia_empresa_ano(
                empresa_nome=empresa_nome_tmp,
                ano_vigencia=int(ano_sel)
            )
        print(f"[RESPOSTA-VERIFICAR-VIGENCIA] - existe: {existe}\n")

        if not existe.get("existe", False):
            st.session_state["page"] = "processor"
            st.rerun()
        else:
            st.session_state["vigencia_id"] = {
                "existe": True,
                "vigencia_id": existe.get("vigencia_id")
            }
            confirmar_sobrescrita()


# Tab 3: Buscar
with tab3:
    st.subheader("🔍 Buscar Plano de Contas")

    col1, col2 = st.columns([2, 3])

    with col1:
        tipo_busca = st.radio(
            "Buscar por:",
            ["Razão Social", "CNPJ", "Abreviação"],
            horizontal=False
        )

    with col2:
        termo_busca = st.text_input(
            "Digite o termo de busca:",
            placeholder=f"Digite {tipo_busca.lower()}...",
            key="termo_busca"
        )

        if st.button("🔍 Buscar", width="stretch", type="primary"):
            if not termo_busca:
                st.error("⚠️ Digite um termo para buscar!")
            else:
                # Mapear tipo de busca
                tipo_map = {
                    "Razão Social": "razao_social",
                    "CNPJ": "cnpj",
                    "Abreviação": "abreviacao"
                }

                with st.spinner(f"🔎 Buscando por {tipo_busca}..."):
                    df_resultado = buscar_empresas(
                        termo_busca, tipo_map[tipo_busca])

                st.markdown("---")

                if not df_resultado.empty:
                    st.success(
                        f"✅ Encontradas **{len(df_resultado)}** empresa(s)")

                    st.dataframe(
                        df_resultado,
                        width="stretch",
                        hide_index=True
                    )
                else:
                    st.warning("⚠️ Nenhum resultado encontrado.")
