from abc import ABC, abstractmethod

class BaseDataSource(ABC):
  @abstractmethod
  def get_deposits(self, wallet_address, from_ms=None, to_ms=None):
    pass

  @abstractmethod
  def get_user_fills(self, user: str, from_ms: int = None, to_ms: int = None):
    pass