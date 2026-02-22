
import mido
import os


def events_to_midi(
    events: list[dict],
    output_path: str,
    tempo: int = 480000,        # BPM ~125
    ticks_per_beat: int = 480,
) -> str:
    """
    Escribe un archivo MIDI a partir de los eventos registrados por el servidor.

    Parámetros
    ----------
    events       : lista de dicts con al menos la clave 'midi_value'
    output_path  : ruta destino del archivo .mid
    tempo        : microsegundos por pulso (500000 = 120 BPM)
    ticks_per_beat: resolución MIDI

    Retorna la ruta del archivo generado.
    """
    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
    # Piano acústico de cola (General MIDI program 0)
    track.append(mido.Message("program_change", program=0, time=0))

    note_duration = ticks_per_beat // 4  # semicorchea

    for event in events:
        midi_val = int(event["midi_value"])
        note = int(midi_val * 0.5 + 36)          # mapeo [0-127] → [36-99]
        velocity = max(40, min(127, midi_val + 30))  # mínimo de volumen audible

        track.append(mido.Message("note_on",  note=note, velocity=velocity, time=0))
        track.append(mido.Message("note_off", note=note, velocity=0, time=note_duration))

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    mid.save(output_path)
    return output_path
