import argparse
import json
from character_models import CharacterSheet
from sheet_reader import load_character_sheet
from episodes_db import init_db, search_episodes, format_citation

try:
    from document_utils import save_response_to_docx
except Exception:
    save_response_to_docx = None

def answer_as_character(sheet: CharacterSheet, question: str) -> str:
    """Responde en tono del personaje usando su ficha y citando episodios."""
    init_db()
    hits = search_episodes(question, limit=2)

    traits = ", ".join(sheet.personality_traits) if sheet.personality_traits else "—"
    catch = sheet.catchphrases[0] if sheet.catchphrases else ""

    reply = []
    if catch:
        reply.append(catch)  
    reply.append(f"Me preguntas: “{question}”.")
    reply.append(f"Yo soy {sheet.name}, suelo ser {traits}.")
    if hits:
        reply.append("Recuerdo algunos episodios relacionados:")
        for ep in hits:
            reply.append(f"- {format_citation(ep)}")
    else:
        reply.append("No recuerdo un episodio específico sobre eso...")
    reply.append("¡Miau!" if (not catch or catch.lower() == "miau") else catch)
    return "\n".join(reply)


def main():
    parser = argparse.ArgumentParser(description="Agente conversacional básico.")
    parser.add_argument(
        "path",
        nargs="?",
        default="./data/ficha/gary.yaml",
        help="Ruta al archivo .yaml/.json (p. ej. ./data/ficha/gary.yaml)"
    )
    parser.add_argument("--ask", help="Pregunta del usuario al personaje")
    parser.add_argument("--save-doc", action="store_true", help="Guardar la respuesta en .docx (requiere python-docx y document_utils.py)")
    parser.add_argument("--save-img", action="store_true", help="Generar imagen con la respuesta (requiere Pillow y image_utils.py)")
    args = parser.parse_args()

    raw = load_character_sheet(args.path)
    sheet = CharacterSheet(**raw)

    print("\n=== Persona prompt sugerido ===\n")
    print(sheet.persona_prompt())

    if args.ask:
        print("\n=== Respuesta en personaje ===\n")
        answer = answer_as_character(sheet, args.ask)  
        print(answer)

        if args.save_doc:
            if save_response_to_docx is None:
                print("\n[Aviso] Falta 'python-docx' o 'document_utils.py'. Instala con: pip install python-docx")
            else:
                path_doc = save_response_to_docx(sheet.name, args.ask, answer)
                print(f"\nRespuesta guardada en: {path_doc}")
    else:
        print("\n(Pista) Usa --ask \"tu pregunta\" para interactuar.")


if __name__ == "__main__":
    main()
