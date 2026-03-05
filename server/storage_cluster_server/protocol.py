#Aqui haremos los procesamientos de mensajes JSON

import json

def parse_message(raw_data):
    try:
        return json.loads(raw_data)
    except json.JSONDecodeError:
        return None