from dataclasses import dataclass, field
from typing import Dict, Optional

@dataclass
class EV:
    id: int
    arrival_time: int      # Epoch de chegada
    departure_time: int    # Epoch de partida
    required_energy: float # Demanda Total (kWh)
    current_energy_needed: float # Demanda Restante (kWh)
    
    assigned_charger_id: Optional[int] = None
    assigned_connector_id: Optional[int] = None

@dataclass
class Charger:
    id: int
    max_power: float       # kW
    num_connectors: int
    is_level_3: bool
    
    connected_evs: Dict[int, int] = field(default_factory=dict)

    def get_available_connectors(self) -> int:
        return self.num_connectors - len(self.connected_evs)