import streamlit as st
import pandas as pd
import plotly.express as px
import database  # Importa o seu módulo de conexão

# Configuração da Página
st.set_page_config(page_title="Dashboard RH", layout="wide")

# --- FUNÇÕES DE CARREGAMENTO DE DADOS ---

@st.cache_data(ttl=600) # Cache por 10 minutos
def get_periodos_disponiveis():
    """Busca apenas os anos e meses distintos para o filtro"""
    conn = database.conectar()
    query = """
    SELECT DISTINCT ano, mes 
    FROM public.ebisa_tab_folha 
    ORDER BY ano DESC, mes DESC
    """
    try:
        df = pd.read_sql(query, conn)
        return df
    finally:
        database.desconectar(conn)

@st.cache_data(ttl=600)
def get_dados_folha(ano, mes):
    """Busca os dados completos apenas do período selecionado"""
    conn = database.conectar()
    query = """
    SELECT * 
    FROM public.ebisa_tab_folha 
    WHERE ano = %s AND mes = %s
    """
    try:
        # O pandas lida bem com a parametrização do psycopg2
        df = pd.read_sql(query, conn, params=(int(ano), int(mes)))
        return df
    finally:
        database.desconectar(conn)

# --- INTERFACE: SIDEBAR (FILTROS) ---
st.sidebar.title("Filtros da Folha")

# 1. Carrega datas disponíveis
df_datas = get_periodos_disponiveis()

if df_datas.empty:
    st.error("Não há dados na tabela de folha.")
    st.stop()

# 2. Seletores de Ano e Mês
lista_anos = df_datas['ano'].unique()
ano_sel = st.sidebar.selectbox("Ano", lista_anos)

# Filtra meses baseados no ano selecionado
lista_meses = df_datas[df_datas['ano'] == ano_sel]['mes'].unique()
mes_sel = st.sidebar.selectbox("Mês", lista_meses)

# 3. Botão de Atualizar (Opcional, mas bom para UX)
if st.sidebar.button("Atualizar Dados"):
    st.cache_data.clear()

# --- CARREGAMENTO DOS DADOS PRINCIPAIS ---
df = get_dados_folha(ano_sel, mes_sel)

# Filtro Adicional de Centro de Custo (Feito no Pandas para ser rápido)
centros_custo = ["Todos"] + list(df['nome_centro_custo_rh'].unique())
cc_sel = st.sidebar.selectbox("Centro de Custo / Depto", centros_custo)

if cc_sel != "Todos":
    df = df[df['nome_centro_custo_rh'] == cc_sel]

# --- DASHBOARD PRINCIPAL ---

st.title(f"📊 Dashboard de Folha - {mes_sel}/{ano_sel}")
st.markdown("---")

if df.empty:
    st.warning("Nenhum dado encontrado para os filtros selecionados.")
else:
    # --- 1. KPIs (INDICADORES) ---
    col1, col2, col3, col4 = st.columns(4)
    
    total_bruto = df['proventos_total'].sum()
    total_liquido = df['liquido'].sum()
    total_fgts = df['valor_fgts'].sum()
    headcount = df['cod_funcionario'].nunique()
    
    col1.metric("💰 Custo Total (Bruto)", f"R$ {total_bruto:,.2f}")
    col2.metric("💸 Total Líquido", f"R$ {total_liquido:,.2f}")
    col3.metric("🏦 Total FGTS", f"R$ {total_fgts:,.2f}")
    col4.metric("👥 Funcionários (Headcount)", headcount)

    st.markdown("---")

    # --- 2. GRÁFICOS ---
    
    # Linha superior de gráficos
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Top 10 Centros de Custo (Valor Bruto)")
        # Agrupamento
        df_cc = df.groupby('nome_centro_custo_rh')[['proventos_total']].sum().reset_index()
        df_cc = df_cc.sort_values(by='proventos_total', ascending=True).tail(10) # Top 10
        
        fig_bar = px.bar(
            df_cc, 
            x='proventos_total', 
            y='nome_centro_custo_rh', 
            orientation='h',
            text_auto='.2s',
            color='proventos_total',
            color_continuous_scale='Blues'
        )
        fig_bar.update_layout(xaxis_title="Total Proventos", yaxis_title="")
        st.plotly_chart(fig_bar, use_container_width=True)

    with c2:
        st.subheader("Distribuição por Vínculo")
        df_vinculo = df['vinculo'].value_counts().reset_index()
        df_vinculo.columns = ['vinculo', 'count']
        
        fig_pie = px.pie(
            df_vinculo, 
            values='count', 
            names='vinculo', 
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # Linha inferior de gráficos
    c3, c4 = st.columns(2)

    with c3:
        st.subheader("Faixa Salarial (Histograma)")
        fig_hist = px.histogram(
            df, 
            x="salario", 
            nbins=20, 
            title="Distribuição dos Salários Base",
            color_discrete_sequence=['#3366CC']
        )
        fig_hist.update_layout(xaxis_title="Salário Base", yaxis_title="Qtd Funcionários")
        st.plotly_chart(fig_hist, use_container_width=True)

    with c4:
        st.subheader("Maiores Salários Líquidos")
        # Tabela simples dos top 5
        top_liquidos = df[['nome_funcionario', 'nome_cargo', 'liquido']].sort_values(by='liquido', ascending=False).head(5)
        st.dataframe(
            top_liquidos.style.format({"liquido": "R$ {:,.2f}"}), 
            use_container_width=True,
            hide_index=True
        )

    # --- 3. TABELA DETALHADA (EXPANDER) ---
    with st.expander("📂 Ver Dados Detalhados da Folha"):
        colunas_visiveis = [
            'cod_funcionario', 'nome_funcionario', 'nome_cargo', 
            'departamento', 'salario', 'proventos_total', 
            'descontos_total', 'liquido'
        ]
        st.dataframe(
            df[colunas_visiveis],
            use_container_width=True,
            hide_index=True
        )