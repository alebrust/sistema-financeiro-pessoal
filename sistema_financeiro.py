# --- ARQUIVO: sistema_financeiro.py (VERSÃO 54 - ARQUITETURA DE FATURA) ---

import json
from abc import ABC, abstractmethod
from uuid import uuid4
from datetime import date, timedelta
from typing import List, Optional, Dict, Any
from dateutil.relativedelta import relativedelta
import calendar

# --- NOVAS CLASSES E CLASSES MODIFICADAS ---

class Fatura:
    """Representa uma fatura de cartão de crédito consolidada e fechada."""
    def __init__(self, id_cartao: str, mes: int, ano: int, data_fechamento: date, data_vencimento: date, valor_total: float, id_fatura: str = None, status: str = "Fechada"):
        self.id_fatura = id_fatura if id_fatura else str(uuid4())
        self.id_cartao = id_cartao
        self.mes = mes
        self.ano = ano
        self.data_fechamento = data_fechamento
        self.data_vencimento = data_vencimento
        self.valor_total = valor_total
        self.status = status # "Fechada" ou "Paga"

    def para_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy()
        d['data_fechamento'] = self.data_fechamento.isoformat()
        d['data_vencimento'] = self.data_vencimento.isoformat()
        return d

class CompraCartao:
    # MUDANÇA: Adicionado id_fatura
    def __init__(self, id_cartao: str, descricao: str, valor: float, data_compra: date, categoria: str, 
                 total_parcelas: int = 1, parcela_atual: int = 1, id_compra: str = None, id_compra_original: str = None, observacao: str = "", id_fatura: str = None):
        self.id_compra = id_compra if id_compra else str(uuid4())
        self.id_compra_original = id_compra_original if id_compra_original else self.id_compra
        self.id_cartao, self.descricao, self.valor, self.data_compra, self.categoria, self.total_parcelas, self.parcela_atual, self.observacao = id_cartao, descricao, valor, data_compra, categoria, total_parcelas, parcela_atual, observacao
        self.id_fatura = id_fatura # Vincula a compra a uma fatura fechada

    def para_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy(); d['data_compra'] = self.data_compra.isoformat(); return d

# ... (Classes CartaoCredito, Ativo, Transacao, Conta, ContaCorrente, ContaInvestimento sem mudanças) ...
class CartaoCredito:
    def __init__(self, nome: str, dia_fechamento: int, dia_vencimento: int, id_cartao: str = None, logo_url: str = ""):
        if not (1 <= dia_fechamento <= 31 and 1 <= dia_vencimento <= 31): raise ValueError("Dias de fechamento e vencimento devem ser válidos.")
        self.id_cartao, self.nome, self.logo_url, self.dia_fechamento, self.dia_vencimento = (id_cartao if id_cartao else str(uuid4()), nome, logo_url, dia_fechamento, dia_vencimento)
    def para_dict(self) -> Dict[str, Any]: return self.__dict__

class Ativo:
    def __init__(self, ticker: str, quantidade: float, preco_medio: float, tipo_ativo: str):
        self.ticker, self.quantidade, self.preco_medio, self.tipo_ativo = ticker, quantidade, preco_medio, tipo_ativo
    @property
    def valor_total(self) -> float: return self.quantidade * self.preco_medio
    def para_dict(self) -> Dict[str, Any]: return self.__dict__

class Transacao:
    def __init__(self, id_conta: str, descricao: str, valor: float, tipo: str, data_transacao: date, categoria: str, id_transacao: str = None, detalhes_operacao: Dict = None, observacao: str = ""):
        self.id_transacao = id_transacao if id_transacao else str(uuid4())
        self.id_conta, self.descricao, self.valor, self.tipo, self.data, self.categoria, self.detalhes_operacao, self.observacao = id_conta, descricao, valor, tipo, data_transacao, categoria, detalhes_operacao if detalhes_operacao else {}, observacao
    def para_dict(self) -> Dict[str, Any]:
        d = self.__dict__.copy(); d['data'] = self.data.isoformat(); return d

class Conta(ABC):
    def __init__(self, nome: str, saldo: float = 0.0, id_conta: str = None, logo_url: str = ""):
        self._id_conta, self._nome, self._saldo, self._logo_url = (id_conta if id_conta else str(uuid4()), nome, saldo, logo_url if logo_url else "")
    def alterar_saldo(self, valor: float): self._saldo += valor
    @property
    def logo_url(self) -> str: return self._logo_url
    def editar_logo_url(self, nova_url: str) -> bool:
        if isinstance(nova_url, str): self._logo_url = nova_url; return True
        return False
    def editar_nome(self, novo_nome: str) -> bool:
        if isinstance(novo_nome, str) and novo_nome.strip(): self._nome = novo_nome; return True
        return False
    @property
    def id_conta(self) -> str: return self._id_conta
    @property
    def nome(self) -> str: return self._nome
    @property
    def saldo(self) -> float: return self._saldo
    def depositar(self, valor: float):
        if not isinstance(valor, (int, float)) or valor <= 0: return
        self._saldo += valor
    @abstractmethod
    def sacar(self, valor: float) -> bool: pass
    def para_dict(self) -> Dict[str, Any]:
        return {"id_conta": self.id_conta, "tipo_classe": self.__class__.__name__, "nome": self.nome, "saldo": self.saldo, "logo_url": self.logo_url}
    def __repr__(self) -> str: return f"<{self.__class__.__name__}(nome='{self.nome}', saldo=R${self.saldo:.2f})>"

class ContaCorrente(Conta):
    def __init__(self, nome: str, saldo: float = 0.0, limite_cheque_especial: float = 0.0, **kwargs):
        super().__init__(nome, saldo, **kwargs)
        self._limite_cheque_especial = limite_cheque_especial
    def editar_limite(self, novo_limite: float) -> bool:
        if isinstance(novo_limite, (int, float)) and novo_limite >= 0: self._limite_cheque_especial = novo_limite; return True
        return False
    @property
    def limite_cheque_especial(self) -> float: return self._limite_cheque_especial
    @property
    def saldo_disponivel_saque(self) -> float: return self.saldo + self.limite_cheque_especial
    def sacar(self, valor: float) -> bool:
        if not isinstance(valor, (int, float)) or valor <= 0: return False
        if valor > self.saldo_disponivel_saque: return False
        self._saldo -= valor
        return True
    def para_dict(self) -> Dict[str, Any]:
        dados = super().para_dict(); dados["limite_cheque_especial"] = self.limite_cheque_especial; return dados

class ContaInvestimento(Conta):
    def __init__(self, nome: str, saldo: float = 0.0, **kwargs):
        super().__init__(nome, saldo, **kwargs)
        self._ativos: List[Ativo] = []
    @property
    def saldo_caixa(self) -> float: return self._saldo
    @property
    def valor_em_ativos(self) -> float: return sum(ativo.valor_total for ativo in self._ativos)
    @property
    def saldo(self) -> float: return self.saldo_caixa + self.valor_em_ativos
    @property
    def ativos(self) -> List[Ativo]: return self._ativos
    def atualizar_ou_adicionar_ativo(self, ticker: str, quantidade_compra: float, preco_compra: float, tipo_ativo: str):
        for ativo in self._ativos:
            if ativo.ticker.upper() == ticker.upper():
                custo_total_antigo = ativo.quantidade * ativo.preco_medio; custo_total_compra = quantidade_compra * preco_compra; nova_quantidade = ativo.quantidade + quantidade_compra
                ativo.preco_medio = (custo_total_antigo + custo_total_compra) / nova_quantidade; ativo.quantidade = nova_quantidade
                return
        self._ativos.append(Ativo(ticker.upper(), quantidade_compra, preco_compra, tipo_ativo))
    def reverter_operacao_ativo(self, ticker: str, quantidade_reverter: float, preco_reverter: float) -> bool:
        for i, ativo in enumerate(self._ativos):
            if ativo.ticker.upper() == ticker.upper():
                if ativo.quantidade < quantidade_reverter: return False
                custo_total_atual = ativo.quantidade * ativo.preco_medio; custo_total_reversao = quantidade_reverter * preco_reverter; nova_quantidade = ativo.quantidade - quantidade_reverter
                if nova_quantidade == 0: self._ativos.pop(i)
                else: ativo.preco_medio = (custo_total_atual - custo_total_reversao) / nova_quantidade; ativo.quantidade = nova_quantidade
                return True
        return False
    def sacar(self, valor: float) -> bool:
        if not isinstance(valor, (int, float)) or valor <= 0: return False
        if valor > self.saldo_caixa: return False
        self._saldo -= valor
        return True
    def para_dict(self) -> Dict[str, Any]:
        dados = super().para_dict(); dados["ativos"] = [ativo.para_dict() for ativo in self._ativos]; return dados

class GerenciadorContas:
    def __init__(self, arquivo_dados: str):
        self._contas: List[Conta] = []
        self._transacoes: List[Transacao] = []
        self._cartoes_credito: List[CartaoCredito] = []
        self._compras_cartao: List[CompraCartao] = []
        self._categorias: List[str] = []
        self._faturas: List[Fatura] = [] # NOVA LISTA
        self._arquivo_dados = arquivo_dados
        self.carregar_dados()
    
    # ... (propriedades)
    @property
    def contas(self) -> List[Conta]: return self._contas
    @property
    def transacoes(self) -> List[Transacao]: return self._transacoes
    @property
    def cartoes_credito(self) -> List[CartaoCredito]: return self._cartoes_credito
    @property
    def compras_cartao(self) -> List[CompraCartao]: return self._compras_cartao
    @property
    def categorias(self) -> List[str]: return self._categorias
    @property
    def faturas(self) -> List[Fatura]: return self._faturas

    # --- NOVOS MÉTODOS DE FATURA ---
    def obter_compras_fatura_aberta(self, id_cartao: str):
        """Retorna todas as compras ainda não associadas a nenhuma fatura fechada."""
        return [c for c in self._compras_cartao if c.id_cartao == id_cartao and c.id_fatura is None]

    def fechar_fatura(self, id_cartao: str, data_fechamento_real: date, data_vencimento_real: date) -> Optional[Fatura]:
        cartao = self.buscar_cartao_por_id(id_cartao)
        if not cartao: return None

        # Encontra a data de fechamento da fatura anterior para definir o início do período
        faturas_anteriores = sorted([f for f in self._faturas if f.id_cartao == id_cartao], key=lambda f: f.data_fechamento, reverse=True)
        data_inicio_periodo = faturas_anteriores[0].data_fechamento + timedelta(days=1) if faturas_anteriores else date(1900, 1, 1)

        compras_para_fechar = [
            c for c in self.obter_compras_fatura_aberta(id_cartao)
            if data_inicio_periodo <= c.data_compra <= data_fechamento_real
        ]

        if not compras_para_fechar: return None

        valor_total_fatura = sum(c.valor for c in compras_para_fechar)
        nova_fatura = Fatura(
            id_cartao=id_cartao,
            mes=data_vencimento_real.month,
            ano=data_vencimento_real.year,
            data_fechamento=data_fechamento_real,
            data_vencimento=data_vencimento_real,
            valor_total=valor_total_fatura
        )
        
        # Vincula as compras à nova fatura
        for compra in compras_para_fechar:
            compra.id_fatura = nova_fatura.id_fatura
        
        self._faturas.append(nova_fatura)
        return nova_fatura

    # ... (resto do Gerenciador)
    def registrar_compra_cartao(self, id_cartao: str, descricao: str, valor_total: float, data_compra: date, categoria: str, num_parcelas: int = 1, observacao: str = ""):
        # A lógica de data de vencimento foi removida daqui, pois será tratada no fechamento
        valor_parcela = round(valor_total / num_parcelas, 2)
        id_compra_original = str(uuid4())
        for i in range(num_parcelas):
            # A data da "compra" da parcela é a data original + meses
            data_parcela = data_compra + relativedelta(months=i)
            desc_parcela = f"{descricao} ({i+1}/{num_parcelas})" if num_parcelas > 1 else descricao
            nova_compra = CompraCartao(id_cartao=id_cartao, descricao=desc_parcela, valor=valor_parcela, data_compra=data_parcela, categoria=categoria, total_parcelas=num_parcelas, parcela_atual=i + 1, id_compra_original=id_compra_original, observacao=observacao)
            self._compras_cartao.append(nova_compra)
        return True
    def salvar_dados(self):
        dados_completos = {"contas": [c.para_dict() for c in self._contas], "transacoes": [t.para_dict() for t in self._transacoes], "cartoes_credito": [cc.para_dict() for cc in self._cartoes_credito], "compras_cartao": [cp.para_dict() for cp in self._compras_cartao], "categorias": self._categorias, "faturas": [f.para_dict() for f in self._faturas]}
        with open(self._arquivo_dados, 'w', encoding='utf-8') as f: json.dump(dados_completos, f, indent=4, ensure_ascii=False)
    def carregar_dados(self):
        try:
            with open(self._arquivo_dados, 'r', encoding='utf-8') as f: dados_completos = json.load(f)
            self._contas = []
            for dados_conta in dados_completos.get("contas", []):
                tipo_classe = dados_conta.pop("tipo_classe")
                if tipo_classe == "ContaCorrente": self._contas.append(ContaCorrente(**dados_conta))
                elif tipo_classe == "ContaInvestimento":
                    lista_ativos_dados = dados_conta.pop("ativos", []); nova_conta_invest = ContaInvestimento(**dados_conta)
                    for dados_ativo in lista_ativos_dados: nova_conta_invest.adicionar_ativo(Ativo(**dados_ativo))
                    self._contas.append(nova_conta_invest)
            self._transacoes = []
            for dados_transacao in dados_completos.get("transacoes", []):
                dados_transacao["data_transacao"] = date.fromisoformat(dados_transacao.pop("data"))
                if "categoria" not in dados_transacao: dados_transacao["categoria"] = "Não categorizado"
                self._transacoes.append(Transacao(**dados_transacao))
            self._cartoes_credito = [CartaoCredito(**d) for d in dados_completos.get("cartoes_credito", [])]
            self._compras_cartao = []
            for d in dados_completos.get("compras_cartao", []):
                d["data_compra"] = date.fromisoformat(d.pop("data_compra"))
                self._compras_cartao.append(CompraCartao(**d))
            self._faturas = []
            for d in dados_completos.get("faturas", []):
                d["data_fechamento"] = date.fromisoformat(d.pop("data_fechamento"))
                d["data_vencimento"] = date.fromisoformat(d.pop("data_vencimento"))
                self._faturas.append(Fatura(**d))
            self._categorias = dados_completos.get("categorias", ["Moradia", "Alimentação", "Transporte", "Lazer", "Saúde", "Educação", "Salário", "Outros"])
        except (FileNotFoundError, json.JSONDecodeError):
            self._contas, self._transacoes, self._cartoes_credito, self._compras_cartao, self._faturas, self._categorias = [], [], [], [], [], ["Moradia", "Alimentação", "Transporte", "Lazer", "Saúde", "Educação", "Salário", "Outros"]
    def adicionar_cartao_credito(self, cartao: CartaoCredito): self._cartoes_credito.append(cartao)
    def buscar_cartao_por_id(self, id_cartao: str) -> Optional[CartaoCredito]: return next((c for c in self._cartoes_credito if c.id_cartao == id_cartao), None)
    def remover_compra_cartao(self, id_compra_original: str) -> bool:
        compras_para_remover = [c for c in self._compras_cartao if c.id_compra_original == id_compra_original]
        if not compras_para_remover: return False
        self._compras_cartao = [c for c in self._compras_cartao if c.id_compra_original != id_compra_original]
        return True
    def comprar_ativo(self, id_conta_destino: str, ticker: str, quantidade: float, preco_unitario: float, tipo_ativo: str, data_compra: date) -> bool:
        conta_destino = self.buscar_conta_por_id(id_conta_destino)
        if not isinstance(conta_destino, ContaInvestimento): return False
        custo_total = quantidade * preco_unitario
        if not conta_destino.sacar(custo_total): return False
        conta_destino.atualizar_ou_adicionar_ativo(ticker, quantidade, preco_unitario, tipo_ativo)
        detalhes = {"ticker": ticker, "quantidade": quantidade, "preco_unitario": preco_unitario}
        self._apenas_registrar_transacao(id_conta_destino, f"Compra de {quantidade}x {ticker}", custo_total, "Despesa", data_compra, "Compra de Ativo", detalhes_operacao=detalhes)
        return True
    def reverter_compra_ativo(self, id_transacao: str) -> bool:
        transacao = next((t for t in self._transacoes if t.id_transacao == id_transacao), None)
        if not transacao or not transacao.detalhes_operacao: return False
        conta_invest = self.buscar_conta_por_id(transacao.id_conta)
        if not isinstance(conta_invest, ContaInvestimento): return False
        detalhes = transacao.detalhes_operacao; ticker = detalhes["ticker"]; quantidade = detalhes["quantidade"]; preco_unitario = detalhes["preco_unitario"]; custo_total = quantidade * preco_unitario
        if not conta_invest.reverter_operacao_ativo(ticker, quantidade, preco_unitario): return False
        conta_invest.depositar(custo_total); self._transacoes.remove(transacao)
        return True
    def remover_transacao(self, id_transacao: str) -> bool:
        transacao = next((t for t in self._transacoes if t.id_transacao == id_transacao), None)
        if not transacao: return False
        if transacao.categoria == "Compra de Ativo": return self.reverter_compra_ativo(id_transacao)
        conta_afetada = self.buscar_conta_por_id(transacao.id_conta)
        if conta_afetada:
            valor_reversao = -transacao.valor if transacao.tipo == "Receita" else transacao.valor
            conta_afetada.alterar_saldo(valor_reversao)
        self._transacoes.remove(transacao)
        return True
    def _apenas_registrar_transacao(self, id_conta: str, descricao: str, valor: float, tipo: str, data_transacao: date, categoria: str, detalhes_operacao: Dict = None, observacao: str = ""):
        nova_transacao = Transacao(id_conta, descricao, valor, tipo, data_transacao, categoria, detalhes_operacao=detalhes_operacao, observacao=observacao)
        self._transacoes.append(nova_transacao)
    def registrar_transacao(self, id_conta: str, descricao: str, valor: float, tipo: str, data_transacao: date, categoria: str, observacao: str = "") -> bool:
        conta = self.buscar_conta_por_id(id_conta)
        if not conta: return False
        valor_efetivo = valor if tipo == "Receita" else -valor
        if tipo == "Despesa":
            if isinstance(conta, ContaCorrente) and valor > conta.saldo_disponivel_saque: return False
            if isinstance(conta, ContaInvestimento) and valor > conta.saldo_caixa: return False
        conta.alterar_saldo(valor_efetivo)
        self._apenas_registrar_transacao(id_conta, descricao, valor, tipo, data_transacao, categoria, observacao=observacao)
        return True
    def realizar_transferencia(self, id_origem: str, id_destino: str, valor: float) -> bool:
        conta_origem = self.buscar_conta_por_id(id_origem); conta_destino = self.buscar_conta_por_id(id_destino)
        if not all([conta_origem, conta_destino]) or id_origem == id_destino or valor <= 0: return False
        if conta_origem.sacar(valor):
            conta_destino.depositar(valor)
            hoje = date.today()
            self._apenas_registrar_transacao(id_origem, f"Transferência para {conta_destino.nome}", valor, "Despesa", hoje, "Transferência")
            self._apenas_registrar_transacao(id_destino, f"Transferência de {conta_origem.nome}", valor, "Receita", hoje, "Transferência")
            return True
        return False
    def adicionar_conta(self, conta: Conta):
        if not isinstance(conta, Conta): return
        self._contas.append(conta)
    def buscar_conta_por_id(self, id_conta: str) -> Optional[Conta]:
        for conta in self._contas:
            if conta.id_conta == id_conta: return conta
        return None
    def remover_conta(self, id_conta: str) -> bool:
        conta_para_remover = self.buscar_conta_por_id(id_conta)
        if conta_para_remover:
            self._contas.remove(conta_para_remover)
            self._transacoes = [t for t in self._transacoes if t.id_conta != id_conta]
            return True
        return False
