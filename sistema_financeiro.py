# --- ARQUIVO: sistema_financeiro.py (VERSÃO 43 - SALDO EM CAIXA E CORREÇÕES) ---

import json
from abc import ABC, abstractmethod
from uuid import uuid4
from datetime import date
from typing import List, Optional, Dict, Any

class Ativo:
    # ... (sem mudanças)
    def __init__(self, ticker: str, quantidade: float, preco_medio: float, tipo_ativo: str):
        self.ticker, self.quantidade, self.preco_medio, self.tipo_ativo = ticker, quantidade, preco_medio, tipo_ativo
    @property
    def valor_total(self) -> float: return self.quantidade * self.preco_medio
    def para_dict(self) -> Dict[str, Any]: return self.__dict__

class Transacao:
    # ... (sem mudanças)
    def __init__(self, id_conta: str, descricao: str, valor: float, tipo: str, data_transacao: date, categoria: str, id_transacao: str = None):
        self.id_transacao = id_transacao if id_transacao else str(uuid4())
        self.id_conta, self.descricao, self.valor, self.tipo, self.data, self.categoria = id_conta, descricao, valor, tipo, data_transacao, categoria
    def para_dict(self) -> Dict[str, Any]:
        return {"id_transacao": self.id_transacao, "id_conta": self.id_conta, "descricao": self.descricao, "valor": self.valor, "tipo": self.tipo, "data": self.data.isoformat(), "categoria": self.categoria}

class Conta(ABC):
    # ... (sem mudanças)
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
    # ... (sem mudanças)
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

# --- MUDANÇA DRÁSTICA NA ContaInvestimento ---
class ContaInvestimento(Conta):
    def __init__(self, nome: str, saldo: float = 0.0, **kwargs):
        # O 'saldo' da conta pai agora representa o SALDO EM CAIXA.
        super().__init__(nome, saldo, **kwargs)
        self._ativos: List[Ativo] = []

    @property
    def saldo_caixa(self) -> float:
        """Retorna o dinheiro parado na corretora."""
        return self._saldo

    @property
    def valor_em_ativos(self) -> float:
        """Retorna o valor total apenas dos ativos investidos."""
        return sum(ativo.valor_total for ativo in self._ativos)

    @property
    def saldo(self) -> float:
        """O saldo total da conta é o caixa + o valor dos ativos."""
        return self.saldo_caixa + self.valor_em_ativos

    @property
    def ativos(self) -> List[Ativo]:
        return self._ativos

    def atualizar_ou_adicionar_ativo(self, ticker: str, quantidade_compra: float, preco_compra: float, tipo_ativo: str):
        for ativo in self._ativos:
            if ativo.ticker.upper() == ticker.upper():
                custo_total_antigo = ativo.quantidade * ativo.preco_medio
                custo_total_compra = quantidade_compra * preco_compra
                nova_quantidade = ativo.quantidade + quantidade_compra
                ativo.preco_medio = (custo_total_antigo + custo_total_compra) / nova_quantidade
                ativo.quantidade = nova_quantidade
                return
        novo_ativo = Ativo(ticker.upper(), quantidade_compra, preco_compra, tipo_ativo)
        self._ativos.append(novo_ativo)

    # O método sacar agora saca do SALDO EM CAIXA.
    def sacar(self, valor: float) -> bool:
        if not isinstance(valor, (int, float)) or valor <= 0: return False
        if valor > self.saldo_caixa: return False
        self._saldo -= valor # Debita do saldo em caixa (_saldo)
        return True

    def para_dict(self) -> Dict[str, Any]:
        # Salvamos o saldo em caixa como 'saldo' e a lista de ativos.
        dados = super().para_dict()
        dados["ativos"] = [ativo.para_dict() for ativo in self._ativos]
        return dados

# --- MUDANÇAS NO GERENCIADOR ---
class GerenciadorContas:
    def __init__(self, arquivo_dados: str):
        self._contas: List[Conta] = []
        self._transacoes: List[Transacao] = []
        self._arquivo_dados = arquivo_dados
        self.carregar_dados()
    
    @property
    def contas(self) -> List[Conta]: return self._contas
    @property
    def transacoes(self) -> List[Transacao]: return self._transacoes

    # MUDANÇA: Lógica de compra agora usa o caixa da corretora
    def comprar_ativo(self, id_conta_destino: str, ticker: str, quantidade: float, preco_unitario: float, tipo_ativo: str, data_compra: date) -> bool:
        conta_destino = self.buscar_conta_por_id(id_conta_destino)
        if not isinstance(conta_destino, ContaInvestimento): return False
        
        custo_total = quantidade * preco_unitario
        # Tira o dinheiro do caixa da PRÓPRIA corretora
        if not conta_destino.sacar(custo_total): return False

        conta_destino.atualizar_ou_adicionar_ativo(ticker, quantidade, preco_unitario, tipo_ativo)
        
        descricao_transacao = f"Compra de {quantidade}x {ticker}"
        self._apenas_registrar_transacao(id_conta_destino, descricao_transacao, custo_total, "Despesa", data_compra, "Compra de Ativo")
        return True

    # NOVO MÉTODO: Remover transação
    def remover_transacao(self, id_transacao: str) -> bool:
        transacao_para_remover = next((t for t in self._transacoes if t.id_transacao == id_transacao), None)
        if not transacao_para_remover: return False

        conta_afetada = self.buscar_conta_por_id(transacao_para_remover.id_conta)
        if conta_afetada:
            # Reverte o efeito da transação no saldo da conta
            valor_reversao = -transacao_para_remover.valor if transacao_para_remover.tipo == "Receita" else transacao_para_remover.valor
            conta_afetada.alterar_saldo(valor_reversao)
        
        self._transacoes.remove(transacao_para_remover)
        return True

    # ... (resto do Gerenciador)
    def _apenas_registrar_transacao(self, id_conta: str, descricao: str, valor: float, tipo: str, data_transacao: date, categoria: str):
        nova_transacao = Transacao(id_conta, descricao, valor, tipo, data_transacao, categoria)
        self._transacoes.append(nova_transacao)
    def registrar_transacao(self, id_conta: str, descricao: str, valor: float, tipo: str, data_transacao: date, categoria: str) -> bool:
        conta = self.buscar_conta_por_id(id_conta)
        if not conta: return False
        valor_efetivo = valor if tipo == "Receita" else -valor
        if tipo == "Despesa":
            if isinstance(conta, ContaCorrente) and valor > conta.saldo_disponivel_saque: return False
            if isinstance(conta, ContaInvestimento) and valor > conta.saldo_caixa: return False
        conta.alterar_saldo(valor_efetivo)
        self._apenas_registrar_transacao(id_conta, descricao, valor, tipo, data_transacao, categoria)
        return True
    def realizar_transferencia(self, id_origem: str, id_destino: str, valor: float) -> bool:
        conta_origem = self.buscar_conta_por_id(id_origem)
        conta_destino = self.buscar_conta_por_id(id_destino)
        if not all([conta_origem, conta_destino]) or id_origem == id_destino or valor <= 0: return False
        if conta_origem.sacar(valor):
            conta_destino.depositar(valor)
            hoje = date.today()
            self._apenas_registrar_transacao(id_origem, f"Transferência para {conta_destino.nome}", valor, "Despesa", hoje, "Transferência")
            self._apenas_registrar_transacao(id_destino, f"Transferência de {conta_origem.nome}", valor, "Receita", hoje, "Transferência")
            return True
        return False
    def salvar_dados(self):
        dados_completos = {"contas": [c.para_dict() for c in self._contas], "transacoes": [t.para_dict() for t in self._transacoes]}
        with open(self._arquivo_dados, 'w', encoding='utf-8') as f: json.dump(dados_completos, f, indent=4, ensure_ascii=False)
    def carregar_dados(self):
        try:
            with open(self._arquivo_dados, 'r', encoding='utf-8') as f: dados_completos = json.load(f)
            self._contas = []
            for dados_conta in dados_completos.get("contas", []):
                tipo_classe = dados_conta.pop("tipo_classe")
                if tipo_classe == "ContaCorrente": self._contas.append(ContaCorrente(**dados_conta))
                elif tipo_classe == "ContaInvestimento":
                    lista_ativos_dados = dados_conta.pop("ativos", [])
                    nova_conta_invest = ContaInvestimento(**dados_conta)
                    for dados_ativo in lista_ativos_dados: nova_conta_invest.adicionar_ativo(Ativo(**dados_ativo))
                    self._contas.append(nova_conta_invest)
            self._transacoes = []
            for dados_transacao in dados_completos.get("transacoes", []):
                dados_transacao["data_transacao"] = date.fromisoformat(dados_transacao.pop("data"))
                if "categoria" not in dados_transacao: dados_transacao["categoria"] = "Não categorizado"
                self._transacoes.append(Transacao(**dados_transacao))
        except (FileNotFoundError, json.JSONDecodeError): self._contas, self._transacoes = [], []
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
