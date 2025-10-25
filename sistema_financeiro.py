# --- ARQUIVO: sistema_financeiro.py (VERSÃO 9) ---

import json
from abc import ABC, abstractmethod
from uuid import uuid4
from typing import List, Optional, Dict, Any

class Conta(ABC):
    def __init__(self, nome: str, saldo: float = 0.0, id_conta: str = None):
        # ... construtor sem mudanças ...
        if not isinstance(nome, str) or not nome.strip(): raise ValueError("O nome da conta não pode ser vazio.")
        if not isinstance(saldo, (int, float)) or saldo < 0: raise ValueError("O saldo inicial deve ser um número não negativo.")
        self._id_conta = id_conta if id_conta else str(uuid4())
        self._nome = nome
        self._saldo = saldo
    
    # --- NOVO MÉTODO NA CLASSE BASE ---
    def editar_nome(self, novo_nome: str):
        """Altera o nome da conta."""
        if isinstance(novo_nome, str) and novo_nome.strip():
            self._nome = novo_nome
            return True
        return False

    # ... resto dos métodos da Conta ...
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
    @abstractmethod
    def para_dict(self) -> Dict[str, Any]:
        return {"id_conta": self.id_conta, "tipo_classe": self.__class__.__name__, "nome": self.nome, "saldo": self.saldo}
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(nome='{self.nome}', saldo=R${self.saldo:.2f})>"

# As classes ContaCorrente e ContaInvestimento não precisam de mudanças nesta etapa.
# Cole o conteúdo delas aqui. Para garantir, segue abaixo:
class ContaCorrente(Conta):
    def __init__(self, nome: str, saldo: float = 0.0, limite_cheque_especial: float = 0.0, id_conta: str = None):
        super().__init__(nome, saldo, id_conta)
        if not isinstance(limite_cheque_especial, (int, float)) or limite_cheque_especial < 0: raise ValueError("O limite do cheque especial deve ser um número não negativo.")
        self._limite_cheque_especial = limite_cheque_especial
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
        dados = super().para_dict()
        dados["limite_cheque_especial"] = self.limite_cheque_especial
        return dados

class ContaInvestimento(Conta):
    def __init__(self, nome: str, tipo_investimento: str, saldo: float = 0.0, id_conta: str = None):
        super().__init__(nome, saldo, id_conta)
        if not isinstance(tipo_investimento, str) or not tipo_investimento.strip(): raise ValueError("O tipo de investimento não pode ser vazio.")
        self._tipo_investimento = tipo_investimento
    @property
    def tipo_investimento(self) -> str: return self._tipo_investimento
    def sacar(self, valor: float) -> bool:
        if not isinstance(valor, (int, float)) or valor <= 0: return False
        if valor > self.saldo: return False
        self._saldo -= valor
        return True
    def para_dict(self) -> Dict[str, Any]:
        dados = super().para_dict()
        dados["tipo_investimento"] = self.tipo_investimento
        return dados

# --- MUDANÇAS IMPORTANTES NO GERENCIADOR ---
class GerenciadorContas:
    def __init__(self, arquivo_dados: str):
        self._contas: List[Conta] = []
        self._arquivo_dados = arquivo_dados
        self.carregar_dados()
    
    @property
    def contas(self) -> List[Conta]:
        return self._contas

    def adicionar_conta(self, conta: Conta):
        if not isinstance(conta, Conta): return
        self._contas.append(conta)
    
    def buscar_conta_por_id(self, id_conta: str) -> Optional[Conta]:
        for conta in self._contas:
            if conta.id_conta == id_conta: return conta
        return None

    # --- NOVO MÉTODO ---
    def remover_conta(self, id_conta: str) -> bool:
        """Remove uma conta da lista pelo seu ID."""
        conta_para_remover = self.buscar_conta_por_id(id_conta)
        if conta_para_remover:
            self._contas.remove(conta_para_remover)
            return True
        return False

    def realizar_transferencia(self, id_origem: str, id_destino: str, valor: float) -> bool:
        # ... método sem mudanças ...
        conta_origem = self.buscar_conta_por_id(id_origem)
        conta_destino = self.buscar_conta_por_id(id_destino)
        if not all([conta_origem, conta_destino]) or id_origem == id_destino or valor <= 0: return False
        if conta_origem.sacar(valor):
            conta_destino.depositar(valor)
            return True
        return False

    def salvar_dados(self):
        # ... método sem mudanças ...
        with open(self._arquivo_dados, 'w', encoding='utf-8') as f:
            json.dump([c.para_dict() for c in self._contas], f, indent=4, ensure_ascii=False)

    def carregar_dados(self):
        # ... método sem mudanças ...
        try:
            with open(self._arquivo_dados, 'r', encoding='utf-8') as f:
                dados_carregados = json.load(f)
            self._contas = []
            for dados_conta in dados_carregados:
                tipo_classe = dados_conta.pop("tipo_classe")
                if tipo_classe == "ContaCorrente": nova_conta = ContaCorrente(**dados_conta)
                elif tipo_classe == "ContaInvestimento": nova_conta = ContaInvestimento(**dados_conta)
                else: continue
                self._contas.append(nova_conta)
        except (FileNotFoundError, json.JSONDecodeError):
            self._contas = []
