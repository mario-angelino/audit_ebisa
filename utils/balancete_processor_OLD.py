"""
balancete_processor.py - Processamento de arquivos de balancete com pandas
"""

import pandas as pd
import io


def ler_balancete_txt_csv(arquivo, encoding='utf-8'):
    """
    Lê arquivo CSV/TXT de balancete

    Args:
        arquivo: arquivo uploadado (UploadedFile do Streamlit)
        encoding: encoding do arquivo ('utf-8' ou 'latin1')

    Returns:
        tuple (sucesso: bool, mensagem: str, df: DataFrame ou None)
    """
    try:
        # Ler arquivo
        df = pd.read_csv(
            arquivo,
            sep=';',
            encoding=encoding,
            dtype=str  # Ler tudo como string inicialmente
        )

        return (True, "✅ Arquivo lido com sucesso", df)

    except Exception as e:
        # Tentar com outro encoding
        if encoding == 'utf-8':
            try:
                arquivo.seek(0)  # Voltar ao início do arquivo
                df = pd.read_csv(arquivo, sep=';',
                                 encoding='latin1', dtype=str)
                return (True, "✅ Arquivo lido com sucesso (latin1)", df)
            except:
                pass

        return (False, f"❌ Erro ao ler arquivo: {str(e)}", None)


def validar_estrutura(df):
    """
    Valida se o DataFrame tem as colunas esperadas

    Args:
        df: DataFrame do pandas

    Returns:
        tuple (valido: bool, mensagem: str)
    """
    colunas_esperadas = [
        'Nível',
        'Conta',
        'Desc. Conta',
        'Saldo Anterior',
        'Val. Débito',
        'Val. Crédito',
        'Saldo Atual'
    ]

    # Verificar se todas as colunas existem
    colunas_faltando = []
    for col in colunas_esperadas:
        if col not in df.columns:
            colunas_faltando.append(col)

    if colunas_faltando:
        return (False, f"❌ Colunas faltando: {', '.join(colunas_faltando)}")

    return (True, "✅ Estrutura válida")


def limpar_dados(df):
    """
    Limpa e formata os dados do DataFrame

    Args:
        df: DataFrame do pandas

    Returns:
        DataFrame limpo
    """
    # Criar cópia para não modificar original
    df_limpo = df.copy()

    # Remover espaços em branco de todas as colunas de texto
    colunas_texto = ['Nível', 'Conta', 'Desc. Conta']
    for col in colunas_texto:
        if col in df_limpo.columns:
            df_limpo[col] = df_limpo[col].astype(str).str.strip()

    # Limpar e converter colunas numéricas
    colunas_numericas = ['Saldo Anterior',
                         'Val. Débito', 'Val. Crédito', 'Saldo Atual']

    for col in colunas_numericas:
        if col in df_limpo.columns:
            # Remover espaços
            df_limpo[col] = df_limpo[col].astype(str).str.strip()

            # Remover pontos de milhares e substituir vírgula por ponto
            df_limpo[col] = df_limpo[col].str.replace(
                '.', '', regex=False)  # Remove pontos
            df_limpo[col] = df_limpo[col].str.replace(
                ',', '.', regex=False)  # Vírgula vira ponto

            # Remover caracteres não numéricos (exceto ponto e sinal negativo)
            df_limpo[col] = df_limpo[col].str.replace(
                r'[^\d\.\-]', '', regex=True)

            # Substituir vazios por 0
            df_limpo[col] = df_limpo[col].replace('', '0')
            df_limpo[col] = df_limpo[col].replace('nan', '0')

    # Remover linhas completamente vazias
    df_limpo = df_limpo.dropna(how='all')

    return df_limpo


def validar_tipos(df):
    """
    Valida e converte tipos de dados

    Args:
        df: DataFrame do pandas

    Returns:
        tuple (valido: bool, mensagem: str, df_convertido: DataFrame ou None)
    """
    try:
        df_convertido = df.copy()

        # Converter colunas numéricas
        colunas_numericas = ['Saldo Anterior',
                             'Val. Débito', 'Val. Crédito', 'Saldo Atual']

        for col in colunas_numericas:
            if col in df_convertido.columns:
                df_convertido[col] = pd.to_numeric(
                    df_convertido[col], errors='coerce').fillna(0)

        # Validar campo Conta (obrigatório)
        if df_convertido['Conta'].isna().any() or (df_convertido['Conta'] == '').any():
            linhas_invalidas = df_convertido[df_convertido['Conta'].isna() | (
                df_convertido['Conta'] == '')].index.tolist()
            return (False, f"❌ Campo 'Conta' vazio nas linhas: {linhas_invalidas}", None)

        return (True, "✅ Tipos validados e convertidos", df_convertido)

    except Exception as e:
        return (False, f"❌ Erro ao validar tipos: {str(e)}", None)


def remover_colunas_vazias(df):
    """
    Remove colunas completamente vazias (Unnamed, etc.)

    Args:
        df: DataFrame do pandas

    Returns:
        DataFrame sem colunas vazias
    """
    # Remover colunas que começam com "Unnamed"
    colunas_para_manter = [
        col for col in df.columns if not col.startswith('Unnamed')]

    return df[colunas_para_manter]


def remover_linhas_totalizadoras(df):
    """
    Remove linhas de totalização/lixo do balancete
    (Linhas onde Nível = "T" E Desc. Conta = "Total")

    Args:
        df: DataFrame do pandas

    Returns:
        DataFrame sem linhas totalizadoras
    """
    linhas_antes = len(df)

    # Filtrar linhas onde Nível = "T" E Desc. Conta = "Total"
    df_limpo = df[
        ~((df['Nível'].astype(str).str.strip().str.upper() == 'T') &
          (df['Desc. Conta'].astype(str).str.strip().str.upper() == 'TOTAL'))
    ].reset_index(drop=True)

    linhas_removidas = linhas_antes - len(df_limpo)

    if linhas_removidas > 0:
        print(f"🗑️ Removidas {linhas_removidas} linha(s) totalizadora(s)")

    return df_limpo


def remover_coluna_saldo_periodo(df):
    """
    Remove a coluna "Saldo Período" se ela existir no DataFrame

    Args:
        df: DataFrame do pandas

    Returns:
        DataFrame sem a coluna "Saldo Período"
    """
    if 'Saldo Período' in df.columns:
        df = df.drop(columns=['Saldo Período'])
        print(f"🗑️ Coluna 'Saldo Período' removida")

    return df


def processar_balancete(arquivo):
    """
    Processa arquivo de balancete completo (pipeline)

    Args:
        arquivo: arquivo uploadado (UploadedFile do Streamlit)

    Returns:
        tuple (sucesso: bool, mensagem: str, df: DataFrame ou None)
    """
    # 1. Ler arquivo
    sucesso, mensagem, df = ler_balancete_txt_csv(arquivo)
    if not sucesso:
        return (False, mensagem, None)

    # 2. Remover colunas vazias (Unnamed, etc.)
    df = remover_colunas_vazias(df)

    # 3. Remover coluna "Saldo Período" se existir
    df = remover_coluna_saldo_periodo(df)

    # 4. Validar estrutura
    valido, mensagem = validar_estrutura(df)
    if not valido:
        return (False, mensagem, None)

    # 5. Limpar dados
    df_limpo = limpar_dados(df)

    # 6. Validar tipos
    valido, mensagem, df_final = validar_tipos(df_limpo)
    if not valido:
        return (False, mensagem, None)

    # 7. Remover linhas totalizadoras/lixo
    df_final = remover_linhas_totalizadoras(df_final)

    # 8. Verificar se há dados
    if len(df_final) == 0:
        return (False, "❌ Arquivo não possui dados válidos", None)

    return (True, f"✅ Processado com sucesso! {len(df_final)} registros", df_final)
