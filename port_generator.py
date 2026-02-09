"""Port layout generator module."""

from __future__ import annotations

import random
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np


class PortGenerator:
    def __init__(self, seed: int | None = None) -> None:
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)
        self.graph = nx.Graph()

    def _add_node(self, node_id: str, pos: Tuple[float, float], node_type: str, capacity: float = 1.0) -> None:
        """Añade un nodo con metadatos para la HetGNN"""
        self.graph.add_node(node_id, pos=pos, type=node_type, capacity=capacity, occupied=0)

    def generate_prat_variant(
        self,
        bridge_length: int = 270,
        head_length: int = 103,
        noise_factor: float = 0.05,
    ) -> nx.Graph:
        """
        Genera el Terminal Arturo Prat (Punta Arenas) con fidelidad ingenieril.
        Estructura: Muelle de penetración segmentado (Puente + Cabezo).
        Capacidad: 6 Sitios, Dolphins para cruceros, Zona MXU terrestre.
        """
        self.graph.clear()
        print(f"🏗️ Generando PRAT REAL (Bridge: {bridge_length}m + Head: {head_length}m)")

        # --- 1. VARIABILIDAD PARAMÉTRICA ---
        # Aplicamos ruido leve para robustez del entrenamiento
        act_bridge_len = int(bridge_length * random.uniform(1.0 - noise_factor, 1.0 + noise_factor))
        act_head_len = int(head_length * random.uniform(1.0 - noise_factor, 1.0 + noise_factor))
        total_pier_len = act_bridge_len + act_head_len

        # --- 2. GENERACIÓN DEL TRONCAL (ESPIGÓN) ---
        # El muelle es una "columna vertebral" con nodos cada 10 metros
        # Segmento A: Puente de Acceso (Más angosto, 16.8m)
        num_bridge_nodes = act_bridge_len // 10
        for i in range(num_bridge_nodes):
            node_id = f"Bridge_Segment_{i}"
            # Capacidad restringida por ancho (un carril ida/vuelta apretado)
            self._add_node(node_id, (0, i * 10), "PIER_ACCESS_ROAD", capacity=1)
            if i > 0:
                self.graph.add_edge(f"Bridge_Segment_{i-1}", node_id, distance=10, width=16.8)

        # Segmento B: Cabezo (Más ancho, 17.5m, estructura mixta)
        start_head_idx = num_bridge_nodes
        num_head_nodes = act_head_len // 10
        for i in range(num_head_nodes):
            idx = start_head_idx + i
            node_id = f"Head_Segment_{i}"
            # El cabezo suele tener mayor resistencia para grúas móviles
            self._add_node(node_id, (0, idx * 10), "PIER_HEAD_OPERATIONAL", capacity=2)

            # Conexión con el segmento anterior (sea puente o cabezo)
            prev_node = f"Bridge_Segment_{num_bridge_nodes-1}" if i == 0 else f"Head_Segment_{i-1}"
            self.graph.add_edge(prev_node, node_id, distance=10, width=17.5)

        # --- 3. SITIOS DE ATRAQUE (BERTHS) ---
        # Mapeamos los 6 sitios a lo largo del muelle (Simetría Norte/Sur)
        # Distancias aproximadas desde la costa (Y=0)
        sitios_config: List[Tuple[str, int, int, float, str]] = [
            # (Nombre, Y_inicio, Largo, Calado, Tipo)
            ("Sitio_3", 20, 73, 5.0, "BERTH_SMALL"),  # Cerca de tierra, naves menores
            ("Sitio_2", 100, 108, 9.0, "BERTH_MED"),  # Mitad del puente
            ("Sitio_1", 210, 163, 18.0, "BERTH_DEEP"),  # Cabezo y final del puente (Deep water)
        ]

        for nombre, y_start, length, draft, b_type in sitios_config:
            # Calculamos el nodo central de este sitio para conectarlo al troncal
            center_y = y_start + (length / 2)
            # Buscamos el nodo troncal más cercano
            closest_segment_idx = int(center_y // 10)

            # Ajuste por si el sitio cae en el puente o cabeza
            if closest_segment_idx < num_bridge_nodes:
                connector_node = f"Bridge_Segment_{closest_segment_idx}"
            else:
                head_idx = closest_segment_idx - num_bridge_nodes
                # Clamp para no salirnos del array
                head_idx = min(head_idx, num_head_nodes - 1)
                connector_node = f"Head_Segment_{head_idx}"

            # Crear nodos Norte y Sur
            for side in ["Norte", "Sur"]:
                berth_id = f"{nombre}_{side}"
                x_pos = -25 if side == "Norte" else 25  # Desplazamiento lateral visual

                features = {
                    "length_m": length,
                    "draft_m": draft,
                    "max_disp_ton": 15728,
                    "utilities": ["WATER", "ELEC"],  # Recurso disponible
                }
                _ = features

                self._add_node(berth_id, (x_pos, center_y), b_type, capacity=1)
                # Arista de operación (Delantal virtual)
                self.graph.add_edge(connector_node, berth_id, distance=15, type="OPERATION_APRON")

        # --- 4. ESTRUCTURAS DE APOYO (DOLPHINS) ---
        # Permiten atender cruceros > largo del muelle (250m)
        tip_node = f"Head_Segment_{num_head_nodes-1}"

        self._add_node("Dolphin_1", (0, total_pier_len + 25), "MOORING_DOLPHIN")
        self._add_node("Dolphin_2", (0, total_pier_len + 50), "MOORING_DOLPHIN")

        # Conexión lógica (amarras), no física para camiones
        self.graph.add_edge(tip_node, "Dolphin_1", distance=25, type="MOORING_LINE")
        self.graph.add_edge("Dolphin_1", "Dolphin_2", distance=25, type="MOORING_LINE")

        # --- 5. ZONA TERRESTRE (BACKLAND - MXU) ---
        # Nodo Gate (Punto cero real)
        self._add_node("Gate_Costanera", (0, -10), "GATE_MAIN", capacity=10)
        self.graph.add_edge("Gate_Costanera", "Bridge_Segment_0", distance=10, type="ACCESS_CONTROL")

        # Zona Mixta (MXU) - Explanadas
        # Lado Norte: Pasajeros / Antártico
        self._add_node("Sala_Pasajeros", (-40, -20), "PAX_TERMINAL", capacity=500)  # Pax aumentados
        self._add_node("Bodega_Antartica", (-40, 20), "WAREHOUSE_NASA", capacity=1000)

        # Lado Sur: Carga / Turismo
        self._add_node("Patio_Carga_MXU", (40, 0), "YARD_OPEN", capacity=2000)  # ~8000m2 pavimentados
        self._add_node("Estacionamiento_Turismo", (40, -30), "PARKING_BUS", capacity=20)

        # Conectividad Terrestre
        self.graph.add_edge("Gate_Costanera", "Sala_Pasajeros", distance=50, type="ROAD_PAVED")
        self.graph.add_edge("Gate_Costanera", "Patio_Carga_MXU", distance=50, type="ROAD_PAVED")

        # Conexión operativa (shuttle bus / grúas horquilla hacia el muelle)
        self.graph.add_edge("Sala_Pasajeros", "Bridge_Segment_0", distance=30, type="WALKWAY_SEGREGATED")
        self.graph.add_edge("Patio_Carga_MXU", "Bridge_Segment_0", distance=30, type="CARGO_LANE")

        return self.graph

    def generate_mardones_variant(
        self,
        bridge_length: int = 130,
        head_length: int = 150,
        paved_area_rows: int = 15,
        paved_area_cols: int = 10,
        noise_factor: float = 0.05,
    ) -> nx.Graph:
        """
        Genera el Terminal Mardones con fidelidad operativa real.
        Topología: Muelle L-Shape (Puente + Cabezo) + Patio Industrial Segmentado.
        Reto IA: Gestión de cuello de botella (Puente 10m ancho) y Tetris en zonas no arrendadas.
        """
        self.graph.clear()
        print(f"🏗️ Generando MARDONES REAL (Puente: {bridge_length}m - Cabezo: {head_length}m)")

        # --- 1. PUENTE DE ACCESO (EL CUELLO DE BOTELLA) ---
        # Largo 130m, Ancho 10m. Es la única vía de entrada/salida.
        actual_bridge_len = int(bridge_length * random.uniform(1.0 - noise_factor, 1.0 + noise_factor))
        num_bridge_nodes = actual_bridge_len // 10  # Nodos cada 10 metros

        for i in range(num_bridge_nodes):
            node_id = f"Bridge_Segment_{i}"
            # Capacity=1 simulando la dificultad de cruce en 10m de ancho con camiones grandes
            self._add_node(node_id, (0, i * 10), "BOTTLENECK_ACCESS", capacity=1)
            if i > 0:
                self.graph.add_edge(f"Bridge_Segment_{i-1}", node_id, distance=10, type="CONCRETE_SLAB")

        # Punto de conexión Puente-Cabezo
        bridge_end_node = f"Bridge_Segment_{num_bridge_nodes-1}"

        # --- 2. CABEZO (FRENTE DE ATRAQUE) ---
        # Largo 150m, Ancho 20m. Perpendicular al puente.
        actual_head_len = int(head_length * random.uniform(1.0 - noise_factor, 1.0 + noise_factor))

        # El puente llega al inicio del cabezo (Forma de L o Martillo asimétrico)
        # Generamos nodos a lo largo del cabezo
        num_head_nodes = actual_head_len // 15

        for i in range(num_head_nodes):
            head_node_id = f"Head_Deck_{i}"
            # Coordenadas: Desplazado en X desde el final del puente
            pos_x = i * 15
            pos_y = actual_bridge_len + 10  # Un poco más allá del final del puente

            self._add_node(head_node_id, (pos_x, pos_y), "PIER_DECK_HEAVY", capacity=2)

            if i > 0:
                self.graph.add_edge(f"Head_Deck_{i-1}", head_node_id, distance=15, type="PIER_MANEUVER")
            elif i == 0:
                # Conectar el inicio del cabezo con el final del puente
                self.graph.add_edge(bridge_end_node, head_node_id, distance=20, type="TURNING_POINT")

        # --- 3. SITIOS DE ATRAQUE (BERTHS) ---
        # Definidos según Tabla 9: Sitio 1 (Ext), Sitio 2 y 3 (Int)

        # Sitio 1: Exterior (Para naves grandes 65k Ton) - A lo largo de todo el cabezo
        self._add_node("Sitio_1_Exterior", (actual_head_len / 2, actual_bridge_len + 30), "BERTH_PANAMAX", capacity=1)
        # Conectamos Sitio 1 a varios puntos del cabezo para simular múltiples puntos de acceso/carga
        self.graph.add_edge("Sitio_1_Exterior", f"Head_Deck_{num_head_nodes//2}", distance=10, type="SHIP_TO_SHORE")

        # Sitio 2: Interior Lateral (60m) - Cerca del codo
        self._add_node("Sitio_2_Interior", (30, actual_bridge_len - 10), "BERTH_SERVICE", capacity=1)
        self.graph.add_edge("Sitio_2_Interior", "Head_Deck_1", distance=20, type="SHIP_TO_SHORE")

        # Sitio 3: Interior (70m) - Más alejado del codo
        self._add_node("Sitio_3_Interior", (100, actual_bridge_len - 10), "BERTH_BARGE", capacity=1)
        self.graph.add_edge("Sitio_3_Interior", f"Head_Deck_{num_head_nodes-2}", distance=20, type="SHIP_TO_SHORE")

        # --- 4. ÁREA DE RESPALDO (BACKLAND) ---
        # Aquí implementamos la realidad de los arriendos y el espacio pavimentado.

        # Nodo Gate (Inicio del Puente)
        self._add_node("Gate_Mardones", (0, -10), "GATE_MAIN", capacity=5)
        self.graph.add_edge("Gate_Mardones", "Bridge_Segment_0", distance=10, type="ACCESS_CONTROL")

        # A. Zona Pavimentada (Grid de Tetris) ~35.000 m2
        # Generamos una grilla detrás del Gate
        print("   > Generando Grid de Carga General...")
        for r in range(paved_area_rows):
            for c in range(paved_area_cols):
                slot_id = f"Yard_Slot_{r}_{c}"
                # Posición negativa en Y (hacia tierra)
                p_x = (c - paved_area_cols / 2) * 15
                p_y = -30 - (r * 15)

                self._add_node(slot_id, (p_x, p_y), "STORAGE_GENERAL", capacity=1)

                # Conexiones de grilla
                if c > 0:
                    self.graph.add_edge(slot_id, f"Yard_Slot_{r}_{c-1}", distance=15, type="YARD_LANE")
                if r > 0:
                    self.graph.add_edge(slot_id, f"Yard_Slot_{r-1}_{c}", distance=15, type="YARD_LANE")

        # Conectar el Grid al Gate
        entry_slot = f"Yard_Slot_0_{paved_area_cols//2}"
        self.graph.add_edge("Gate_Mardones", entry_slot, distance=20, type="INTERNAL_ROAD")

        # B. Zonas Arrendadas / Específicas (Obstáculos Lógicos o Destinos Fijos)
        # Estas zonas NO son para almacenamiento dinámico general, son destinos específicos.
        reserved_zones: List[Tuple[str, int, str, Tuple[int, int]]] = [
            ("Melon_SA", 1110, "SILO_CEMENTO", (-80, -50)),
            ("Vilicic_Patio", 1652, "LEASED_YARD", (80, -50)),
            ("Vilicic_Bodega", 1200, "WAREHOUSE", (80, -80)),
            ("ULOG_Logistica", 4000, "LOGISTICS_CENTER", (-100, -150)),
            ("Ultraport_Sala", 130, "STAFF_BUILDING", (20, -20)),
        ]

        for name, area, ztype, pos in reserved_zones:
            # Creamos un nodo que representa toda la zona arrendada
            # Para la IA, esto es un "Sink Node" (Destino final) para cierta carga, no un espacio libre.
            self._add_node(name, pos, ztype, capacity=int(area / 30))  # Capacidad aprox en TEUs/Camiones

            # Conectamos a la red vial más cercana (al Grid)
            # Buscamos el nodo del grid más cercano geométricamente (simplificado aquí conectando al borde)
            closest_row = min(abs(int(pos[1] / 15)), paved_area_rows - 1)
            closest_col = 0 if pos[0] < 0 else paved_area_cols - 1
            connector = f"Yard_Slot_{closest_row}_{closest_col}"

            self.graph.add_edge(connector, name, distance=30, type="PRIVATE_ACCESS")

        return self.graph

    def generate_natales_variant(
        self,
        pedraplen_len: int = 85,
        bridge_len: int = 20,
        head_len: int = 33,
        yard_area_m2: int = 17000,
        noise_factor: float = 0.05,
    ) -> nx.Graph:
        """
        Genera el Terminal Puerto Natales (Estructura Compuesta / Dolphins).
        Reto IA: Sincronización Ro-Ro en cuello de botella extremo (8m ancho).
        Física: Atraque virtual (Dolphins) > Estructura física (Cabezo).
        """
        self.graph.clear()
        print(f"🏗️ Generando NATALES REAL (Pedraplén: {pedraplen_len}m - Dolphins System)")

        # --- 1. EL CUELLO DE BOTELLA (PEDRAPLÉN + PUENTE) ---
        # Este es el "Tubo" por donde todo entra y sale.
        # Tramo A: Pedraplén (Terraplén de acceso) - 85m x 8m (CRÍTICO)
        act_pedraplen_len = int(pedraplen_len * random.uniform(1.0 - noise_factor, 1.0 + noise_factor))
        num_pedra_nodes = act_pedraplen_len // 10

        for i in range(num_pedra_nodes):
            node_id = f"Pedraplen_Seg_{i}"
            # Capacity=0.5 -> Indica que apenas cabe 1 camión grande o 2 chicos con riesgo
            self._add_node(node_id, (0, i * 10), "NARROW_EMBANKMENT", capacity=0.8)
            if i > 0:
                # Arista con penalización alta por cruce
                self.graph.add_edge(
                    f"Pedraplen_Seg_{i-1}",
                    node_id,
                    distance=10,
                    width=8.0,
                    risk="HIGH_COLLISION",
                )

        # Tramo B: Puente de Acceso - 20m x 10m (Alivia un poco)
        bridge_start_y = act_pedraplen_len
        bridge_end_node = "Bridge_End"
        self._add_node("Bridge_Start", (0, bridge_start_y), "BRIDGE_JOIN", capacity=1)
        self._add_node(bridge_end_node, (0, bridge_start_y + bridge_len), "BRIDGE_END", capacity=1)

        # Conectar Pedraplén con Puente
        self.graph.add_edge(f"Pedraplen_Seg_{num_pedra_nodes-1}", "Bridge_Start", distance=5, width=8.0)
        self.graph.add_edge("Bridge_Start", bridge_end_node, distance=bridge_len, width=10.0)

        # --- 2. CABEZO EN "L" & DOLPHINS (FRENTE VIRTUAL) ---
        # El hormigón es pequeño (32m), pero el barco es grande (135m).
        # Los Dolphins crean la "cancha" real.
        head_y_start = bridge_start_y + bridge_len

        # Cabezo Físico (Plataforma de Hormigón)
        # Modelamos la L pequeña
        self._add_node("Cabezo_Central", (0, head_y_start + 15), "PIER_HEAD_CONCRETE", capacity=2)
        self.graph.add_edge(bridge_end_node, "Cabezo_Central", distance=15, width=11.0)

        # Extensiones Virtuales (Dolphins)
        # Permiten que atraque un barco de 135m aunque el muelle sea de 30m
        dolphin_dist = 40
        _ = dolphin_dist

        # Dolphins Sur (Para Ro-Ro)
        self._add_node("Dolphin_Sur_1", (20, head_y_start + 40), "DOLPHIN_STRUCT")
        self._add_node("Dolphin_Sur_2", (20, head_y_start + 90), "DOLPHIN_STRUCT")  # Lejos

        # Dolphins Oeste (Para Turismo)
        self._add_node("Dolphin_West_1", (-20, head_y_start + 40), "DOLPHIN_STRUCT")
        self._add_node("Dolphin_West_2", (-20, head_y_start + 90), "DOLPHIN_STRUCT")

        # --- 3. SITIOS DE ATRAQUE (BERTHS) ---

        # SITIO SUR (Ro-Ro / Ferries) - Misión Principal
        # Se conecta directamente al Cabezo Central para que bajen los autos
        self._add_node("Sitio_Sur_RoRo", (25, head_y_start + 15), "BERTH_RORO_RAMP", capacity=1)
        # Features clave para el RL:
        # draft=20m, max_len=135m, NO_CRANE (Usa rampas del barco)
        self.graph.add_edge("Cabezo_Central", "Sitio_Sur_RoRo", distance=5, type="RAMP_CONNECTION")

        # Conexión lógica a los dolphins (amarres)
        self.graph.add_edge("Sitio_Sur_RoRo", "Dolphin_Sur_1", distance=25, type="MOORING_LINE")
        self.graph.add_edge("Sitio_Sur_RoRo", "Dolphin_Sur_2", distance=75, type="MOORING_LINE")

        # SITIO OESTE (Turismo / Pesca)
        self._add_node("Sitio_Weste_Pax", (-25, head_y_start + 15), "BERTH_PAX", capacity=1)
        self.graph.add_edge("Cabezo_Central", "Sitio_Weste_Pax", distance=5, type="GANGWAY_PAX")

        # SITIOS INTERIORES (Naves Menores)
        # En el "sobaco" de la L
        self._add_node("Sitio_Interior_N", (-10, head_y_start + 5), "BERTH_SMALL", capacity=1)
        self.graph.add_edge(bridge_end_node, "Sitio_Interior_N", distance=5, type="SERVICE_ACCESS")

        # --- 4. ZONA TERRESTRE (2 Hectáreas - Buffer FIFO) ---
        # Aquí no hay Tetris complejo, hay COLAS (Queues).
        # Dividido por Av. Pedro Montt (Gate)

        self._add_node("Gate_PedroMontt", (0, -10), "GATE_URBAN", capacity=5)
        self.graph.add_edge("Gate_PedroMontt", "Pedraplen_Seg_0", distance=10, type="ACCESS_ROAD")

        # Explanada Sur (Estacionamiento Camiones / Espera Ferry)
        # Generamos líneas de espera (Lanes)
        num_lanes = 5
        lane_len = 50  # metros

        print("   > Generando Buffer FIFO para Ferry...")
        for L in range(num_lanes):
            lane_start = f"Queue_Lane_{L}_Start"
            lane_end = f"Queue_Lane_{L}_End"

            # Ubicación física en la explanada
            x_pos = 20 + (L * 5)
            self._add_node(lane_start, (x_pos, -20), "QUEUE_ENTRY")
            self._add_node(lane_end, (x_pos, -20 + lane_len), "QUEUE_EXIT")

            # Arista de almacenamiento (Cola)
            self.graph.add_edge(lane_start, lane_end, distance=lane_len, type="WAITING_LANE", capacity=3)  # ~3 camiones por fila

            # Conexión al Gate y al Pedraplén
            self.graph.add_edge("Gate_PedroMontt", lane_start, distance=15, type="YARD_MANEUVER")
            self.graph.add_edge(lane_end, "Pedraplen_Seg_0", distance=20, type="DISPATCH_ROUTE")

        # Zona Mixta / Bodega (Norte)
        self._add_node("Bodega_Fija", (-30, -30), "WAREHOUSE_FIXED", capacity=100)  # 700m2
        self._add_node("Patio_MXU", (-30, -10), "YARD_MIXED", capacity=200)
        self.graph.add_edge("Gate_PedroMontt", "Patio_MXU", distance=20, type="ROAD")

        return self.graph

    def visualize(self, title: str = "") -> None:
        pos: Dict[str, Tuple[float, float]] = nx.get_node_attributes(self.graph, "pos")
        if not pos:
            print("No graph to visualize.")
            return

        types: Dict[str, str] = nx.get_node_attributes(self.graph, "type")
        unique_types = sorted(set(types.values()))
        color_map = {t: plt.cm.tab20(i % 20) for i, t in enumerate(unique_types)}
        node_colors = [color_map.get(types.get(n, ""), (0.5, 0.5, 0.5, 1.0)) for n in self.graph.nodes()]

        plt.figure(figsize=(10, 8))
        nx.draw(
            self.graph,
            pos,
            node_color=node_colors,
            with_labels=False,
            node_size=120,
            edge_color="#999999",
        )
        if title:
            plt.title(title)

        handles = [
            plt.Line2D([0], [0], marker="o", color="w", label=t, markerfacecolor=color_map[t], markersize=8)
            for t in unique_types
        ]
        if handles:
            plt.legend(handles=handles, bbox_to_anchor=(1.02, 1), loc="upper left")

        plt.axis("equal")
        plt.tight_layout()
        plt.show()


__all__ = ["PortGenerator"]
