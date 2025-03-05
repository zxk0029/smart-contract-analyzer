from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class ContractEvent:
    event: str
    returnValues: Dict[str, Any]
    blockNumber: int
