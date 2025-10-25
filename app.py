# --- ARQUIVO: app.py (VERSÃO 20 - LIMPEZA DE TRANSFERÊNCIA COM CALLBACK) ---

import streamlit as st
from sistema_financeiro import GerenciadorContas, ContaCorrente, ContaInvestimento

# --- Funções de Callback para Limpeza ---
def limpar_campos_transferencia():
    """Reseta os valores dos widgets de transferência no session_state."""
    # Verificamos se as chaves existem antes de tentar modificá-las
    if 'transfer_valor' in st.session_state:
        st.session_state.transfer_valor = 0.01
    # Para os selectbox, o comportamento padrão ao recarregar é suficiente,
    # mas limpar o valor do input numérico é o mais importante.

# --- Configuração da Página ---
st.set_page_config(page_title="Meu Sistema Financeiro", page_icon="💰", layout="wide")

# --- Inicialização do Sistema ---
if 'gerenciador' not in st.session_state:
    st.session_state.gerenciador = GerenciadorContas("dados_contas.json")

# --- Título da Aplicação ---
st.title("Meu Sistema de Gestão Financeira Pessoal 💰")

# --- Colunas Principais ---
col1, col2 = st.columns([1, 1])

# --- COLUNA DA ESQUERDA: Contas e Transferências ---
with col1:
    st.header("Painel de Contas")
    
    todas_as_contas = st.session_state.gerenciador.contas
    contas_correntes = [c for c in todas_as_contas if isinstance(c, ContaCorrente)]
    contas_investimento = [c for c in todas_as_contas if isinstance(c, ContaInvestimento)]

    if not todas_as_contas:
        st.warning("Nenhuma conta encontrada. Adicione uma nova conta no painel ao lado.")
    else:
        tab_cc, tab_ci = st.tabs(["Contas Correntes", "Contas de Investimento"])
        # ... (código das abas não precisa de mudanças)
        with tab_cc:
            if not contas_correntes: st.info("Nenhuma conta corrente cadastrada.")
            for conta in contas_correntes:
                with st.expander(f"{conta.nome} - R$ {conta.saldo:,.2f}"):
                    st.write(f"**Limite:** R$ {conta.limite_cheque_especial:,.2f}")
                    with st.form(f"edit_form_{conta.id_conta}"):
                        novo_nome = st.text_input("Novo nome", value=conta.nome)
                        if st.form_submit_button("Salvar"):
                            if conta.editar_nome(novo_nome):
                                st.session_state.gerenciador.salvar_dados()
                                st.toast(f"Conta '{novo_nome}' atualizada!")
                                st.rerun()
                    if st.button(f"Remover", key=f"remove_{conta.id_conta}", type="primary"):
                        if st.session_state.gerenciador.remover_conta(conta.id_conta):
                            st.session_state.gerenciador.salvar_dados()
                            st.toast(f"Conta '{conta.nome}' removida!")
                            st.rerun()
        with tab_ci:
            if not contas_investimento: st.info("Nenhuma conta de investimento cadastrada.")
            for conta in contas_investimento:
                with st.expander(f"{conta.nome} - R$ {conta.saldo:,.2f}"):
                    st.write(f"**Tipo:** {conta.tipo_investimento}")
                    with st.form(f"edit_form_{conta.id_conta}"):
                        novo_nome = st.text_input("Novo nome", value=conta.nome)
                        if st.form_submit_button("Salvar"):
                            if conta.editar_nome(novo_nome):
                                st.session_state.gerenciador.salvar_dados()
                                st.toast(f"Conta '{novo_nome}' atualizada!")
                                st.rerun()
                    if st.button(f"Remover", key=f"remove_{conta.id_conta}", type="primary"):
                        if st.session_state.gerenciador.remover_conta(conta.id_conta):
                            st.session_state.gerenciador.salvar_dados()
                            st.toast(f"Conta '{conta.nome}' removida!")
                            st.rerun()

    st.header("Realizar Transferência")
    if len(todas_as_contas) >= 2:
        nomes_contas = [c.nome for c in todas_as_contas]
        conta_origem_nome = st.selectbox("De:", nomes_contas, key="transfer_origem")
        opcoes_destino = [nome for nome in nomes_contas if nome != conta_origem_nome]
        conta_destino_nome = st.selectbox("Para:", opcoes_destino, key="transfer_destino")
        valor_transferencia = st.number_input("Valor (R$)", min_value=0.01, format="%.2f", key="transfer_valor")
        
        # MUDANÇA: Adicionamos o on_click ao botão
        if st.button(
            "Confirmar Transferência", 
            use_container_width=True,
            on_click=limpar_campos_transferencia # A função de limpeza é chamada no clique
        ):
            id_origem = next((c.id_conta for c in todas_as_contas if c.nome == conta_origem_nome), None)
            id_destino = next((c.id_conta for c in todas_as_contas if c.nome == conta_destino_nome), None)
            
            if id_origem and id_destino:
                # Usamos o valor do session_state para garantir que pegamos o valor antes da limpeza
                valor = st.session_state.transfer_valor 
                if st.session_state.gerenciador.realizar_transferencia(id_origem, id_destino, valor):
                    st.session_state.gerenciador.salvar_dados()
                    st.success("Transferência realizada com sucesso!")
                    st.rerun()
                else:
                    st.error("Falha na transferência. Saldo insuficiente?")
    else:
        st.info("Adicione pelo menos duas contas para realizar transferências.")

# --- COLUNA DA DIREITA: Ações e Resumo ---
with col2:
    # ... (código da coluna da direita não precisa de mudanças)
    st.header("Ações")
    st.subheader("Adicionar Nova Conta")
    tipo_conta = st.selectbox("Tipo de Conta", ["Conta Corrente", "Conta Investimento"], index=0, key='add_tipo_conta')
    nome_conta = st.text_input("Nome da Conta", key="add_nome")
    saldo_inicial = st.number_input("Saldo Inicial (R$)", min_value=0.0, format="%.2f", key="add_saldo")
    if tipo_conta == "Conta Corrente":
        limite = st.number_input("Limite do Cheque Especial (R$)", min_value=0.0, format="%.2f", key="add_limite")
    else:
        tipo_invest = st.text_input("Tipo de Investimento (Ex: Ações, Cripto)", key="add_tipo_invest")
    if st.button("Adicionar Conta", use_container_width=True):
        if not nome_conta:
            st.error("O nome da conta é obrigatório.")
        else:
            nova_conta = None
            if tipo_conta == "Conta Corrente":
                nova_conta = ContaCorrente(nome=nome_conta, saldo=saldo_inicial, limite_cheque_especial=limite)
            else:
                if not tipo_invest:
                    st.error("O tipo de investimento é obrigatório.")
                else:
                    nova_conta = ContaInvestimento(nome=nome_conta, saldo=saldo_inicial, tipo_investimento=tipo_invest)
            if nova_conta:
                st.session_state.gerenciador.adicionar_conta(nova_conta)
                st.session_state.gerenciador.salvar_dados()
                st.success(f"Conta '{nome_conta}' adicionada com sucesso!")
                st.session_state.add_nome = ""
                st.session_state.add_saldo = 0.0
                if 'add_limite' in st.session_state: st.session_state.add_limite = 0.0
                if 'add_tipo_invest' in st.session_state: st.session_state.add_tipo_invest = ""
                st.rerun()
    st.header("Resumo Financeiro")
    if todas_as_contas:
        patrimonio_total = sum(c.saldo for c in todas_as_contas)
        st.metric(label="**Patrimônio Total**", value=f"R$ {patrimonio_total:,.2f}")
    else:
        st.metric(label="**Patrimônio Total**", value="R$ 0,00")
