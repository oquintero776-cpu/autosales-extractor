"""
AUTO SALES — Extractor de datos de vehículos
=============================================
Este script recibe el texto libre de un mensaje de WhatsApp
de un autolote y devuelve los datos estructurados en JSON.

USO EN MAKE:
  Make hace un HTTP POST a este endpoint con el texto del mensaje.
  El script lo procesa con Claude y devuelve JSON limpio.

DEPLOY:
  Sube este archivo a Render.com (gratuito) como un Web Service de Python.
  Render te da una URL pública automáticamente.

REQUISITOS:
  pip install anthropic flask
"""

import os
import json
import re
from flask import Flask, request, jsonify
from anthropic import Anthropic

app = Flask(__name__)
client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

PROMPT_SISTEMA = """
Eres un extractor de datos de vehículos para Auto Sales, un negocio de reventa de autos en Honduras.

Tu única función es recibir un texto libre que un autolote envió por WhatsApp describiendo un vehículo, 
y extraer los datos en un formato JSON estructurado.

REGLAS IMPORTANTES:
- Si un dato no aparece en el texto, ponlo como null (no inventes datos)
- El precio debe ser solo un número sin signos ni letras (ej: 350000, no "L.350,000")
- El kilometraje debe ser solo un número (ej: 45000)
- El año debe ser un número de 4 dígitos
- La condición es "Nueva" o "Usada" — si no lo dice explícitamente pero menciona año actual o "0km", es Nueva
- Las características van como una lista separada por comas
- El color puede estar descrito de diferentes formas: "negro", "blanco perla", "azul marino" etc.

FORMATO DE RESPUESTA (solo JSON, nada más):
{
  "marca": "string",
  "modelo": "string", 
  "anio": number,
  "color": "string",
  "precio": number,
  "kilometraje": number,
  "condicion": "Nueva" o "Usada",
  "caracteristicas": "string separado por comas",
  "notas_adicionales": "cualquier otra info relevante que no encaje en los campos anteriores"
}

IMPORTANTE: Responde SOLO con el JSON. Sin explicaciones, sin texto adicional, sin bloques de código.
"""


@app.route("/extraer", methods=["POST"])
def extraer_datos():
    """
    Endpoint principal que Make llama.
    
    Espera un POST con JSON:
    {
        "texto_mensaje": "texto del mensaje del autolote",
        "numero_autolote": "+504XXXXXXXX"  (opcional)
    }
    
    Devuelve:
    {
        "exito": true/false,
        "datos": { ...datos extraídos... },
        "numero_autolote_original": "numero limpio",
        "error": "mensaje de error si falló"
    }
    """
    try:
        body = request.get_json()
        texto = body.get("texto_mensaje", "")
        numero_autolote = body.get("numero_autolote", "")

        if not texto:
            return jsonify({"exito": False, "error": "No se envió texto del mensaje"}), 400

        # ─── Llamar a Claude para extraer datos ───
        respuesta = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=500,
            system=PROMPT_SISTEMA,
            messages=[
                {
                    "role": "user",
                    "content": f"Extrae los datos de este mensaje del autolote:\n\n{texto}"
                }
            ],
        )

        texto_respuesta = respuesta.content[0].text.strip()

        # Limpiar posibles bloques de código markdown
        texto_respuesta = re.sub(r"```json\s*", "", texto_respuesta)
        texto_respuesta = re.sub(r"```\s*", "", texto_respuesta)
        texto_respuesta = texto_respuesta.strip()

        datos = json.loads(texto_respuesta)

        # Limpiar número de autolote
        numero_limpio = re.sub(r"[\s\-\(\)\+]", "", numero_autolote) if numero_autolote else None

        return jsonify({
            "exito": True,
            "datos": datos,
            "numero_autolote_original": numero_limpio,
        })

    except json.JSONDecodeError:
        return jsonify({
            "exito": False,
            "error": "La IA no devolvió JSON válido",
            "respuesta_cruda": texto_respuesta,
        }), 500
    except Exception as e:
        return jsonify({"exito": False, "error": str(e)}), 500


@app.route("/salud", methods=["GET"])
def salud():
    """Endpoint para verificar que el server está funcionando."""
    return jsonify({"estado": "activo", "mensaje": "Auto Sales Extractor listo"})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
