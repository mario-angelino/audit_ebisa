"""
database.py -> módulo responsável pela conexão com o banco de dados PostgreSQL

Funções disponíveis:
- conectar()
- desconectar()
"""

import psycopg2
import streamlit as st


def conectar():
    """Conecta ao banco PostgreSQL do Supabase usando secrets.toml"""
    try:
        conn = psycopg2.connect(
            host=st.secrets["DB_HOST"],
            port=st.secrets["DB_PORT"],
            database=st.secrets["DB_NAME"],
            user=st.secrets["DB_USER"],
            password=st.secrets["DB_PASSWORD"],
        )
        return conn
    except Exception as e:
        print(f"❌ Erro ao conectar: {e}")
        raise


def desconectar(conn):
    if conn:
        conn.close()
