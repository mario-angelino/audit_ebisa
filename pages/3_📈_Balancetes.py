import streamlit as st
from utils.auth import require_authentication, get_current_user
from utils.balancete_processor import run_processor
from utils.empresa_db import listar_empresas
# from utils.balancete_db import importar_balancete_completo
from utils.balancete_db import listar_balancetes

import pandas as pd
from datetime import datetime
import sys

import warnings
warnings.filterwarnings('ignore')

# ------------------------------------
# Navegação interna manual
# ------------------------------------
if st.session_state.get("page") == "processor":
    run_processor()  # executa sua "página interna"
    st.stop()        # impede o restante da página de carregar


# Configuração da página
st.set_page_config(
    page_title="Balancetes - Audit Ebisa",
    page_icon="📈",
    layout="wide"
)

# Verificar autenticação
require_authentication()

# Obter usuário atual
user = get_current_user()

# Header
st.title("📈 Gestão de Balancetes")
st.markdown(f"**Usuário:** {user['nome']}")
st.markdown("---")

# Abas
tab1, tab2, tab3 = st.tabs(
    ["📊 Balancetes Processados", "📤 Upload de Balancetes", "📋 Histórico"])

# Tab 1: Processados
with tab1:
    st.subheader("📊 Balancetes Processados")

    # Buscar empresas e anos únicos para os filtros
    with st.spinner("Carregando dados..."):

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
        filtro_ano = st.selectbox(
            "Ano",
            ["Todos", "2025", "2024", "2023"]
        )

    with col3:
        filtro_mes = st.selectbox(
            "Mês",
            ["Todos", "01", "02", "03", "04", "05",
                "06", "07", "08", "09", "10", "11", "12"]
        )

    st.markdown("---")

    # Ajustar valor a enviar para o filtro (manter lógica original de 'Todas')
    empresa_param = filtro_empresa if filtro_empresa == "Todas" else filtro_empresa.split(
        " - ", 1)[1]

    # Buscar balancetes com filtros aplicados
    df_balancetes = listar_balancetes(
        empresa=empresa_param,
        ano=filtro_ano,
        mes=filtro_mes
    )

    if df_balancetes.empty:
        st.warning("⚠️ Nenhum balancete encontrado com os filtros selecionados.")
    else:
        # Formatar data de importação
        df_balancetes["Data Importação"] = pd.to_datetime(
            df_balancetes["Data Importação"]
        ).dt.strftime("%d/%m/%Y %H:%M")

        # Formatar mês com zero à esquerda
        df_balancetes["Mês"] = df_balancetes["Mês"].apply(
            lambda x: str(x).zfill(2))

        # Exibir tabela
        st.dataframe(df_balancetes, width="stretch", hide_index=True)

        # Botões de ação
        col1, col2 = st.columns([1, 5])
        with col1:
            st.button("📥 Exportar", width="stretch")

# Tab 2: Upload
with tab2:
    st.subheader("📤 Upload de Balancetes")

    # Buscar empresas do banco
    with st.spinner("Carregando empresas..."):
        df_empresas = listar_empresas()

    if df_empresas.empty:
        st.warning("⚠️ Nenhuma empresa cadastrada. Cadastre empresas primeiro.")
    else:
        if not df_empresas.empty:
            df_empresas = df_empresas.copy()
            df_empresas["label"] = df_empresas["cod_empresa"].astype(
                str) + " - " + df_empresas["Empresa"].astype(str)
            empresas_lista = sorted(df_empresas["label"].tolist())
        else:
            empresas_lista = [""]

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            empresa = st.selectbox("Selecione a Empresa *", empresas_lista)

        with col2:
            ano_ref = st.selectbox("Ano de Referência *",
                                   ["2025", "2024", "2023", "2022"])

        with col3:
            mes_ref = st.selectbox(
                "Mês de Referência *", ["01", "02", "03", "04",
                                        "05", "06", "07", "08", "09", "10", "11", "12"])

        with col4:
            formato = st.selectbox(
                "Formato do Arquivo *", ["CSV (.csv)", "Excel (.xlsx)", "PDF (.pdf)"])

        st.markdown("---")

        # Botão Avançar
        avancar = st.button("➡️ Avançar", type="primary")

    if avancar:

        if not empresa or not ano_ref or not mes_ref:
            st.error("Informe dados do balancete.")
            st.stop()

        empresa_nome_tmp = empresa.split(" - ", 1)[1]

        # Salvar dados base no session_state
        st.session_state["empresa"] = empresa_nome_tmp
        st.session_state["ano"] = ano_ref
        st.session_state["mes"] = mes_ref
        st.session_state["formato"] = formato
        st.session_state["page"] = "processor"
        st.rerun()


# Tab 3: Histórico
with tab3:
    st.subheader("📋 Histórico Completo")

    # Filtro de data
    col1, col2 = st.columns(2)
    with col1:
        data_inicio = st.date_input("Data Início", datetime(2025, 1, 1))
    with col2:
        data_fim = st.date_input("Data Fim", datetime.now())

    st.markdown("---")

    # Timeline de atividades
    st.markdown("### 📅 Timeline de Atividades")

    activities = [
        {"data": "22/01/2025 14:30", "acao": "Upload de balancete",
            "empresa": "Empresa A", "usuario": "admin@empresa.com"},
        {"data": "21/01/2025 10:15", "acao": "Aprovação de balancete",
            "empresa": "Empresa B", "usuario": "admin@empresa.com"},
        {"data": "20/01/2025 16:45", "acao": "Upload de balancete",
            "empresa": "Empresa C", "usuario": "admin@empresa.com"}
    ]

    for act in activities:
        with st.container():
            col1, col2 = st.columns([1, 5])
            with col1:
                st.markdown(f"**{act['data']}**")
            with col2:
                st.markdown(
                    f"**{act['acao']}** - {act['empresa']} _(por {act['usuario']})_")
            st.markdown("---")
