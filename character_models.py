from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class CharacterSheet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    series: Optional[str] = None
    description: Optional[str] = None
    
    visual_description_for_ai: Optional[str] = None 
    
    personality_traits: List[str] = []
    catchphrases: List[str] = []

    def persona_prompt(self) -> str:
        """
        Construye un texto base para que el bot hable como el personaje.
        """
        parts = []
        parts.append(f"Eres {self.name} de la serie {self.series}." if self.series else f"Eres {self.name}.")
        if self.description:
            parts.append(f"Descripción: {self.description}")
        if self.personality_traits:
            parts.append("Rasgos de personalidad: " + ", ".join(self.personality_traits))
        if self.catchphrases:
            parts.append("Frases típicas (úsalas con moderación): " + ", ".join(self.catchphrases))
        return "\n".join(parts)