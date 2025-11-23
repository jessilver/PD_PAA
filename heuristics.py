def solve_heuristic(evs, chargers, rule, tau=15):
    decisions = []
    # Filtra apenas quem precisa de carga
    active_evs = [e for e in evs if e.current_energy_needed > 0.001]
    
    if not active_evs:
        return []

    # Ordenação baseada na regra
    if rule == 'FCLD': # First Come, Largest Demand
        active_evs.sort(key=lambda x: (x.arrival_time, -x.required_energy))
    elif rule == 'EDLD': # Earliest Due, Largest Demand
        active_evs.sort(key=lambda x: (x.departure_time, -x.required_energy))

    # Alocação Gulosa
    allocated_ev_ids = set()
    
    for charger in chargers:
        available_slots = charger.get_available_connectors()
        
        for k in range(available_slots):
            # Busca o próximo carro da fila que ainda não foi alocado
            candidate = next((e for e in active_evs if e.id not in allocated_ev_ids), None)
            
            if candidate:
                # Carrega o máximo possível (ASAP)
                power = min(charger.max_power, candidate.current_energy_needed / (tau/60.0))
                
                # Descobre qual conector fisico usar (logica sequencial)
                connector_idx = charger.num_connectors - available_slots + k
                
                decisions.append({
                    'charger_id': charger.id,
                    'connector_id': connector_idx,
                    'ev_id': candidate.id,
                    'charge_rate': power
                })
                allocated_ev_ids.add(candidate.id)

    return decisions