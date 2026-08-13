"""
ANVIQO VOICE INTERFACE
======================
Voice is only an interface layer.

VOICE -> SPEECH TO TEXT -> EXISTING /api/ask -> ANVI KNOWLEDGE/V5/COMMAND INTENT
       <- TEXT RESPONSE <- SAME ANVI PIPELINE
       -> OPTIONAL BROWSER TEXT TO SPEECH

No second reasoning engine.
No PLC/SCADA bypass.
"""

VOICE_CAPABILITIES = {
    "speech_to_text": True,
    "text_to_speech": True,
    "automatic_transcript": True,
    "same_anvi_orchestrator": True,
    "same_command_intent_layer": True,
    "plc_write": False,
    "scada_control": False,
    "execution_mode": "SIMULATION",
    "real_plc_write_enabled": False,
    "real_scada_control_enabled": False,
    "human_approval_required": True,
}


def voice_capabilities():
    return dict(VOICE_CAPABILITIES)


def voice_architecture():
    return {
        "input": "MICROPHONE",
        "speech_to_text": "BROWSER WEB SPEECH API",
        "reasoning": "EXISTING ANVI KNOWLEDGE/V5 PIPELINE",
        "command_intent": "EXISTING ANVI COMMAND INTENT LAYER",
        "safety": "ANVI CONTROL GATEWAY",
        "output": "TEXT + BROWSER TEXT TO SPEECH",
        "execution": "SIMULATION",
    }
