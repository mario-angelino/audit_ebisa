import streamlit as st
from utils.auth import require_authentication, get_current_user
from utils.plano_contas_db import listar_planos_empresa
from utils.empresa_db import (
    listar_empresas,
    buscar_empresas,
    cadastrar_empresa,
    buscar_empresa_por_cnpj
)

# Configuração da página
st.set_page_config(
    page_title="Empresas - Audit Ebisa",
    page_icon="🏢",
    layout="wide"
)

# Verificar autenticação
require_authentication()

# Obter usuário atual
user = get_current_user()

# Header
st.title("🏢 Gestão de Empresas")
st.markdown(f"**Usuário:** {user['nome']}")
st.markdown("---")

# Abas
tab1, tab2, tab3, tab4 = st.tabs(
    ["📋 Lista de Empresas", "➕ Nova Empresa", ":page_with_curl: Plano de Contas", "🔍 Buscar"])

# Tab 1: Lista de Empresas
with tab1:
    st.subheader("📋 Empresas Cadastradas")

    # Filtros
    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        filtro_status = st.selectbox(
            "Status",
            ["Todas", "Ativas", "Inativas"],
            key="filtro_status"
        )

    with col2:
        st.markdown("<div style='height: 1.8rem;'></div>",
                    unsafe_allow_html=True)
        if st.button("🔄 Atualizar", width="stretch"):
            st.rerun()

    st.markdown("---")

    # Buscar empresas
    with st.spinner("Carregando empresas..."):
        if filtro_status == "Ativas":
            df_empresas = listar_empresas(filtro_status="ativa")
        elif filtro_status == "Inativas":
            df_empresas = listar_empresas(filtro_status="inativa")
        else:
            df_empresas = listar_empresas()

    if not df_empresas.empty:
        # Configurar colunas a exibir
        st.dataframe(
            df_empresas,
            width="stretch",
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", width="small"),
                # "Plano Contas ID": st.column_config.NumberColumn("Plano Contas", width="small"),
                "Abreviação": st.column_config.TextColumn("Abreviação", width="medium"),
                "Razão Social": st.column_config.TextColumn("Razão Social", width="large"),
                "CNPJ": st.column_config.TextColumn("CNPJ", width="medium"),
                "Controladora": st.column_config.TextColumn("Controladora", width="small"),
                "Controlada": st.column_config.TextColumn("Controlada", width="small"),
                "Operacional": st.column_config.TextColumn("Operacional", width="small"),
                "Patrimonial": st.column_config.TextColumn("Patrimonial", width="small"),
                "Ativa": st.column_config.TextColumn("Ativa", width="small")
            }
        )

        st.info(f"📊 **Total de empresas:** {len(df_empresas)}")

        # Botões de ação
        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            st.button("📥 Exportar Excel", width="stretch")
        with col2:
            st.button("📄 Exportar PDF", width="stretch")
    else:
        st.warning("⚠️ Nenhuma empresa encontrada.")

# Tab 2: Nova Empresa
with tab2:
    st.subheader("➕ Cadastrar Nova Empresa")

    with st.form("form_nova_empresa", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            cnpj = st.text_input(
                "CNPJ *",
                placeholder="00.000.000/0000-00",
                help="Digite apenas os números"
            )
            razao_social = st.text_input(
                "Razão Social *",
                placeholder="Nome completo da empresa"
            )
            abreviacao = st.text_input(
                "Abreviação *",
                placeholder="Nome curto",
                help="Nome curto para facilitar identificação"
            )
            plano_contas_id = st.number_input(
                "Plano de Contas ID",
                min_value=0,
                value=0,
                help="Deixe 0 se não tiver plano de contas"
            )

        with col2:
            st.markdown("#### Flags de Controle")

            fl_controladora = st.checkbox("✅ Controladora", value=False)
            fl_controlada = st.checkbox("✅ Controlada", value=False)
            fl_operacional = st.checkbox("✅ Operacional", value=False)
            fl_patrimonial = st.checkbox("✅ Patrimonial", value=False)

            st.markdown("---")

            fl_ativa = st.checkbox("✅ Ativa", value=True)
            fl_inativa = st.checkbox("❌ Inativa", value=False)

        st.markdown("---")

        col1, col2, col3 = st.columns([1, 1, 4])
        with col1:
            submit = st.form_submit_button(
                "💾 Cadastrar", width="stretch", type="primary")
        with col2:
            cancel = st.form_submit_button(
                "🚫 Limpar", width="stretch")

        if submit:
            # Validações
            if not cnpj or not razao_social or not abreviacao:
                st.error("⚠️ Preencha todos os campos obrigatórios (*)")
            else:
                # Validar CNPJ (apenas números)
                cnpj_limpo = ''.join(filter(str.isdigit, cnpj))

                if len(cnpj_limpo) != 14:
                    st.error("⚠️ CNPJ deve ter 14 dígitos!")
                else:
                    # Verificar se CNPJ já existe
                    empresa_existente = buscar_empresa_por_cnpj(cnpj_limpo)

                    if empresa_existente:
                        st.error(
                            f"⚠️ CNPJ já cadastrado para: **{empresa_existente['razao_social']}**")
                    else:
                        # Preparar dados
                        dados = {
                            'cnpj': cnpj_limpo,
                            'razao_social': razao_social,
                            'abreviacao': abreviacao,
                            'plano_contas_id': plano_contas_id if plano_contas_id > 0 else None,
                            'fl_controladora': fl_controladora,
                            'fl_controlada': fl_controlada,
                            'fl_operacional': fl_operacional,
                            'fl_patrimonial': fl_patrimonial,
                            'fl_ativa': fl_ativa,
                            'fl_inativa': fl_inativa
                        }

                        # Cadastrar
                        with st.spinner("Cadastrando empresa..."):
                            sucesso, mensagem, id_empresa = cadastrar_empresa(
                                dados)

                            if sucesso:
                                st.success(mensagem)
                                st.balloons()
                                st.info(f"🆔 ID da empresa: **{id_empresa}**")
                            else:
                                st.error(mensagem)

# Tab 3: Plano de Contas
with tab3:
    st.subheader(":page_with_curl: Plano de Contas")

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

        # Buscar todos os balancetes para extrair anos únicos
        # df_todos = listar_balancetes()
        # anos_unicos = ["Todos"] + sorted(df_todos["Ano"].unique(
        # ).tolist(), reverse=True) if not df_todos.empty else ["Todos"]
        anos_unicos = [2023, 2024, 2025]

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

# Tab 4: Buscar
with tab4:
    st.subheader("🔍 Buscar Empresa")

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
