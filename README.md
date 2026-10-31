# Dell Precision M4800 · Sensor Gauges

Ein kleines Python-/Tkinter-Programm für Linux mit animierten Rundinstrumenten
für CPU-Taktfrequenzen, CPU-Temperaturen und Lüfterdrehzahlen. Entwickelt auf
Linux Mint 22.3 mit Xfce auf einem Dell Precision M4800.

## Funktionen

- Übersicht: höchster gemeldeter CPU-Takt und wärmster CPU-Sensor.
- Reiter für die Frequenz jeder logischen CPU, einzelne CPU-Temperaturen und Lüfter.
- Lüfterdrehzahlen in U/min, einschließlich gültiger Werte von 0 U/min.
- Sanfte Zeiger- und Bogenanimation über etwa 0,45 Sekunden.
- Sensorabfrage jede Sekunde im Hintergrund; verdeckte Instrumente werden nicht animiert.
- Vergrößerbares Fenster und Bildlaufleisten bei vielen Instrumenten.

Das Programm liest Sensoren ausschließlich aus und verändert keine Lüftersteuerung,
Taktraten oder Energieeinstellungen. Andere Linux-Rechner können ebenfalls
funktionieren; welche Werte erscheinen, hängt von Kernel und Hardware ab.

## Installation unter Linux Mint / Ubuntu

Benötigt werden Python 3, Tkinter und `lm-sensors`. `python3-venv` ermöglicht die
virtuelle Umgebung. Es sind keine zusätzlichen Python-Pakete aus PyPI erforderlich.
Tkinter wird über die Paketverwaltung installiert, nicht über pip.

```bash
sudo apt update
sudo apt install git python3 python3-tk python3-venv lm-sensors

mkdir -p ~/src/git-repos
cd ~/src/git-repos
git clone https://github.com/ciesinsk/DellPrecisionM4800-sensor-gauges.git
cd DellPrecisionM4800-sensor-gauges
python3 -m venv .venv
./start.sh
```

Ein grafischer Desktop ist erforderlich. Bei Fernzugriff beispielsweise innerhalb
einer Xfce-/XRDP-Sitzung starten.

## Später erneut starten

```bash
~/src/git-repos/DellPrecisionM4800-sensor-gauges/start.sh
```

Alternativ direkt mit dem Python-Interpreter der Umgebung:

```bash
.venv/bin/python cpu_monitor.py
```

Wenn bereits eine Umgebung unter `~/src/cpu-monitor-venv` existiert, kann sie ohne
weitere venv verwendet werden:

```bash
CPU_MONITOR_PYTHON="$HOME/src/cpu-monitor-venv/bin/python" ./start.sh
```

Nach Codeänderungen das Fenster schließen und neu starten.

## Messwerte und Grenzen

- **Takt:** Momentaufnahmen aus `/proc/cpuinfo` in MHz. Logische CPUs einschließlich
  Hyperthreading werden separat angezeigt. Es handelt sich nicht um über längere
  Zeit gemessene effektive Taktraten. Die Skala verwendet nach Möglichkeit
  `cpuinfo_max_freq` aus sysfs und passt sich höheren Messwerten an.
- **Temperaturen:** CPU-Sensoren aus `sensors -j`; ersatzweise passende
  `/sys/class/thermal`-Zonen. SSD-/GPU-Temperaturen werden nicht angezeigt.
  Gelb ab 75 °C, rot ab 90 °C: feste Anzeigegrenzen, keine prozessorspezifische
  Überhitzungsdiagnose.
- **Lüfter:** Alle von `sensors -j` gemeldeten `fan*_input`-Werte. Auf dem M4800
  wurden `Processor Fan` und `Video Fan` erkannt. Fehlende Messwerte werden
  nicht als 0 U/min ausgegeben. Die Skala berücksichtigt gemeldete Maximalwerte.
- Die Zahl zeigt immer den letzten Messwert. Zeiger und Bogen bewegen sich
  interpoliert dorthin; Zwischenpositionen sind keine zusätzlichen Messungen.

## Fehlersuche

**`No module named tkinter`:**

```bash
sudo apt install python3-tk
```

**`ensurepip is not available` beim Erstellen der venv:**

```bash
sudo apt install python3-venv
python3 -m venv .venv
```

Bei einer separat installierten Python-Version kann stattdessen das passende
Versionspaket nötig sein, beispielsweise `python3.12-venv`.

**Keine Temperatur- oder Lüfterwerte:**

```bash
sensors
sensors -j
```

Nur Sensoren, die Kernel und Treiber bereitstellen, können angezeigt werden.
Das Programm meldet nicht verfügbare Sensoren im jeweiligen Reiter.

**`no display name and no $DISPLAY environment variable`:**

Das Programm in einem Terminal der grafischen Sitzung starten, nicht in einer
reinen SSH-Sitzung ohne grafische Weiterleitung.

## Technischer Aufbau

`cpu_monitor.py` enthält Sensorabfrage und Oberfläche. Ein Hintergrundthread
liest die Daten; eine Queue übergibt sie an den Tk-Hauptthread. Pro Aktualisierung
wird `sensors -j` einmal mit einem Timeout von zwei Sekunden aufgerufen.
Die Animation verwendet Tk-Callbacks mit ungefähr 30 Bildern pro Sekunde und
endet nach Erreichen des Zielwerts.
