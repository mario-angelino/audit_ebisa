import streamlit as st
import pandas as pd
import database  # Seu módulo de conexão

st.set_page_config(page_title="DFC Gerencial", layout="wide")

# --- 1. ESTRUTURA DO DFC (O ESQUELETO INTELIGENTE) ---
# Aqui definimos a ordem de apresentação e a lógica de cálculo.
# 'tipo': 
#   - 'analitica': Conta que recebe dados do banco (agregados pelo prefixo).
#   - 'subtotal': Soma as analíticas imediatamente acima (dentro do mesmo grupo).
#   - 'grupo': Soma grandes blocos (Entradas, Saídas).
#   - 'resultado': O cálculo final (Entradas - Saídas).
#   - 'titulo': Apenas texto visual.

ESTRUTURA_DFC = [
    # --- BLOCO OPERACIONAL ---
    {"cod": "", "desc": "RESULTADO OPERACIONAL", "tipo": "titulo"},
    
    {"cod": "1.01.01", "desc": "RECEITA OPERACIONAL BRUTA", "tipo": "analitica"},
    {"cod": "1.01.02", "desc": "(-) IMPOSTOS DIRETOS SOBRE FATURAMENTO", "tipo": "analitica"},
    {"cod": "ST_ROL",  "desc": "(=) Receita Operacional Líquida", "tipo": "subtotal", "formula": ["1.01.01", "1.01.02"]},
    
    {"cod": "1.09.01", "desc": "IMPOSTOS RETIDOS DE CLIENTES", "tipo": "analitica"},
    {"cod": "1.09.02", "desc": "OUTRAS RETENÇÕES ATIVAS", "tipo": "analitica"},
    {"cod": "ST_RET",  "desc": "(=) Retenções de Clientes", "tipo": "subtotal", "formula": ["1.09.01", "1.09.02"]},
    
    {"cod": "GRP_ENT_OP", "desc": "(=) Total de Entradas Operacionais", "tipo": "grupo", "formula": ["ST_ROL", "ST_RET"]},
    
    {"cod": "2.01.01", "desc": "MATERIAIS E INSUMOS APLICADOS NAS OBRAS E PROJETOS", "tipo": "analitica"},
    {"cod": "2.01.02", "desc": "MÃO DE OBRA PRÓPRIA E ENCARGOS", "tipo": "analitica"},
    {"cod": "2.01.03", "desc": "OUTROS GASTOS COM MÃO DE OBRA PRÓPRIA", "tipo": "analitica"},
    {"cod": "2.01.04", "desc": "VEÍCULOS E EQUIPAMENTOS", "tipo": "analitica"},
    {"cod": "2.01.05", "desc": "VIAGENS E DESLOCAMENTOS", "tipo": "analitica"},
    {"cod": "2.01.06", "desc": "LOCALIZAÇÃO", "tipo": "analitica"},
    {"cod": "2.01.07", "desc": "ADMINISTRAÇÃO", "tipo": "analitica"},
    {"cod": "2.01.08", "desc": "INFORMÁTICA E TELECOMUNICAÇÕES", "tipo": "analitica"},
    {"cod": "2.01.09", "desc": "SERVIÇOS ESPECIALIZADOS", "tipo": "analitica"},
    {"cod": "2.01.10", "desc": "COMERCIAIS", "tipo": "analitica"},
    {"cod": "ST_CUSTOS", "desc": "(=) Custos e Despesas Operacionais", "tipo": "subtotal", "formula": ["2.01.01", "2.01.02", "2.01.03", "2.01.04", "2.01.05", "2.01.06", "2.01.07", "2.01.08", "2.01.09", "2.01.10"]},
    
    {"cod": "2.04.01", "desc": "IMPOSTOS DIRETOS A PAGAR", "tipo": "analitica"},
    {"cod": "2.04.02", "desc": "TRIBUTOS E ENCARGOS DE FOLHA DE PGTO E TERCEIROS", "tipo": "analitica"},
    {"cod": "2.04.03", "desc": "IMPOSTOS DE TERCEIROS", "tipo": "analitica"},
    {"cod": "2.04.04", "desc": "IMPOSTOS SOBRE PROPRIEDADES", "tipo": "analitica"},
    {"cod": "2.04.05", "desc": "PARCELAMENTO DE IMPOSTOS", "tipo": "analitica"},
    {"cod": "2.04.07", "desc": "AUTUAÇÕES E INFRAÇÕES", "tipo": "analitica"},
    {"cod": "ST_TRIB", "desc": "(=) Despesas Tributárias", "tipo": "subtotal", "formula": ["2.04.01", "2.04.02", "2.04.03", "2.04.04", "2.04.05", "2.04.07"]},
    
    {"cod": "2.09.01", "desc": "IMPOSTOS RETIDOS FOLHA/FORNECEDORES", "tipo": "analitica"},
    {"cod": "2.09.02", "desc": "OUTRAS RETENÇÕES PASSIVAS", "tipo": "analitica"},
    {"cod": "ST_RET_FORN", "desc": "(=) Retenções de Fornecedores", "tipo": "subtotal", "formula": ["2.09.01", "2.09.02"]},
    
    {"cod": "2.99.01", "desc": "Uso Indevido Imposto no Contas a Receber", "tipo": "analitica"},
    {"cod": "2.99.02", "desc": "Uso Indevido Imposto no Contas a Pagar", "tipo": "analitica"},
    {"cod": "ST_USO_IND", "desc": "(=) Uso Indevido de Impostos", "tipo": "subtotal", "formula": ["2.99.01", "2.99.02"]},
    
    {"cod": "GRP_SAI_OP", "desc": "(=) Total de Saídas Operacionais", "tipo": "grupo", "formula": ["ST_CUSTOS", "ST_TRIB", "ST_RET_FORN", "ST_USO_IND"]},
    
    {"cod": "RES_OP", "desc": "(=) Total do Resultado Operacional", "tipo": "resultado", "formula": ["GRP_ENT_OP", "GRP_SAI_OP"]}, # Entradas + Saídas (assumindo que saídas já vêm negativas do banco ou ajustaremos)

    # --- BLOCO PATRIMONIAL ---
    {"cod": "", "desc": "RESULTADO PATRIMONIAL (SÓCIOS)", "tipo": "titulo"},
    
    {"cod": "1.02.01", "desc": "APORTE DE CAPITAL", "tipo": "analitica"},
    {"cod": "1.02.04", "desc": "VENDA DE ATIVOS", "tipo": "analitica"},
    {"cod": "1.04.01", "desc": "DISTRIBUIÇÃO DE LUCROS", "tipo": "analitica"},
    {"cod": "1.05.09", "desc": "Transferência Mesma Titularidade", "tipo": "analitica"},
    {"cod": "ST_ENT_PAT", "desc": "(=) Entradas Patrimoniais", "tipo": "subtotal", "formula": ["1.02.01", "1.02.04", "1.04.01", "1.05.09"]},
    
    {"cod": "2.02.01", "desc": "RETIRADA DOS SÓCIOS", "tipo": "analitica"},
    {"cod": "2.02.02", "desc": "APORTE", "tipo": "analitica"},
    {"cod": "2.02.03", "desc": "DISTRIBUIÇÃO DE LUCROS", "tipo": "analitica"},
    {"cod": "ST_SAI_PAT", "desc": "(=) Saídas Patrimoniais", "tipo": "subtotal", "formula": ["2.02.01", "2.02.02", "2.02.03"]},
    
    {"cod": "RES_PAT", "desc": "(=) Total do Resultado Patrimonial", "tipo": "resultado", "formula": ["ST_ENT_PAT", "ST_SAI_PAT"]},

    # --- BLOCO FINANCEIRO ---
    {"cod": "", "desc": "RESULTADO FINANCEIRO", "tipo": "titulo"},
    
    {"cod": "1.02.02", "desc": "EMPRÉSTIMOS E FINANCIAMENTOS", "tipo": "analitica"},
    {"cod": "1.02.03", "desc": "REPASSES", "tipo": "analitica"},
    {"cod": "1.03.01", "desc": "RECEITAS FINANCEIRAS", "tipo": "analitica"},
    {"cod": "1.03.02", "desc": "INVERSÕES", "tipo": "analitica"},
    {"cod": "1.03.03", "desc": "VARIAÇÕES FINANCEIRAS", "tipo": "analitica"},
    {"cod": "ST_ENT_FIN", "desc": "(=) Entradas Financeiras", "tipo": "subtotal", "formula": ["1.02.02", "1.02.03", "1.03.01", "1.03.02", "1.03.03"]},
    
    {"cod": "2.03.01", "desc": "DESPESAS FINANCEIRAS E BANCÁRIAS", "tipo": "analitica"},
    {"cod": "2.03.02", "desc": "INVERSÕES", "tipo": "analitica"},
    {"cod": "2.03.03", "desc": "VARIAÇÕES FINANCEIRAS", "tipo": "analitica"},
    {"cod": "2.04.06", "desc": "OPERAÇÕES FINANCEIRAS", "tipo": "analitica"},
    {"cod": "2.03.04", "desc": "PAGAMENTO DE EMPRÉSTIMOS E FINANCIAMENTOS", "tipo": "analitica"},
    {"cod": "2.03.05", "desc": "CONTENCIOSO", "tipo": "analitica"},
    {"cod": "ST_SAI_FIN", "desc": "(=) Saídas Financeiras", "tipo": "subtotal", "formula": ["2.03.01", "2.03.02", "2.03.03", "2.04.06", "2.03.04", "2.03.05"]},
    
    {"cod": "RES_FIN", "desc": "(=) Total do Resultado Financeiro", "tipo": "resultado", "formula": ["ST_ENT_FIN", "ST_SAI_FIN"]},
    
    # --- RESULTADO FINAL ---
    {"cod": "RES_FINAL", "desc": "(=) Superávit/Déficit do Período", "tipo": "resultado_final", "formula": ["RES_OP", "RES_PAT", "RES_FIN"]},
]

# --- 2. FUNÇÕES DE DADOS ---
@st.cache_data(ttl=600)
def get_lista_projetos():
    """Busca a lista única de projetos disponíveis na view"""
    conn = database.conectar()
    try:
        # Trazemos cod e nome concatenados para ficar bonito no filtro
        query = """
        SELECT DISTINCT nome_projeto 
        FROM public.vw_fin_dfc_mensal_ppr 
        WHERE nome_projeto IS NOT NULL 
        ORDER BY nome_projeto
        """
        df = pd.read_sql(query, conn)
        return df['nome_projeto'].tolist()
    except Exception as e:
        st.error(f"Erro ao carregar projetos: {e}")
        return []
    finally:
        database.desconectar(conn)


@st.cache_data(ttl=300)
def get_dados_brutos(projetos_selecionados):
    """Busca dados da View e agrega por Ano e Conta"""
    conn = database.conectar()
    
    filtro_proj = ""
    params = []
    
    # Lógica do filtro: Se tem seleção e não contém "TODOS"
    if projetos_selecionados and "TODOS" not in projetos_selecionados:
        placeholders = ', '.join(['%s'] * len(projetos_selecionados))
        # Mudamos aqui para filtrar por nome_projeto
        filtro_proj = f"WHERE nome_projeto IN ({placeholders})"
        params = projetos_selecionados

    query = f"""
    SELECT 
        ano,
        cod_plano_financeiro,
        SUM(valor_total) as valor
    FROM public.vw_fin_dfc_mensal_ppr
    {filtro_proj}
    GROUP BY ano, cod_plano_financeiro
    """
    
    try:
        df = pd.read_sql(query, conn, params=params)
        return df
    finally:
        database.desconectar(conn)

def processar_relatorio(df_bruto):
    if df_bruto.empty:
        return pd.DataFrame()

    # 1. Pivotar: Linhas = Conta Completa, Colunas = Ano
    df_pivot = df_bruto.pivot_table(index='cod_plano_financeiro', columns='ano', values='valor', aggfunc='sum').fillna(0)
    anos_cols = sorted([c for c in df_pivot.columns if isinstance(c, int)])
    
    # 2. Criar DataFrame do Relatório
    df_report = pd.DataFrame(ESTRUTURA_DFC)
    
    # Inicializa colunas de ano com 0.0
    for ano in anos_cols:
        df_report[ano] = 0.0
        
    # 3. PREENCHER CONTAS ANALÍTICAS (Agregação por Prefixo)
    # Ex: Se a linha do relatório é "1.01.01", somamos tudo do banco que começa com "1.01.01"
    for index, row in df_report.iterrows():
        if row['tipo'] == 'analitica':
            codigo_base = row['cod']
            # Filtra no pivot tudo que começa com esse código
            # Ex: 1.01.01.001, 1.01.01.002 -> Tudo entra em 1.01.01
            contas_filhas = [c for c in df_pivot.index if str(c).startswith(codigo_base)]
            
            if contas_filhas:
                soma_filhas = df_pivot.loc[contas_filhas, anos_cols].sum()
                df_report.loc[index, anos_cols] = soma_filhas.values

    # 4. CALCULAR TOTAIS (Subtotais, Grupos e Resultados)
    # Como a lista ESTRUTURA_DFC está ordenada, podemos calcular na ordem
    # Mas para garantir, vamos fazer um loop inteligente ou buscar pelo código
    
    # Dicionário auxiliar para acesso rápido aos valores calculados
    valores_calculados = {} # { 'CODIGO': {2023: 100, 2024: 200} }

    # Primeiro pass: Analíticas já estão preenchidas
    for index, row in df_report.iterrows():
        if row['tipo'] == 'analitica':
            valores_calculados[row['cod']] = df_report.loc[index, anos_cols].to_dict()

    # Segundo pass: Calcular Subtotais, Grupos e Resultados
    # Precisamos iterar algumas vezes ou usar recursão simples, mas como a lista segue ordem lógica (filhos antes dos pais),
    # um loop sequencial geralmente funciona se a estrutura estiver bem montada.
    # Para garantir, vamos calcular por tipo.
    
    def calcular_linha(row_cod, formula):
        somas = {ano: 0.0 for ano in anos_cols}
        for componente in formula:
            # Se o componente já foi calculado, usa. Se não, tenta achar na tabela.
            if componente in valores_calculados:
                vals = valores_calculados[componente]
                for ano in anos_cols:
                    somas[ano] += vals[ano]
            else:
                # Tenta pegar do dataframe se já foi processado (caso a ordem ajude)
                idx = df_report[df_report['cod'] == componente].index
                if not idx.empty:
                    vals = df_report.loc[idx[0], anos_cols].to_dict()
                    valores_calculados[componente] = vals # Cache
                    for ano in anos_cols:
                        somas[ano] += vals[ano]
        return somas

    # Iteramos sobre a estrutura para preencher os calculados
    for index, row in df_report.iterrows():
        if row['tipo'] in ['subtotal', 'grupo', 'resultado', 'resultado_final']:
            if 'formula' in row and isinstance(row['formula'], list):
                somas = calcular_linha(row['cod'], row['formula'])
                df_report.loc[index, anos_cols] = list(somas.values())
                valores_calculados[row['cod']] = somas

    # 5. Coluna Total Geral
    df_report['TOTAL'] = df_report[anos_cols].sum(axis=1)
    
    return df_report, anos_cols

# --- 3. ESTILIZAÇÃO ---

def aplicar_estilo(row):
    estilo = [''] * len(row)
    
    bg_color = ''
    font_color = 'black'
    weight = 'normal'
    border = ''
    
    tipo = row['tipo']
    desc = str(row['desc'])

    if tipo == 'titulo':
        bg_color = '#002060' # Azul Marinho Excel
        font_color = 'white'
        weight = 'bold'
    elif tipo == 'resultado_final':
        bg_color = '#FFFF00' # Amarelo
        weight = 'bold'
        border = '2px solid black'
    elif tipo == 'resultado':
        bg_color = '#1f4e78' # Azul Escuro
        font_color = 'white'
        weight = 'bold'
    elif tipo == 'grupo':
        bg_color = '#8EA9DB' # Azul Médio
        font_color = 'white'
        weight = 'bold'
    elif tipo == 'subtotal':
        bg_color = '#D9E1F2' # Azul Claro
        weight = 'bold'
        font_color = 'black' # Garante preto
    elif "(-)" in desc: # Despesas/Deduções
        font_color = '#cc0000' # Vermelho
        
    for i in range(len(row)):
        css = f'color: {font_color}; font-weight: {weight};'
        if bg_color:
            css += f' background-color: {bg_color};'
        if border:
            css += f' border-top: {border}; border-bottom: {border};'
        estilo[i] = css
        
    return estilo

# --- INTERFACE ---

st.sidebar.header("Filtros DFC")

# 1. Busca a lista do banco
opcoes_projetos = get_lista_projetos()

# 2. Adiciona "TODOS" no início da lista
lista_completa = ["TODOS"] + opcoes_projetos

# 3. Cria o multiselect
proj_sel = st.sidebar.multiselect("Projetos", lista_completa, default="TODOS")

if st.sidebar.button("Atualizar"):
    st.cache_data.clear()

df_bruto = get_dados_brutos(proj_sel)
df_final, cols_anos = processar_relatorio(df_bruto)

# ... (todo o código anterior permanece igual até a linha st.title) ...

# ... (todo o código anterior permanece igual) ...

st.title("📑 Demonstração de Fluxo de Caixa (Gerencial)")

# --- NOVO BLOCO: SUBTÍTULO DINÂMICO ---
if "TODOS" in proj_sel:
    texto_projetos = "Consolidado (Todos os Projetos)"
else:
    # Junta os nomes selecionados com vírgula (ex: "Obra A, Obra B")
    texto_projetos = ", ".join(proj_sel)

st.markdown(f"##### 🏗️ **Projeto(s):** <span style='color:#1f4e78'>{texto_projetos}</span>", unsafe_allow_html=True)
st.markdown("---")
# --------------------------------------

if not df_final.empty:
    # --- CORREÇÃO CRÍTICA ---
    # O Streamlit não aceita inteiros (ex: 2023) no column_order.
    # Vamos converter TODOS os nomes de coluna para string.
    df_final.columns = df_final.columns.astype(str)
    
    # Atualizamos a lista de anos para string também para bater com o DF
    cols_anos_str = [str(ano) for ano in cols_anos]
    
    # 1. Definir explicitamente quais colunas queremos ver (agora tudo é string)
    cols_visiveis = ['cod', 'desc'] + cols_anos_str + ['TOTAL']
    
    # 2. Configurar Formatação de Moeda (usando as chaves em string)
    format_dict = {c: 'R$ {:,.2f}' for c in cols_anos_str}
    format_dict['TOTAL'] = 'R$ {:,.2f}'
    
    # 3. Criar o Styler
    styler = df_final.style.apply(aplicar_estilo, axis=1)\
        .format(format_dict)\
        .hide(axis="index")
        
    # 4. Exibir com column_order
    st.dataframe(
        styler,
        height=800,
        use_container_width=True,
        column_order=cols_visiveis, # Agora funciona pois a lista é só de strings
        column_config={
            "cod": st.column_config.TextColumn("Código", width="small"),
            "desc": st.column_config.TextColumn("Descrição", width="large"),
        }
    )
else:
    st.warning("Nenhum dado encontrado.")