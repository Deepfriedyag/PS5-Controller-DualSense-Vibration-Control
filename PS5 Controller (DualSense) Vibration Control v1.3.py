import time
import threading
import itertools
import keyboard
import mouse
from pydualsense import pydualsense

ds = pydualsense()
ds.init()

# List of digital buttons to monitor (PlayStation controller)
digital_buttons = [
    'cross', 'circle', 'square', 'triangle',
    'dpadUp', 'dpadDown', 'dpadLeft', 'dpadRight',
    'R1', 'R2'
]

# Map programmable mouse buttons to PlayStation buttons
mouse_to_ps = {
    'x2': 'R2',
    'x': 'circle',
}

# Vibration patterns for face buttons
face_buttons = {
    'cross': [100, 0, 100, 0],
    'circle': [150, 150, 0, 0],
    'square': [255, 0, 255, 0, 50],
    'triangle': [0, 200, 0, 200]
}
pattern_threads = {}

# Track which buttons are held
button_held = {btn: False for btn in digital_buttons}
for ps_btn in mouse_to_ps.values():
    if ps_btn not in button_held:
        button_held[ps_btn] = False

# Vibration intensity (0–255)
vibration_intensity = 100
vibration_lock = threading.Lock()

def set_vibration(level):
    ds.setLeftMotor(level)
    ds.setRightMotor(level)

def play_pattern(button):
    pattern = itertools.cycle(face_buttons[button])
    while button_held.get(button, False):
        with vibration_lock:
            level = next(pattern)
            ds.setLeftMotor(level)
            ds.setRightMotor(level)
        time.sleep(0.1)
    set_vibration(0)

def vibration_loop():
    last_face_state = {btn: False for btn in face_buttons}
    while True:
        active_nonface = any(
            button_held[b] for b in digital_buttons if b not in face_buttons
        )
        active_face = any(button_held[b] for b in face_buttons)

        for btn in face_buttons:
            now = button_held[btn]
            was = last_face_state[btn]
            if now and not was:
                t = threading.Thread(target=play_pattern, args=(btn,))
                t.daemon = True
                pattern_threads[btn] = t
                t.start()
            last_face_state[btn] = now

        with vibration_lock:
            if active_nonface and not active_face:
                set_vibration(vibration_intensity)
            elif not active_nonface and not active_face:
                set_vibration(0)

        time.sleep(0.02)

def handle_key_event(event):
    global vibration_intensity
    if event.event_type != 'down':
        return
    name = event.name
    if name == '+':
        with vibration_lock:
            vibration_intensity = min(255, vibration_intensity + 5)
        print(f"Vibration intensity increased: {vibration_intensity}")
    elif name == '-':
        with vibration_lock:
            vibration_intensity = max(0, vibration_intensity - 5)
        print(f"Vibration intensity decreased: {vibration_intensity}")
    elif name == '*':
        print("Exiting...")
        set_vibration(0)
        ds.close()
        quit()

keyboard.hook(handle_key_event)

def handle_mouse_event(event):
    if hasattr(event, 'event_type') and event.event_type in ('down', 'up'):
        ps_btn = mouse_to_ps.get(event.button)
        if ps_btn:
            button_held[ps_btn] = event.event_type == 'down'

mouse.hook(handle_mouse_event)

def main_loop():
    try:
        while True:
            for btn in digital_buttons:
                if btn not in mouse_to_ps.values():  # Avoid overwriting mouse
                    current = getattr(ds.state, btn, False)
                    button_held[btn] = current
            time.sleep(0.01)
    except KeyboardInterrupt:
        print("Exiting...")
        set_vibration(0)
        ds.close()

# --- START THREADS ---
threading.Thread(target=vibration_loop, daemon=True).start()

print("Hold any controller or mapped mouse button to vibrate. Use '+' or '-' to adjust intensity. '*' to quit.")
main_loop()
