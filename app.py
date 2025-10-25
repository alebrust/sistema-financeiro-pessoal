# --- ARQUIVO: app.py (VERSÃO 15 - CORREÇÃO FINAL DO ESTADO DO FORMULÁRIO) ---

import streamlit as st
from sistema_financeiro import GerenciadorContas, ContaCorrente, ContaInvestimento

# --- Configuração da Página ---
st.set_page_config(page_title="Meu Sistema Financeiro", page_icon="💰", layout="wide")

# --- Inicialização do Sistema ---
if 'gerenciador' not in st.session_state:
    st.session_state.gerenciador = GerenciadorContas("dados_contas.json")
# Inicializa a chave para o tipo de conta se ela não existir
if 'tipo_conta_selecionada' not in st.session_state:
    st.session_state.tipo_conta_selecionada = "Conta Corrente"

# --- Título da Aplicação ---
st.title("Meu Sistema de Gestão Financeira Pessoal 💰")

# --- Colunas Principais ---
col1, col2 = st.columns([1, 1])

# --- COLUNA DA ESQUERDA: Contas e Transferências ---
with col1:
    st.header("Painel de Contas")
    
    contas = st.session_state.gerenciador.contas
    if not contas:
        st.warning("Nenhuma conta encontrada. Adicione uma nova conta no painel ao lado.")
    
    for conta in contas:
        with st.expander(f"{conta.nome} - R$ {conta.saldo:,.2f}"):
            st.write(f"**Tipo:** {conta.__class__.__name__.replace('Conta', '')}")
            st.write(f"**ID:** `{conta.id_conta}`")
            
            with st.form(f"edit_form_{conta.id_conta}"):
                novo_nome = st.text_input("Novo nome da conta", value=conta.nome)
                if st.form_submit_button("Salvar Alterações"):
                    if conta.editar_nome(novo_nome):
                        st.session_state.gerenciador.salvar_dados()
                        st.toast(f"Conta '{novo_nome}' atualizada!")
                        st.rerun()
            
            if st.button(f"Remover Conta '{conta.nome}'", key=f"remove_{conta.id_conta}", type="primary"):
                if st.session_state.gerenciador.remover_conta(conta.id_conta):
                    st.session_state.gerenciador.salvar_dados()
                    st.toast(f"Conta '{conta.nome}' removida!")
                    st.rerun()

    st.header("Realizar Transferência")
    if len(contas) >= 2:
        nomes_contas = [c.nome for c in contas]
        conta_origem_nome = st.selectbox("De:", nomes_contas, key="origem")
        opcoes_destino = [nome for nome in nomes_contas if nome != conta_origem_nome]
        conta_destino_nome = st.selectbox("Para:", opcoes_destino, key="destino")
        valor_transferencia = st.number_input("Valor (R$)", min_value=0.01, format="%.2f")
        if st.button("Confirmar Transferência", use_container_width=True):
            id_origem = next((c.id_conta for c in contas if c.nome == conta_origem_nome), None)
            id_destino = next((c.id_conta for c in contas if c.nome == conta_destino_nome), None)
            if id_origem and id_destino:
                if st.session_state.gerenciador.realizar_transferencia(id_origem, id_destino, valor_transferencia):
                    st.session_state.gerenciador.salvar_dados()
                    st.success("Transferência realizada com sucesso!")
                    st.rerun()
                else:
                    st.error("Falha na transferência. Saldo insuficiente?")
    else:
        st.info("Adicione pelo menos duas contas para realizar transferências.")

# --- COLUNA DA DIREITA: Ações e Resumo ---
with col2:
    st.header("Ações")
    st.subheader("Adicionar Nova Conta")
    
    # MUDANÇA CRÍTICA: O selectbox agora é controlado pelo session_state
    # O valor dele é escrito diretamente na chave 'tipo_conta_selecionada'
    st.selectbox(
        "Tipo de Conta", 
        ["Conta Corrente", "Conta Investimento"], 
        key="tipo_conta_selecionada",
        # on_change=None # Não precisamos mais de on_change, o fluxo normal cuidará disso
    )
    
    with st.form("add_account_form", clear_on_submit=True):
        nome_conta = st.text_input("Nome da Conta")
        saldo_inicial = st.number_input("Saldo Inicial (R$)", min_value=0.0, format="%.2f")
        
        # A lógica condicional continua a mesma, lendo do session_state
        if st.session_state.tipo_conta_selecionada == "Conta Corrente":
            limite = st.number_input("Limite do Cheque Especial (R$)", min_value=0.0, format="%.2f")
        else:
            tipo_invest = st.text_input("Tipo de Investimento (Ex: Ações, Cripto)")

        submitted_add = st.form_submit_button("Adicionar Conta")

        if submitted_add:
            if not nome_conta:
                st.error("O nome da conta é obrigatório.")
            else:
                nova_conta = None
                if st.session_state.tipo_conta_selecionada == "Conta Corrente":
                    nova_conta = ContaCorrente(nome=nome_conta, saldo=saldo_inicial, limite_cheque_especial=limite)
                else: # Conta de Investimento
                    if not tipo_invest:
                        st.error("O tipo de investimento é obrigatório.")
                    else:
                        nova_conta = ContaInvestimento(nome=nome_conta, saldo=saldo_inicial, tipo_investimento=tipo_invest)
                
                if nova_conta:
                    st.session_state.gerenciador.adicionar_conta(nova_conta)
                    st.session_state.gerenciador.salvar_dados()
                    st.success(f"Conta '{nome_conta}' adicionada com sucesso!")
                    st.rerun()

    st.header("Resumo Financeiro")
    if contas:
        patrimonio_total = sum(c.saldo for c in contas)
        st.metric(label="**Patrimônio Total**", value=f"R$ {patrimonio_total:,.2f}")
    else:
        st.metric(label="**Patrimônio Total**", value="R$ 0,00")
