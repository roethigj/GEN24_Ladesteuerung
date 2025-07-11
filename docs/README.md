
## ☀️ GEN24_Ladesteuerung 🔋 
  
**Programmfunktionen:**  
- Prognosebasierte Ladesteuerung für  Fronius Symo GEN24 Plus um eine Einspeisebegrenzung (bei mir 70%) zu umgehen,
und eine Produktion über der AC-Ausgangsleistungsgrenze des WR als DC in die Batterie zu laden.  
Über die Tabelle [Ladesteuerung](https://github.com/wiggal/GEN24_Ladesteuerung/#batterieladesteuerung--tab---ladesteuerung-) können große, geplante Verbräuche bei der Ladeplanung berücksichtigt werden.  
- [Entladesteuerung,](https://github.com/wiggal/GEN24_Ladesteuerung/#batterieentladesteuerung--tab---entladesteuerung-) um die Entladung der Batterie bei großen Verbräuchen zu steuern.  
- [Logging](https://github.com/wiggal/GEN24_Ladesteuerung/#bar_chart-logging) und grafische Darstellung von Produktion und Verbrauch.  
- Akkuschonung: Um einen LFP-Akku zu schonen, wird die Ladeleistung ab 80% auf 0,2C und ab 90% auf 0,1C (optional ab 95% weniger) beschränkt (anpassbar).  
- [Dynamischen Strompreis](https://github.com/wiggal/GEN24_Ladesteuerung/#heavy_dollar_signelectric_plug-dynamicpricecheckpy) nutzen um bei niedrigen Preisen den Akku zu laden und grafische Darstellung.  
- **NEU:** [Grafana](https://github.com/wiggal/GEN24_Ladesteuerung/#grafana-beispiele) Beschreibung zu Auswertungen mit Grafana inklusive fertige Dashboards von [@Manniene](https://github.com/Manniene).  

![new](pics/new.png)  
Ab Version: **0.30.4**  
Neues Prognoseskripte OpenMeteo_WeatherData.py für https://open-meteo.com.  
Ab Version: **0.30.2**  
Konsolidierung der Dokumentation, Hilfen und [Wiki](https://wiggal.github.io/GEN24_Ladesteuerung/) nach GitHub/Pages übernommen.  
Ab Version: **0.30.0**  
Speicherung der Prognosedaten in `weatherData.sqlite`, Berechnung der Prognose mit gespeicherten Werten.  
Mit dem verlinkten  `ForecastMgr` können die Prognosedaten gesichtet und gelöscht werden.  
Ab Version: **0.29.0**  
Zur Akkuschonung kann der Akku bei entprechender Prognose auch nur bis 80% geladen werden.  
Vorbereitung des DynamicPriceCheck auf viertelstündliche Strompreise.  
![new](pics/new2.png)  

Die Ladung des Hausakkus erfolgt prognosebasiert und kann mit der Variablen „BatSparFaktor“ in der „CONFIG/charge_priv.ini“ gesteuert werden.  
Hier eine schematische Darstellung um die Auswirkung des „BatSparFaktor“ zu verdeutlichen:  
![Auswirkung des BatSparFaktor](pics/Ladewertverteilung.png)

## 💾 Installationshinweise: [siehe Wiki](https://wiggal.github.io/GEN24_Ladesteuerung/)

Folgende Installationen sind nötig, damit die Pythonskripte funktionieren  
```
sudo apt install python3
sudo apt install python3-pip
sudo pip install requests
```
Mit start_PythonScript.sh können Pythonskripte per Cronjobs oder auf der Shell gestartet werden, die Ausgabe erfolgt dann in die Datei "Crontab.log". 
Als Erstes muss ein Prognoseskript aufgerufen werden, damit aktuelle Prognosedaten in der DB weatherData.sqlite vorhanden sind!  

Beispiele für Crontabeinträge ("DIR" durch dein Installationsverzeichnis ersetzen).  
Ausführrechte für das start_PythonScript.sh Skript setzen nicht vergessen (chmod +x start_PythonScript.sh).  
http_SymoGen24Controller2.py durchgehend (wegen Logging) alle 10 Minuten starten  
(Häufigerer Aufruf für Logging nicht sinnvoll, da der Gen24 die Zähler nur alle 5 Minuten aktualisiert!).  
Da bei der HTTP-Methode der WR die Einspeisebegrenzung regelt, reicht hier auch ein Aufruf alle 10 Minuten (1-59/10).  

```
1-59/10 * * * * /DIR/start_PythonScript.sh http_SymoGen24Controller2.py schreiben
```
Es können nun alle Prognosen abgefragt werden, Speicherung in `weatherData.sqlite`.  
Die Berechnung der zu erwartenden PV-Produktion erfolgt als Median aus den Werten und Gewichten der DB.
```
33 5,8,10,12,14 * * * /DIR/start_PythonScript.sh FORECAST/Forecast_solar__WeatherData.py
8 5,7,9,11,13,15 * * * /DIR/start_PythonScript.sh FORECAST/Solarprognose_WeatherData.py
0 6,8,11,13,15 * * * /DIR/start_PythonScript.sh FORECAST/Solcast_WeatherData.py
0 5,7,9,11,13,15,17,19 * * * /DIR/start_PythonScript.sh FORECAST/Akkudoktor__WeatherData.py
35 5,7,9,11,13,15,17,19 * * * /home/GEN24/start_PythonScript.sh FORECAST/OpenMeteo_WeatherData.py
```
**Crontab.log jeden Montag abräumen**
```
0 0 * * 1 mv /DIR/Crontab.log /DIR/Crontab.log_weg
```

### 🌦️ Prognoseskripte in FORECAST/

Holen von den jeweiligen API-Urls die Prognosedaten und bereiten sie auf für GEN24_Ladesteuerung. 

Besonderheiten:  
- Bei forecast.solar kann mit einem Account die Prognose mit den Werten der Produktion aus der DB angepasst werden.  
- Bei solarprognose.de ist ein Account erforderlich, hier wird ein genauer Zeitpunkt für die Anforderung vorgegeben.  
- Bei solcast.com.au ist ein "Home User" Account erforderlich. Leider kann nur 10x am Tag angefordert werden.  
- Bei api.akkudoktor.net können Abschattungen und weitere Parameter angegeben werden.  
- Bei open-meteo.com können verschiedene Wetterdienste konfiguriert werden, kein Account nötig.  

### 📉 http_SymoGen24Controller2.py

Berechnet den aktuell besten Ladewert aufgrund der Prognosewerte in weatherData.json und dem Akkustand und gibt sie aus. 
Mit dem Parameter "schreiben" aufgerufen (start_PythonScript.sh http_SymoGen24Controller2.py **schreiben**) setzt es die `Maximale Ladeleistung` **per HTTP-Request** 
im Batteriemanagement des Wechselrichters. 
Die **Einspeisebegrenzung** und die **AC-Kapazität der Wechselrichters** muss hier nicht berücksichtigt werden,
da dies das Batteriemanagement des GEN24 selber regelt (auch über der definierten `Maximale Ladeleistung`!)

### 💲🔌 DynamicPriceCheck.py
Es werden die günstigsten Stunden zum Laden des Akkus aus dem Netz, bzw. eines Akku Entladestopps ermittelt (siehe schematische Darstellung). Der Aufruf von DynamicPriceCheck.py sollte einmal stündlich am besten zwei Minuten vor der vollen Stunde erfolgen.  
**Crontab Beispiel** (-o = alternatives Logfile):
```
58 * * * * /DIR/start_PythonScript.sh -o LOG_DynamicPriceCheck.log DynamicPriceCheck.py schreiben
```
Die Werte werden in die Tabelle EntladeSteuerung eingetragen, und beim nächsten Aufruf von http_SymoGen24Controller2.py auf den GEN24 geschrieben.  
Hier das Diagramm zu den dynamischen Strompreisen:
![Beispiel einer Zwangsladeberechnung](pics/Dyn_Strompreis.png)

## Webserver Installation (WebUI):  

**PHP installieren:**
```
sudo apt update && sudo apt upgrade
sudo apt install php php-sqlite3
```
Wenn PHP installiert ist, wird durch die Variable `Einfacher_PHP_Webserver = 1` (Standard) in der CONFIG/default_priv.ini beim nächsten Start von `start_PythonScript.sh`
automatisch der einfache PHP-Webserver gestartet werden. Die Webseite ist dann auf Port:2424 erreichbar (z.B.: raspberrypi:2424).  

**_Alternativ kann auch der Webserver Apache installiert werden:_**  
[siehe Wiki](https://wiggal.github.io/GEN24_Ladesteuerung/)

### 📊 Logging

Beim Aufruf von `http_SymoGen24Controller2.py schreiben` wird die Ladesteuerung und das Logging ausgeführt.  
Beim Aufruf mit dem Parameter `logging` wird nur das Logging ausgeführt, es erfolgt keine Ladesteuerung.  
Aus der SQLite-Datei `PV_Daten.sqlite` wird dann mit html/8_tab_Diagram.php ein Diagramm nach Quelle (wo kommt die Energie her) und Ziel (wo geht die Energie hin) erzeugt. 
![Grafik zur Quelle/Ziel](pics/QZ_Tag.png)

### Modul zur Reservierung von größeren Mengen PV-Leistung, manuelle Ladesteuerung bzw. Entladesteuerung (z.B. E-Autos)

### Batterieladesteuerung ( TAB--> LadeStrg )
![Tabelle zur Ladesteuerung](pics/Ladesteuerung.png)

Alle eingetragenen Reservierungen werden in die DB-Datei CONFIG/Prog_Steuerung.sqlite geschrieben.  

Ist **AUTO** eingestellt, wird die Reservierung von http_SymoGen24Controller2.py in der Ladeberechnung berücksichtigt.

Bei Einstellung **Slider**, wird mit der eingestellten Prozentzahl der **maximalen Ladeleistung des GEN24**,  
bei **MaxLadung** mit der in CONFIG/charge_priv.ini unter MaxLadung definierten Ladeleistung,  
ab dem nächsten Aufruf von http_SymoGen24Controller2.py geladen.  
Beim Speichern werden nach Auswahl von **Slider** oder **MaxLadung** Gültigkeitsstunden abgefragt, nach deren Ablauf wird wieder Auto angewendet.  

### ForecastMgr
Im ForecastMgr können die gespeicherten Prognosedaten analysiert, und evtl. gelöscht werden. Sie werden grafisch und als Tabelle dargestellt.   
![ForecastMgr](pics/ForecastMgr.png)

Weitere Erklärungen stehen in der verlinkten Hilfe oder im [Wiki](https://wiggal.github.io/GEN24_Ladesteuerung/).  

### BatterieENTladesteuerung ( TAB--> ENTLadeStrg )
![Tabelle zur Entladesteuerung](pics/Entladesteuerung.png)

Unter "Feste Entladegrenze" kann die maximale Entladeleistung in Prozent der WR-Entladeleistung fest eingestellt werden.

In der Entladetabelle können Leistungen in kW zur Steuerung der Akkuentladung, bzw. zum Laden des Akkus aus dem Netz bei niedrigen Strompreisen, eingetragen werden. 
Durch einen negativen Wert in "Feste Entladegrenze" erfolgt die Zwangsladung des Akkus.

Weitere Erklärungen stehen in der verlinkten Hilfe oder im [Wiki](https://wiggal.github.io/GEN24_Ladesteuerung/).  

### Settings ( TAB--> Settings )
![Tabelle zu den Settings](pics/Settings.png)
Programmfunktionen
Unter Settings kann das Programm zusätzlich gesteuert werden.  

Weitere Erklärungen stehen in der verlinkten Hilfe oder im [Wiki](https://wiggal.github.io/GEN24_Ladesteuerung/).    

### Grafana Beispiele  
![Beispiele](pics/Grafana.png)

Eine [Beschreibung](../GRAFANA/Grafana_Installation_readme.pdf) und Dashboarddateien liegen im Verzeichnis GRAFANA.

----------

**News History:**  
Ab Version: **0.28.1**  
Neues Prognoseskripte Akkudoktor__WeatherData.py für https://api.akkudoktor.net/ von @tz8  
**ACHTUNG:** Umfangreiche Änderungen in CONFIG/weather_priv.ini nötig!!  
Ab Version: **0.28.0**  
**ACHTUNG:** Die Prognoseskripte wurden ins Verzeichnis FORECAST verschoben.  
**Cronjobs müssen angepasst werden!!** (siehe Cortabeinträge Wetterdienste).  
Ab Version: **0.26.9**  
Diagramm zur Darstellung der dynamischen Strompreise.  
Ab Version: **0.26.8**  
Beschreibung zu Auswertungen mit Grafana inklusive fertige Dashboards von @Manniene  
Ab Version: **0.26.1**  
Dynamischer Strompreis: Akku laden bei günstigen Strompreisen in Tabelle ENTLadeStrg eintragen durch DynamicPriceCheck.py.  
Ab Version: **0.25.1**  
Prognosebegrenzung auf Höchstwerte der historischen Produktion.  
Ab Version: **0.25.0**  
Zwangsladung durch Eintragen von negativen kW in die Tabelle ENTLadeStrg  
