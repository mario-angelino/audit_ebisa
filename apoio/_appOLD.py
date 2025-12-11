"""
app.py - Página principal do sistema Audit Ebisa
Responsável pela autenticação e criação de usuários
"""

import streamlit as st
from utils.auth import login, logout, check_authentication, get_current_user, create_user

# Configuração da página
st.set_page_config(
    page_title="Audit Ebisa - Sistema de Auditoria",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inicializar session_state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "show_register" not in st.session_state:
    st.session_state.show_register = False


def show_register_page():
    """
    Exibe a página de cadastro de novo usuário
    """
    # CSS customizado
    st.markdown(
        """
        <style>
        .register-header {
            text-align: center;
            padding: 2rem 0;
        }
        .register-container {
            max-width: 450px;
            margin: 0 auto;
            padding: 2rem;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Layout centralizado
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Header
        st.markdown("<div class='register-header'>", unsafe_allow_html=True)
        st.title("📊 Audit Ebisa")
        st.subheader("Cadastro de Novo Usuário")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")

        # Botão para voltar ao login
        if st.button("⬅️ Voltar para Login", use_container_width=True):
            st.session_state.show_register = False
            st.rerun()

        st.markdown("")

        # Formulário de cadastro
        with st.form("register_form", clear_on_submit=False):
            st.markdown("### 📝 Cadastro de Usuário")

            nome = st.text_input(
                "👤 Nome Completo",
                placeholder="Digite seu nome completo",
                help="Informe seu nome completo"
            )

            email = st.text_input(
                "📧 Email",
                placeholder="seu@email.com",
                help="Digite um email válido para cadastro"
            )

            password = st.text_input(
                "🔑 Senha",
                type="password",
                placeholder="••••••••",
                help="Crie uma senha segura (mínimo 6 caracteres)"
            )

            confirm_password = st.text_input(
                "🔒 Confirmar Senha",
                type="password",
                placeholder="••••••••",
                help="Digite a mesma senha novamente para confirmação"
            )

            st.markdown("")

            submit = st.form_submit_button(
                "✅ Criar Conta",
                use_container_width=True,
                type="primary"
            )

            if submit:
                # Validações
                errors = []

                if not nome:
                    errors.append("⚠️ O nome completo é obrigatório!")

                if not email:
                    errors.append("⚠️ O email é obrigatório!")
                elif "@" not in email or "." not in email:
                    errors.append("⚠️ Digite um email válido!")

                if not password:
                    errors.append("⚠️ A senha é obrigatória!")
                elif len(password) < 6:
                    errors.append(
                        "⚠️ A senha deve ter no mínimo 6 caracteres!")

                if not confirm_password:
                    errors.append("⚠️ A confirmação de senha é obrigatória!")
                elif password != confirm_password:
                    errors.append("⚠️ As senhas não coincidem!")

                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    with st.spinner("🔄 Criando usuário..."):
                        result = create_user(email, password, nome)

                        if result["success"]:
                            st.success(result["message"])
                            st.balloons()
                            st.info(
                                "🔐 Você será redirecionado para a página de login em 3 segundos...")
                            st.session_state.show_register = False
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")

        st.markdown("---")

        # Informações adicionais
        with st.expander("ℹ️ Informações sobre o Cadastro"):
            st.markdown("""
            **Requisitos para Cadastro:**
            
            - ✅ Nome completo obrigatório
            - ✅ Email válido e único
            - ✅ Senha com mínimo 6 caracteres
            - ✅ Confirmação de senha idêntica
            
            ---
            
            **Após o cadastro:**
            
            - Seu perfil será criado automaticamente
            - Você receberá nível de acesso 1 (básico)
            - Sua conta será ativada automaticamente (fl_ativo = True)
            - Você poderá fazer login imediatamente
            
            ---
            
            **Dúvidas ou problemas?**  
            Entre em contato com o administrador do sistema.
            """)


def show_login_page():
    """
    Exibe a página de login
    """
    # CSS customizado
    st.markdown(
        """
        <style>
        .login-header {
            text-align: center;
            padding: 2rem 0;
        }
        .login-container {
            max-width: 450px;
            margin: 0 auto;
            padding: 2rem;
            background-color: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Layout centralizado
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Header
        st.markdown("<div class='login-header'>", unsafe_allow_html=True)
        st.title("📊 Audit Ebisa")
        st.subheader("Sistema de Auditoria")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("---")

        # Botão para ir para cadastro
        if st.button("📝 Criar Nova Conta", use_container_width=True):
            st.session_state.show_register = True
            st.rerun()

        st.markdown("")

        # Formulário de login
        with st.form("login_form", clear_on_submit=False):
            st.markdown("### 🔐 Acesso ao Sistema")

            email = st.text_input(
                "📧 Email",
                placeholder="seu@email.com",
                help="Digite o email cadastrado no sistema"
            )

            password = st.text_input(
                "🔑 Senha",
                type="password",
                placeholder="••••••••",
                help="Digite sua senha de acesso"
            )

            st.markdown("")

            submit = st.form_submit_button(
                "🚀 Entrar no Sistema",
                use_container_width=True,
                type="primary"
            )

            if submit:
                if not email or not password:
                    st.error("⚠️ Por favor, preencha todos os campos!")
                elif "@" not in email or "." not in email:
                    st.error("⚠️ Digite um email válido!")
                else:
                    with st.spinner("🔄 Autenticando..."):
                        result = login(email, password)

                        if result["success"]:
                            st.success(result["message"])
                            st.balloons()
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")

        st.markdown("---")

        # Informações adicionais
        with st.expander("ℹ️ Informações do Sistema"):
            st.markdown("""
            **Audit Ebisa - Sistema de Auditoria**
            
            - ✅ Gestão de empresas auditadas
            - ✅ Upload e análise de balancetes
            - ✅ Dashboard com indicadores
            - ✅ Relatórios e exportações
            
            ---
            
            **Problemas de acesso?**  
            Entre em contato com o administrador do sistema.
            """)


def show_main_page():
    """
    Exibe a página principal após login bem-sucedido
    """
    user = get_current_user()

    # Sidebar
    with st.sidebar:
        # Menu de navegação
        # st.markdown("#### 📂 Navegação")
        # st.info("🏢 **Empresas** - Gestão de empresas")
        # st.info("📈 **Balancetes** - Upload e análise")
        # st.info("⚙️ **Configurações** - Ajustes")

        # Informações do usuário
        st.markdown("#### 👤 Usuário")
        st.info(f"**Nome:** {user['nome']}")
        st.info(f"**Email:** {user['email']}")

        st.markdown("---")

        # Botão de logout
        if st.button("🚪 Sair do Sistema", use_container_width=True, type="secondary"):
            logout()

    # Conteúdo principal
    st.title("🏠 Bem-vindo ao Audit MC")
    st.markdown("---")

    # Mensagem de boas-vindas
    st.success(f"✅ Olá, **{user['nome']}**! Você está autenticado no sistema.")

    st.markdown("")

    # Cards informativos
    st.markdown("### 📌 Acesso Rápido")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        #### 🏢 Empresas
        Gerencie as empresas cadastradas no sistema.
        
        - Listar empresas
        - Cadastrar nova empresa
        - Buscar e filtrar
        - Exportar relatórios
        """)

        st.markdown("""
        #### ⚙️ Configurações
        Personalize suas preferências no sistema.
        
        - Editar perfil
        - Alterar senha
        - Notificações
        - Aparência
        """)

    with col2:
        st.markdown("""
        #### 📈 Balancetes
        Faça upload e processe balancetes contábeis.
        
        - Upload de arquivos
        - Processamento automático
        - Histórico de uploads
        - Validação de dados
        """)

    st.markdown("---")

    # Instruções
    st.info("👈 **Use o menu lateral** para navegar entre as páginas do sistema.")

    # Avisos importantes
    st.warning(
        "⚠️ **Atenção:** As páginas internas ainda estão em desenvolvimento.")

    st.markdown("---")

    # Rodapé
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem 0;'>
        <small>Audit Ebisa © 2026 - Sistema de Auditoria Contábil</small>
    </div>
    """, unsafe_allow_html=True)


# Lógica principal da aplicação
def main():
    """
    Função principal que controla o fluxo da aplicação
    """
    if check_authentication():
        show_main_page()
    elif st.session_state.show_register:
        show_register_page()
    else:
        show_login_page()


# Executar aplicação
if __name__ == "__main__":
    main()
