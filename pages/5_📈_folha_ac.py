import streamlit as st
import pandas as pd
import plotly.express as px
import database  # Seu módulo de conexão

# Configuração da Página
st.set_page_config(page_title="Dashboard Anual RH", layout="wide")

# --- FUNÇÕES DE CARREGAMENTO ---

@st.cache_data(ttl=600)
def get_anos_disponiveis():
    """Busca apenas os anos distintos para o filtro inicial"""
    conn = database.conectar()
    query = "SELECT DISTINCT ano FROM public.ebisa_tab_folha ORDER BY ano DESC"
    try:
        df = pd.read_sql(query, conn)
        return df['ano'].tolist()
    finally:
        database.desconectar(conn)

@st.cache_data(ttl=600)
def get_dados_anuais(ano):
    """
    Busca TODOS os dados do ano selecionado.
    Trazemos o ano todo para permitir filtros rápidos de Centro de Custo via Pandas
    sem recarregar o banco a cada clique.
    """
    conn = database.conectar()
    query = """
    SELECT 
        mes, 
        nome_centro_custo_rh, 
        cod_funcionario, 
        nome_cargo,
        proventos_total, 
        liquido, 
        valor_fgts,
        descontos_total
    FROM public.ebisa_tab_folha 
    WHERE ano = %s
    ORDER BY mes ASC
    """
    try:
        df = pd.read_sql(query, conn, params=(int(ano),))
        return df
    finally:
        database.desconectar(conn)

# --- SIDEBAR: FILTROS ---
st.sidebar.title("📊 Filtros Gerenciais")

# 1. Seleção de Ano
anos = get_anos_disponiveis()
if not anos:
    st.error("Nenhum dado encontrado.")
    st.stop()

ano_sel = st.sidebar.selectbox("Selecione o Ano", anos)

# 2. Carrega dados do Ano
df_ano = get_dados_anuais(ano_sel)

# 3. Seleção de Centro de Custo
lista_cc = ["Todos"] + sorted(df_ano['nome_centro_custo_rh'].unique().tolist())
cc_sel = st.sidebar.selectbox("Centro de Custo", lista_cc)

# --- FILTRAGEM DOS DADOS ---
if cc_sel != "Todos":
    df_filtrado = df_ano[df_ano['nome_centro_custo_rh'] == cc_sel]
    titulo_dash = f"Análise Anual Ebisa: {cc_sel} ({ano_sel})"
else:
    df_filtrado = df_ano
    titulo_dash = f"Análise Anual Ebisa: Visão Geral da Empresa ({ano_sel})"

# --- DASHBOARD ---

st.title(titulo_dash)
st.markdown("---")

if df_filtrado.empty:
    st.warning("Sem dados para esta seleção.")
else:
    # --- 1. KPIs ACUMULADOS ---
    # Cálculos
    total_bruto_anual = df_filtrado['proventos_total'].sum()
    total_liquido_anual = df_filtrado['liquido'].sum()
    total_fgts_anual = df_filtrado['valor_fgts'].sum()
    
    # Para headcount anual, a soma não faz sentido. Usamos a MÉDIA MENSAL de funcionários.
    headcount_por_mes = df_filtrado.groupby('mes')['cod_funcionario'].nunique()
    media_headcount = int(headcount_por_mes.mean())
    
    # Layout dos KPIs
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💰 Acumulado Bruto (Ano)", f"R$ {total_bruto_anual:,.2f}")
    k2.metric("💸 Acumulado Líquido (Ano)", f"R$ {total_liquido_anual:,.2f}")
    k3.metric("🏦 Acumulado FGTS (Ano)", f"R$ {total_fgts_anual:,.2f}")
    k4.metric("👥 Média de Funcionários/Mês", media_headcount)

    st.markdown("---")

    # --- 2. EVOLUÇÃO MENSAL (GRÁFICOS DE LINHA/ÁREA) ---
    st.subheader(f"📈 Evolução Financeira Mensal - {ano_sel}")
    
    # Agrupando por mês
    df_evolucao = df_filtrado.groupby('mes')[['proventos_total', 'liquido', 'valor_fgts']].sum().reset_index()
    
    # Gráfico de Área (Bruto vs Líquido)
    fig_evolucao = px.area(
        df_evolucao, 
        x='mes', 
        y=['proventos_total', 'liquido'],
        labels={'value': 'Valor (R$)', 'mes': 'Mês', 'variable': 'Tipo'},
        color_discrete_map={'proventos_total': '#1f77b4', 'liquido': '#2ca02c'}
    )
    fig_evolucao.update_layout(xaxis=dict(tickmode='linear', tick0=1, dtick=1)) # Garante mostrar todos os meses
    st.plotly_chart(fig_evolucao, use_container_width=True)

    # --- 3. ANÁLISE COMPARATIVA ---
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("👥 Evolução do Headcount (Funcionários)")
        # Gráfico de Linha para Headcount
        df_hc = df_filtrado.groupby('mes')['cod_funcionario'].nunique().reset_index()
        df_hc.columns = ['mes', 'qtd_funcionarios']
        
        fig_hc = px.line(
            df_hc, 
            x='mes', 
            y='qtd_funcionarios',
            markers=True,
            line_shape='spline', # Linha suave
            color_discrete_sequence=['#ff7f0e']
        )
        fig_hc.update_layout(yaxis_title="Qtd. Ativos", xaxis=dict(tickmode='linear', tick0=1, dtick=1))
        st.plotly_chart(fig_hc, use_container_width=True)

    with c2:
        st.subheader("💼 Top 5 Cargos (Custo Anual)")
        # Quais cargos custaram mais no ano acumulado?
        df_cargos = df_filtrado.groupby('nome_cargo')['proventos_total'].sum().reset_index()
        df_cargos = df_cargos.sort_values(by='proventos_total', ascending=True).tail(5)
        
        fig_cargos = px.bar(
            df_cargos,
            x='proventos_total',
            y='nome_cargo',
            orientation='h',
            text_auto='.2s',
            color='proventos_total',
            color_continuous_scale='Reds'
        )
        fig_cargos.update_layout(xaxis_title="Custo Total Anual", yaxis_title="")
        st.plotly_chart(fig_cargos, use_container_width=True)

    # --- 4. DETALHAMENTO MENSAL (TABELA PIVOT) ---
    st.subheader("📅 Resumo Mensal (Tabela)")
    
    # Criando uma tabela pivotada para fácil leitura
    pivot_table = df_filtrado.groupby('mes').agg({
        'proventos_total': 'sum',
        'liquido': 'sum',
        'valor_fgts': 'sum',
        'cod_funcionario': 'nunique'
    }).reset_index()
    
    pivot_table.columns = ['Mês', 'Total Bruto', 'Total Líquido', 'Total FGTS', 'Qtd Funcionários']
    
    st.dataframe(
        pivot_table.style.format({
            'Total Bruto': 'R$ {:,.2f}',
            'Total Líquido': 'R$ {:,.2f}',
            'Total FGTS': 'R$ {:,.2f}',
            'Qtd Funcionários': '{:.0f}'
        }),
        use_container_width=True,
        hide_index=True
    )