import numpy as np

class FeatureExtractor:
    def __init__(self, tau_minutes=15):
        self.tau = tau_minutes

    def get_basis_functions(self, evs, chargers, current_epoch):
        """
        Retorna vetor phi normalizado.
        """
        phi_0 = 1.0 # Bias
        
        # 1. Scheduled EVs
        phi_1 = sum(1 for ev in evs if ev.assigned_charger_id is not None)

        # 2. Available Connectors
        phi_2 = sum(c.get_available_connectors() for c in chargers)

        # 3. Remaining Charge (Total)
        phi_3 = sum(ev.current_energy_needed for ev in evs)

        # 4. Urgency Score
        phi_4 = 0.0
        for ev in evs:
            if ev.assigned_charger_id is None and ev.departure_time > current_epoch:
                time_rem = ev.departure_time - current_epoch
                phi_4 += 1.0 / max(time_rem, 0.1)

        # 5. Time (NORMALIZADO: 0.0 a 1.0)
        # Isso corrige a instabilidade do gradiente
        total_day_minutes = 96 * self.tau
        current_minutes = current_epoch * self.tau
        phi_5 = current_minutes / total_day_minutes

        return [phi_0, phi_1, phi_2, phi_3, phi_4, phi_5]