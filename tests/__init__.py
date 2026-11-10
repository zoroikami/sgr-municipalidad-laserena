import sys
from pathlib import Path

# Permitir que las pruebas unitarias históricas encuentren los módulos de evaluación 2
eval2_path = str(Path(__file__).resolve().parent.parent / 'evaluacion2')
if eval2_path not in sys.path:
    sys.path.insert(0, eval2_path)
