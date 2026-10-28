"""Inspect the three existing graph generators without opening a plot window."""
import matplotlib
matplotlib.use("Agg")
import networkx as nx

from port_generator import PortGenerator


if __name__ == "__main__":
    for name in ("prat", "mardones", "natales"):
        generator = PortGenerator(seed=42)
        graph = getattr(generator, f"generate_{name}_variant")()
        print(f"{name}: nodes={graph.number_of_nodes()}, edges={graph.number_of_edges()}, "
              f"connected_components={nx.number_connected_components(graph)}")
