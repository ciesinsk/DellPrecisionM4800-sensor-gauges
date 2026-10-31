#!/usr/bin/env python3
"""CPU-Instrumente für Linux. Benötigt python3-tk und optional lm-sensors."""
import json
import math
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk

BG = '#17212e'
PANEL = '#202e40'
TEXT = '#edf3fb'
MUTED = '#a7b8cc'
GREEN = '#52d6ad'


def frequencies():
    """Logische CPUs und momentane, vom Kernel gemeldete MHz."""
    result = {}
    cpu = None
    for line in Path('/proc/cpuinfo').read_text().splitlines():
        key, _, value = line.partition(':')
        if key.strip() == 'processor':
            cpu = value.strip()
        elif key.strip() == 'cpu MHz' and cpu is not None:
            result[f'CPU {cpu}'] = float(value)
    return result


def maximum_frequency():
    values = []
    for path in Path('/sys/devices/system/cpu').glob('cpu[0-9]*/cpufreq/cpuinfo_max_freq'):
        try:
            values.append(float(path.read_text()) / 1000)
        except (OSError, ValueError):
            pass
    return max(values, default=4000)


def read_sensors():
    """Eine gemeinsame Sensorabfrage pro Aktualisierung."""
    try:
        process = subprocess.run(['sensors', '-j'], capture_output=True, text=True,
                                 timeout=2, check=False)
        data = json.loads(process.stdout)
        return data if isinstance(data, dict) else {}
    except (OSError, subprocess.SubprocessError, ValueError):
        return {}


def fan_speeds(data=None):
    """Gemeldete Lüfterdrehzahlen; 0 U/min ist ein gültiger Wert."""
    data = read_sensors() if data is None else data
    values = {}
    maximum = 5000
    for chip, features in data.items():
        if not isinstance(features, dict):
            continue
        for label, entries in features.items():
            if not isinstance(entries, dict):
                continue
            for key, value in entries.items():
                if re.fullmatch(r'fan\d+_input', key) and isinstance(value, (int, float)):
                    if not math.isfinite(value) or value < 0:
                        continue
                    values[f'{label} · {chip}'] = float(value)
                    maximum = max(maximum, value)
                    limit = entries.get(key.replace('_input', '_max'))
                    if isinstance(limit, (int, float)) and math.isfinite(limit):
                        maximum = max(maximum, limit)
    return values, math.ceil(maximum / 1000) * 1000


def temperatures(data=None):
    """Nur CPU-Sensoren, keine SSD-/GPU-Temperaturen."""
    result = {}
    data = read_sensors() if data is None else data
    try:
        for chip, features in data.items():
            if not isinstance(features, dict):
                continue
            cpu_chip = any(name in chip.lower() for name in ('coretemp', 'k10temp', 'zenpower', 'cpu_thermal'))
            for label, entries in features.items():
                if not isinstance(entries, dict):
                    continue
                cpu_label = re.search(r'\b(cpu|package|core\s*\d|tctl|tdie)\b', label, re.I)
                if not (cpu_chip or cpu_label):
                    continue
                for key, value in entries.items():
                    if re.fullmatch(r'temp\d+_input', key) and isinstance(value, (float, int)):
                        result[f'{label} · {chip}'] = float(value)
    except (FileNotFoundError, subprocess.SubprocessError, ValueError):
        pass
    if not result:
        for zone in Path('/sys/class/thermal').glob('thermal_zone*'):
            try:
                label = (zone / 'type').read_text().strip()
                if any(name in label.lower() for name in ('cpu', 'x86_pkg', 'soc_thermal')):
                    result[f'{label} · {zone.name}'] = float((zone / 'temp').read_text()) / 1000
            except (OSError, ValueError):
                pass
    return result


class Gauge(tk.Canvas):
    def __init__(self, parent, title, unit, maximum=100, temperature=False):
        super().__init__(parent, width=230, height=190, bg=PANEL,
                         highlightthickness=0)
        self.title, self.unit = title, unit
        self.maximum, self.temperature = maximum, temperature
        self.value = None
        self.reading = None
        self.animation = None
        self.duration = 0.45
        self.bind('<Configure>', lambda event: self.draw())

    def stop_animation(self):
        if self.animation is not None:
            self.after_cancel(self.animation)
            self.animation = None

    def update_value(self, value, maximum=None):
        self.stop_animation()
        target_maximum = maximum if maximum is not None else self.maximum
        self.reading = value
        # Verdeckte Reiter und minimierte Fenster brauchen keine Animation.
        if value is None or self.value is None or not self.winfo_viewable():
            self.value, self.maximum = value, target_maximum
            self.draw()
            return
        if self.value == value and self.maximum == target_maximum:
            self.draw()
            return
        self.start_value, self.target_value = self.value, value
        self.start_maximum, self.target_maximum = self.maximum, target_maximum
        self.started = time.monotonic()
        self.animate()

    def animate(self):
        self.animation = None
        progress = min(1.0, (time.monotonic() - self.started) / self.duration)
        if not self.winfo_viewable():
            progress = 1.0
        # Smoothstep: sanftes Beschleunigen und Abbremsen ohne Überschwingen.
        eased = progress * progress * (3 - 2 * progress)
        self.value = self.start_value + (self.target_value - self.start_value) * eased
        self.maximum = self.start_maximum + (self.target_maximum - self.start_maximum) * eased
        if progress >= 1:
            self.value, self.maximum = self.target_value, self.target_maximum
        self.draw()
        if progress < 1:
            self.animation = self.after(33, self.animate)

    def destroy(self):
        self.stop_animation()
        super().destroy()

    def draw(self):
        self.delete('all')
        w, h = max(self.winfo_width(), 230), max(self.winfo_height(), 190)
        cx, cy, radius = w / 2, h * .61, min(w * .37, h * .43)
        box = (cx-radius, cy-radius, cx+radius, cy+radius)
        color = GREEN
        if self.temperature and self.value is not None:
            color = '#ff707c' if self.value >= 90 else '#ffc46b' if self.value >= 75 else GREEN
        self.create_arc(*box, start=225, extent=-270, style='arc', width=13, outline='#34465c')
        ratio = 0 if self.value is None else max(0, min(1, self.value/self.maximum))
        if ratio:
            self.create_arc(*box, start=225, extent=-270*ratio, style='arc', width=13, outline=color)
        for step in range(5):
            angle = math.radians(225 - step*67.5)
            x, y = cx+radius*math.cos(angle), cy-radius*math.sin(angle)
            self.create_line(x, y, cx+(radius-10)*math.cos(angle),
                             cy-(radius-10)*math.sin(angle), fill=TEXT, width=2)
        if self.value is not None:
            angle = math.radians(225-ratio*270)
            self.create_line(cx, cy, cx+radius*.64*math.cos(angle),
                             cy-radius*.64*math.sin(angle), fill=TEXT, width=3)
            self.create_oval(cx-4, cy-4, cx+4, cy+4, fill=TEXT, outline='')
        self.create_text(cx, 17, text=self.title, fill=TEXT, font=('Sans', 11, 'bold'), width=w-16)
        self.create_text(cx, cy+28, text='—' if self.reading is None else (f'{self.reading:.0f} {self.unit}' if self.unit == 'U/min' else f'{self.reading:.1f} {self.unit}'),
                         fill=color, font=('Sans', 15, 'bold'))
        self.create_text(cx, h-12, text=f'0 – {self.maximum:.0f} {self.unit}', fill=MUTED, font=('Sans', 9))


class GaugePage:
    def __init__(self, notebook, title, unit, temperature=False, empty_message=None):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        self.canvas = tk.Canvas(frame, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self.window = self.canvas.create_window(0, 0, anchor='nw', window=self.inner)
        self.inner.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', self.resize)
        self.empty_message = empty_message
        self.gauges = {}
        self.unit, self.temperature = unit, temperature
        self.columns = 3
        self.message = tk.Label(self.inner, bg=BG, fg=MUTED, wraplength=500, pady=30)

    def resize(self, event):
        self.canvas.itemconfigure(self.window, width=event.width)
        self.columns = max(1, event.width // 245)
        self.layout()

    def layout(self):
        for column in range(32):
            self.inner.grid_columnconfigure(column, weight=0)
        for i, gauge in enumerate(self.gauges.values()):
            gauge.grid(row=i//self.columns, column=i % self.columns, padx=7, pady=7, sticky='ew')
        for column in range(self.columns):
            self.inner.grid_columnconfigure(column, weight=1)

    def update(self, values, maximum):
        for key in list(self.gauges):
            if key not in values:
                self.gauges.pop(key).destroy()
        for key, value in values.items():
            if key not in self.gauges:
                self.gauges[key] = Gauge(self.inner, key, self.unit, maximum, self.temperature)
            self.gauges[key].update_value(value, maximum)
        self.message.grid_forget()
        if not values:
            self.message.configure(text=self.empty_message or (
                'Keine CPU-Temperatursensoren verfügbar.\nBei Bedarf: sudo apt install lm-sensors'
                if self.temperature else 'Keine CPU-Taktwerte in /proc/cpuinfo verfügbar.'))
            self.message.grid(row=0, column=0, columnspan=self.columns, sticky='ew')
        self.layout()


class Monitor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('CPU Monitor · Takt, Temperatur & Lüfter')
        self.geometry('800x720')
        self.minsize(530, 510)
        self.configure(bg=BG)
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('TFrame', background=BG)
        style.configure('TNotebook', background=BG, borderwidth=0)
        style.configure('TNotebook.Tab', background=PANEL, foreground=TEXT, padding=(15, 8))
        style.map('TNotebook.Tab', background=[('selected', '#34465c')])
        tk.Label(self, text='CPU MONITOR', bg=BG, fg=TEXT, font=('Sans', 19, 'bold')).pack(pady=(18, 3))
        tk.Label(self, text='Live-Werte · Aktualisierung jede Sekunde', bg=BG, fg=MUTED).pack()
        summary = tk.Frame(self, bg=BG)
        summary.pack(fill='x', padx=15, pady=12)
        self.clock = Gauge(summary, 'Höchster gemeldeter Takt', 'MHz', maximum_frequency())
        self.heat = Gauge(summary, 'Wärmster CPU-Sensor', '°C', 110, True)
        self.clock.pack(side='left', fill='x', expand=True, padx=5)
        self.heat.pack(side='left', fill='x', expand=True, padx=5)
        notebook = ttk.Notebook(self)
        notebook.pack(fill='both', expand=True, padx=15)
        self.cpus = GaugePage(notebook, 'Takt je logischer CPU', 'MHz')
        self.temps = GaugePage(notebook, 'CPU-Temperaturen', '°C', True)
        self.fans = GaugePage(notebook, 'Lüfter', 'U/min',
            empty_message='Keine Lüfterdrehzahlen verfügbar.\nNicht jede Hardware meldet Lüftersensoren.')
        self.status = tk.Label(self, text='Lese Sensoren …', bg=BG, fg=MUTED, pady=10)
        self.status.pack()
        self.mailbox = queue.Queue()
        self.stopping = threading.Event()
        self.maximum = maximum_frequency()
        self.protocol('WM_DELETE_WINDOW', self.close)
        threading.Thread(target=self.collect, daemon=True).start()
        self.after(100, self.poll)

    def collect(self):
        while not self.stopping.is_set():
            try:
                data = read_sensors()
                fans, fan_maximum = fan_speeds(data)
                self.mailbox.put((frequencies(), temperatures(data), fans, fan_maximum, None))
            except (OSError, ValueError) as error:
                self.mailbox.put(({}, {}, {}, 5000, str(error)))
            self.stopping.wait(1)

    def poll(self):
        latest = None
        while True:
            try:
                latest = self.mailbox.get_nowait()
            except queue.Empty:
                break
        if latest is not None:
            cpus, temps, fans, fan_maximum, error = latest
            self.maximum = max(self.maximum, max(cpus.values(), default=0))
            scale = math.ceil(self.maximum/500)*500
            self.clock.update_value(max(cpus.values()) if cpus else None, scale)
            self.heat.update_value(max(temps.values()) if temps else None, max(110, math.ceil(max(temps.values(), default=0)/10)*10))
            self.cpus.update(cpus, scale)
            self.temps.update(temps, max(110, math.ceil(max(temps.values(), default=0)/10)*10))
            self.fans.update(fans, fan_maximum)
            self.status.configure(text=f'Lesefehler: {error}' if error else f'{len(cpus)} logische CPUs · {len(temps)} CPU-Temperatursensoren · {len(fans)} Lüfter')
        self.after(100, self.poll)

    def close(self):
        self.stopping.set()
        self.destroy()


if __name__ == '__main__':
    Monitor().mainloop()
