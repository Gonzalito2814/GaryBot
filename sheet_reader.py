from pathlib import Path
from typing import Any, Dict, Union
import json

def load_character_sheet(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Carga una ficha de personaje desde un archivo JSON.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No existe el archivo de ficha: {p}")
    
    ext = p.suffix.lower()
    if ext != ".json":
        raise ValueError(f"Extensión no soportada: '{ext}'. Solo se aceptan archivos .json")

    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)