# Port Modules

Prototipo exploratorio en Python para construir **grafos de infraestructura
portuaria** con NetworkX y visualizarlos con Matplotlib. Incluye variantes
paramétricas inspiradas en Prat, Mardones y Natales.

El módulo representa nodos, conexiones, posiciones y atributos de capacidad. No
incluye simulación dinámica de tráfico, entrenamiento de una GNN ni un optimizador
operativo. Los nombres y dimensiones presentes en el código deben interpretarse
como supuestos del prototipo, no como una representación certificada de los puertos.

Este repositorio es distinto del proyecto de simulación de tráfico del Puerto San
Antonio descrito en mi perfil.

## Ejecutar un ejemplo

Requiere Python 3.10 o superior. Desde la raíz del clon:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python examples.py
```

El ejemplo genera las tres variantes con una semilla fija e imprime cantidades de
nodos, aristas y componentes conexas, sin abrir ventanas. En la versión actual,
con semilla 42:

| Variante | Nodos | Aristas | Componentes conexas |
|---|---:|---:|---:|
| Prat | 49 | 48 | 3 |
| Mardones | 181 | 306 | 1 |
| Natales | 31 | 32 | 4 |

Prat y Natales contienen componentes desconectadas; antes de usar algoritmos de
ruteo debe revisarse si esas separaciones corresponden al modelo deseado.

Para visualizar una:

```python
from port_generator import PortGenerator

generator = PortGenerator(seed=42)
graph = generator.generate_prat_variant()
generator.visualize("Prototipo de grafo portuario")
```

## Alcance técnico

- `PortGenerator` conserva el grafo actual en `self.graph`. Cada llamada a un
  generador limpia y reutiliza ese grafo; usa `.copy()` si necesitas conservarlo.
- La semilla modifica los generadores globales de `random` y NumPy.
- Las capacidades y clases de nodos no constituyen un modelo validado de operación.
- Faltan validación de parámetros, trazabilidad de supuestos y pruebas sistemáticas
  de conectividad antes de usar estas estructuras en otro sistema.

El código principal está en [port_generator.py](port_generator.py).
