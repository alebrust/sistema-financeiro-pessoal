# --- ARQUIVO: app.py (VERSÃO 45 - CONFIRMAÇÃO DE EXCLUSÃO) ---

import streamlit as st
import pandas as pd
from datetime import datetime
from sistema_financeiro import GerenciadorContas, ContaCorrente, ContaInvestimento, Ativo
from collections import defaultdict

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

st.set_page_config(page_title="Meu Sistema Financeiro", page_icon="💰", layout="wide")

if 'gerenciador' not in st.session_state:
    st.session_state.gerenciador = GerenciadorContas("dados_v7.json")

# Inicializa a chave para o controle do diálogo de confirmação
if 'transacao_para_excluir' not in st.session_state:
    st.session_state.transacao_para_excluir = None

st.title("Meu Sistema de Gestão Financeira Pessoal 💰")

tab_dashboard, tab_transacoes, tab_contas = st.tabs(["📊 Dashboard", "📈 Histórico de Transações", "🏦 Contas"])

# --- ABA 1: DASHBOARD ---
with tab_dashboard:
    # ... (código do Dashboard sem mudanças)
    col1, col2 = st.columns([1, 1])
    with col2:
        st.header("Ações Rápidas")
        with st.expander("📈 Comprar Ativo"):
            contas_investimento = [c for c in st.session_state.gerenciador.contas if isinstance(c, ContaInvestimento)]
            if not contas_investimento: st.warning("Crie uma Conta de Investimento na aba 'Contas' para comprar ativos.")
            else:
                with st.form("buy_asset_form", clear_on_submit=True):
                    st.write("**Registrar Compra de Ativo**"); conta_destino_nome = st.selectbox("Comprar na corretora:", [c.nome for c in contas_investimento]); ticker = st.text_input("Ticker do Ativo (ex: PETR4, AAPL)").upper(); tipo_ativo = st.selectbox("Tipo de Ativo", ["Ação BR", "FII", "Ação EUA", "Cripto", "Outro"]); col_qnt, col_preco = st.columns(2)
                    with col_qnt: quantidade = st.number_input("Quantidade", min_value=0.000001, format="%.6f")
                    with col_preco: preco_unitario = st.number_input("Preço por Unidade (R$)", min_value=0.01, format="%.2f")
                    data_compra = st.date_input("Data da Compra", value=datetime.today(), format="DD/MM/YYYY")
                    if st.form_submit_button("Confirmar Compra"):
                        if not all([ticker, quantidade > 0, preco_unitario > 0]): st.error("Preencha todos os detalhes da compra do ativo.")
                        else:
                            id_destino = next((c.id_conta for c in contas_investimento if c.nome == conta_destino_nome), None)
                            sucesso = st.session_state.gerenciador.comprar_ativo(id_conta_destino=id_destino, ticker=ticker, quantidade=quantidade, preco_unitario=preco_unitario, tipo_ativo=tipo_ativo, data_compra=data_compra)
                            if sucesso: st.session_state.gerenciador.salvar_dados(); st.success(f"Compra de {ticker} registrada!"); st.rerun()
                            else: st.error("Falha na compra. Verifique o saldo em caixa da corretora.")
        with st.expander("💸 Registrar Receita/Despesa", expanded=True):
            contas_correntes = [c for c in st.session_state.gerenciador.contas if isinstance(c, ContaCorrente)]
            if not contas_correntes: st.warning("Crie uma Conta Corrente para registrar receitas/despesas.")
            else:
                with st.form("new_transaction_form", clear_on_submit=True):
                    tipo_transacao = st.selectbox("Tipo", ["Receita", "Despesa"]); conta_selecionada_nome = st.selectbox("Conta Corrente", [c.nome for c in contas_correntes]); descricao = st.text_input("Descrição"); categoria = st.text_input("Categoria"); valor = st.number_input("Valor (R$)", min_value=0.01, format="%.2f"); data_transacao = st.date_input("Data", value=datetime.today(), format="DD/MM/YYYY")
                    if st.form_submit_button("Registrar"):
                        if not all([descricao, categoria]): st.error("Descrição e Categoria são obrigatórios.")
                        else:
                            conta_id = next((c.id_conta for c in contas_correntes if c.nome == conta_selecionada_nome), None)
                            sucesso = st.session_state.gerenciador.registrar_transacao(id_conta=conta_id, descricao=descricao, valor=valor, tipo=tipo_transacao, data_transacao=data_transacao, categoria=categoria)
                            if sucesso: st.session_state.gerenciador.salvar_dados(); st.success("Transação registrada!"); st.rerun()
                            else: st.error("Falha ao registrar. Saldo insuficiente?")
        st.header("Resumo Financeiro")
        todas_as_contas = st.session_state.gerenciador.contas
        if todas_as_contas:
            saldos_agrupados = defaultdict(float)
            for conta in todas_as_contas:
                if isinstance(conta, ContaCorrente): saldos_agrupados["Contas Correntes"] += conta.saldo
                elif isinstance(conta, ContaInvestimento):
                    if conta.saldo_caixa > 0: saldos_agrupados["Caixa Corretoras"] += conta.saldo_caixa
                    for ativo in conta.ativos: saldos_agrupados[ativo.tipo_ativo] += ativo.valor_total
            st.subheader("Patrimônio por Categoria");
            for categoria, saldo in saldos_agrupados.items(): st.metric(label=categoria, value=formatar_moeda(saldo))
            st.divider()
            patrimonio_total = sum(c.saldo for c in todas_as_contas); st.metric(label="**Patrimônio Total**", value=formatar_moeda(patrimonio_total))
        else: st.metric(label="**Patrimônio Total**", value="R$ 0,00")
    with col1:
        st.header("Realizar Transferência")
        todas_as_contas = st.session_state.gerenciador.contas
        if len(todas_as_contas) >= 2:
            with st.form("transfer_form", clear_on_submit=True):
                nomes_contas = [c.nome for c in todas_as_contas]; col_form1, col_form2 = st.columns(2)
                with col_form1: conta_origem_nome = st.selectbox("De:", nomes_contas, key="transfer_origem")
                with col_form2:
                    opcoes_destino = [nome for nome in nomes_contas if nome != st.session_state.get("transfer_origem", nomes_contas[0])]
                    conta_destino_nome = st.selectbox("Para:", opcoes_destino, key="transfer_destino")
                valor_transferencia = st.number_input("Valor (R$)", min_value=0.01, format="%.2f", key="transfer_valor")
                if st.form_submit_button("Confirmar Transferência", use_container_width=True):
                    id_origem = next((c.id_conta for c in todas_as_contas if c.nome == conta_origem_nome), None)
                    id_destino = next((c.id_conta for c in todas_as_contas if c.nome == conta_destino_nome), None)
                    if id_origem and id_destino and valor_transferencia > 0:
                        if st.session_state.gerenciador.realizar_transferencia(id_origem, id_destino, valor_transferencia):
                            st.session_state.gerenciador.salvar_dados(); st.success("Transferência realizada!"); st.rerun()
                        else: st.error("Falha na transferência. Saldo insuficiente?")
                    else: st.error("Erro nos dados da transferência.")
        else: st.info("Adicione pelo menos duas contas para realizar transferências.")

# --- ABA 2: HISTÓRICO DE TRANSAÇÕES ---
with tab_transacoes:
    st.header("Histórico de Todas as Transações")
    transacoes = st.session_state.gerenciador.transacoes
    if not transacoes:
        st.info("Nenhuma transação registrada ainda.")
    else:
        mapa_contas = {c.id_conta: c.nome for c in st.session_state.gerenciador.contas}
        
        col_data, col_conta, col_desc, col_cat, col_valor, col_acao = st.columns([2, 2, 3, 2, 2, 1])
        col_data.write("**Data**"); col_conta.write("**Conta**"); col_desc.write("**Descrição**"); col_cat.write("**Categoria**"); col_valor.write("**Valor**"); col_acao.write("**Ação**")
        st.divider()

        for t in sorted(transacoes, key=lambda x: x.data, reverse=True):
            col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 3, 2, 2, 1])
            with col1: st.text(t.data.strftime("%d/%m/%Y"))
            with col2: st.text(mapa_contas.get(t.id_conta, "N/A"))
            with col3: st.text(t.descricao)
            with col4: st.text(t.categoria)
            with col5:
                valor_str = f"+{formatar_moeda(t.valor)}" if t.tipo == "Receita" else f"-{formatar_moeda(t.valor)}"
                cor = "green" if t.tipo == "Receita" else "red"
                st.markdown(f"<span style='color:{cor};'>{valor_str}</span>", unsafe_allow_html=True)
            
            # --- MUDANÇA PRINCIPAL AQUI ---
            with col6:
                # 1. O botão de lixeira agora apenas define o estado de confirmação
                if st.button("🗑️", key=f"del_{t.id_transacao}", help="Excluir esta transação"):
                    st.session_state.transacao_para_excluir = t.id_transacao
                    st.rerun()

            # 2. Se uma transação está pendente de exclusão, mostramos o diálogo de confirmação
            if st.session_state.transacao_para_excluir == t.id_transacao:
                st.warning(f"Tem certeza que deseja excluir a transação '{t.descricao}'?")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("Sim, excluir", key=f"confirm_del_{t.id_transacao}", type="primary"):
                        sucesso = st.session_state.gerenciador.remover_transacao(t.id_transacao)
                        if sucesso:
                            st.session_state.gerenciador.salvar_dados()
                            st.toast("Transação removida com sucesso!")
                            st.session_state.transacao_para_excluir = None # Limpa o estado
                            st.rerun()
                        else:
                            st.error("Não foi possível remover a transação.")
                with col_cancel:
                    if st.button("Cancelar", key=f"cancel_del_{t.id_transacao}"):
                        st.session_state.transacao_para_excluir = None # Limpa o estado
                        st.rerun()
            
            st.divider()

# --- ABA 3: GESTÃO DE CONTAS ---
with tab_contas:
    # ... (código da aba Contas sem mudanças)
    st.header("Gerenciar Contas"); col_contas1, col_contas2 = st.columns(2)
    with col_contas2:
        with st.form("add_account_form", clear_on_submit=True):
            st.subheader("Adicionar Nova Conta"); tipo_conta = st.selectbox("Tipo de Conta", ["Conta Corrente", "Conta Investimento"]); nome_conta = st.text_input("Nome da Conta"); logo_url_add = st.text_input("URL do Logo (Opcional)")
            if tipo_conta == "Conta Corrente":
                saldo_inicial = st.number_input("Saldo Inicial (R$)", min_value=0.0, format="%.2f"); limite = st.number_input("Limite do Cheque Especial (R$)", min_value=0.0, format="%.2f")
            if st.form_submit_button("Adicionar Conta", use_container_width=True):
                if not nome_conta: st.error("O nome da conta é obrigatório.")
                else:
                    nova_conta = None
                    if tipo_conta == "Conta Corrente": nova_conta = ContaCorrente(nome=nome_conta, saldo=saldo_inicial, limite_cheque_especial=limite, logo_url=logo_url_add)
                    else: nova_conta = ContaInvestimento(nome=nome_conta, logo_url=logo_url_add)
                    if nova_conta: st.session_state.gerenciador.adicionar_conta(nova_conta); st.session_state.gerenciador.salvar_dados(); st.success(f"Conta '{nome_conta}' adicionada!"); st.rerun()
    with col_contas1:
        st.subheader("Contas Existentes"); todas_as_contas = st.session_state.gerenciador.contas
        if not todas_as_contas: st.info("Nenhuma conta cadastrada.")
        else:
            tab_cc_ger, tab_ci_ger = st.tabs(["Contas Correntes", "Contas de Investimento"])
            with tab_cc_ger:
                contas_correntes = [c for c in todas_as_contas if isinstance(c, ContaCorrente)]
                if not contas_correntes: st.info("Nenhuma conta corrente cadastrada.")
                for conta in contas_correntes:
                    logo_col, expander_col = st.columns([1, 5]);
                    with logo_col:
                        if conta.logo_url: st.image(conta.logo_url, width=65)
                        else: st.write("🏦")
                    with expander_col:
                        with st.expander(f"{conta.nome} - {formatar_moeda(conta.saldo)}"):
                            st.write(f"**Limite:** {formatar_moeda(conta.limite_cheque_especial)}")
                            with st.form(f"edit_form_{conta.id_conta}"):
                                novo_nome = st.text_input("Nome", value=conta.nome); nova_logo_url = st.text_input("URL do Logo", value=conta.logo_url); novo_limite = st.number_input("Limite", min_value=0.0, value=float(conta.limite_cheque_especial), format="%.2f")
                                if st.form_submit_button("Salvar Alterações"):
                                    nome_mudou = conta.editar_nome(novo_nome); logo_mudou = conta.editar_logo_url(nova_logo_url); attr_mudou = conta.editar_limite(novo_limite)
                                    if nome_mudou or logo_mudou or attr_mudou: st.session_state.gerenciador.salvar_dados(); st.toast(f"Conta '{novo_nome}' atualizada!"); st.rerun()
                            if st.button(f"Remover Conta", key=f"remove_{conta.id_conta}", type="primary"):
                                if st.session_state.gerenciador.remover_conta(conta.id_conta): st.session_state.gerenciador.salvar_dados(); st.toast(f"Conta '{conta.nome}' removida!"); st.rerun()
            with tab_ci_ger:
                contas_investimento = [c for c in todas_as_contas if isinstance(c, ContaInvestimento)]
                if not contas_investimento: st.info("Nenhuma conta de investimento cadastrada.")
                for conta in contas_investimento:
                    logo_col, expander_col = st.columns([1, 5])
                    with logo_col:
                        if conta.logo_url: st.image(conta.logo_url, width=65)
                        else: st.write("📈")
                    with expander_col:
                        with st.expander(f"{conta.nome} - {formatar_moeda(conta.saldo)}"):
                            st.metric("Patrimônio Consolidado", formatar_moeda(conta.saldo)); col_caixa, col_ativos = st.columns(2)
                            col_caixa.metric("Saldo em Caixa", formatar_moeda(conta.saldo_caixa)); col_ativos.metric("Valor em Ativos", formatar_moeda(conta.valor_em_ativos)); st.divider()
                            if not conta.ativos: st.info("Nenhum ativo nesta conta ainda.")
                            else:
                                st.write("**Ativos em Carteira:**"); df_ativos = pd.DataFrame([a.para_dict() for a in conta.ativos])
                                df_ativos["valor_total"] = df_ativos.apply(lambda row: formatar_moeda(row["quantidade"] * row["preco_medio"]), axis=1)
                                df_ativos["preco_medio"] = df_ativos["preco_medio"].apply(formatar_moeda)
                                st.dataframe(df_ativos[['ticker', 'quantidade', 'preco_medio', 'tipo_ativo', 'valor_total']], use_container_width=True, hide_index=True)
                            if st.button(f"Remover Corretora '{conta.nome}'", key=f"remove_{conta.id_conta}", type="primary"):
                                if st.session_state.gerenciador.remover_conta(conta.id_conta): st.session_state.gerenciador.salvar_dados(); st.toast(f"Conta '{conta.nome}' removida!"); st.rerun()
