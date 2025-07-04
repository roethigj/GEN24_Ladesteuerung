# Funktionen für die Gen24_Ladesteuerung
from datetime import datetime, timedelta
import os
import json
import configparser
import sqlite3
from collections import defaultdict
import FUNCTIONS.functions

basics = FUNCTIONS.functions.basics()
    
class WeatherData:
    def __init__(self):
        self.now = datetime.now()

    def check_or_create_db(self, path):
        # Prüfen, ob Datei existiert und ob sie leer ist
        if not os.path.exists(path) or os.path.getsize(path) == 0:
            print("DB existiert nicht oder ist leer. Wird neu erstellt.")
            return self.create_database(path)

        # Prüfen, ob Datei eine gültige SQLite-DB ist
        try:
            with sqlite3.connect(path) as conn:
                conn.execute("SELECT name FROM sqlite_master LIMIT 1;")
        except sqlite3.DatabaseError:
            print("DB beschädigt oder ungültig. Neu erstellen.")
            os.remove(path)
            create_database(path)

    def create_database(self, path):
        with sqlite3.connect(path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS weatherData (
                    Zeitpunkt TEXT,
                    Quelle TEXT,
                    Prognose_W INTEGER,
                    Gewicht INTEGER,
                    Options TEXT,
                    UNIQUE(Zeitpunkt, Quelle)
                );
            """)
        print("DB wurde erstellt.")


    def storeWeatherData_SQL(self, data, quelle, gewicht_neu=-1):
        self.check_or_create_db('weatherData.sqlite')
        verbindung = sqlite3.connect('weatherData.sqlite')
        zeiger = verbindung.cursor()
        print_level = basics.getVarConf('env','print_level','eval')
        # Alte Einträge löschen die älter 30 Tage sind
        loesche_bis = (datetime.today() - timedelta(days=30)).date().isoformat()

        #Prognosen kleiner 10 löschen
        data = [entry for entry in data if entry[2] >= 10]

        try:
            # Index auf Zeitpunkt anlegen, falls nicht vorhanden
            zeiger.execute("""
                CREATE INDEX IF NOT EXISTS idx_weatherData_Zeitpunkt ON weatherData(Zeitpunkt);
            """)
        
            # Alte Daten löschen
            zeiger.execute("""
                DELETE FROM weatherData
                WHERE datetime(Zeitpunkt) < datetime(?);
            """, (loesche_bis,))
        
            # Datensätze mit Quelle = 'Ergebnis' löschen, Historisch
            zeiger.execute("""
                DELETE FROM weatherData
                WHERE Quelle = 'Ergebnis';
            """)

            # Neue Prognosen speichern
            zeiger.executemany("""
            INSERT OR REPLACE INTO weatherData (Zeitpunkt, Quelle, Prognose_W, Gewicht, Options)
            VALUES (?, ?, ?, ?, ?);
            """, data)

        except Exception as e:
            print("Fehler:", e)
            import traceback
            traceback.print_exc()
            print("ERROR :", self.now, "Die Prognosedaten von ", quelle, "konnten NICHT gespeichert werden!")
            exit(0)

        # Hier noch prüfen ob sich das gewicht_neu geändert hat und evtl. in DB ändern
        # Aber nur wenn gewicht_neu nicht -1, da ses sonst nicht von einem Wetterdienst kommt
        if (gewicht_neu != -1):
            if print_level >= 3:
                print("DEBUG Gewichte überprüft für ", quelle)
            zeiger.execute("""
                UPDATE weatherData
                SET Gewicht = ?
                WHERE Quelle = ? AND Gewicht != ?
            """, (gewicht_neu, quelle, gewicht_neu))
        else:
            if print_level >= 3:
                print("DEBUG Gewichte !!NICHT!! überprüft für ", quelle)

        verbindung.commit()
        verbindung.close()

        return()
    
    def get_produktion_result(self, von_tag):
        conn = sqlite3.connect('PV_Daten.sqlite')
        verbindung = conn.cursor()
        heute = datetime.now().strftime('%Y-%m-%d 23:59:59')
        aktuelle_Std = datetime.now().strftime('%Y-%m-%d %H:00:00')
        Max_Leistung = basics.getVarConf('pv.strings','wp','eval')
        # Der offset soll die Stunde in die Mitte der Produktion verschieben
        offset = '+30 minutes'
        sql_anweisung = f"""
        WITH VerschobenePVDaten AS (
            SELECT
                datetime(Zeitpunkt, '{offset}') AS verschobenerZeitpunkt,
                DC_Produktion
            FROM pv_daten
            WHERE Zeitpunkt BETWEEN '{von_tag}' AND '{heute}'
        ),
        Alle_PVDaten AS (
            SELECT verschobenerZeitpunkt AS Zeitpunkt,
                DC_Produktion
            FROM VerschobenePVDaten
            GROUP BY STRFTIME('%Y%m%d%H', Zeitpunkt)
        ),
        ProduktionDiff AS (
            SELECT
                STRFTIME('%Y-%m-%d %H:00:00', Zeitpunkt) AS Zeitpunkt,
                (LEAD(DC_Produktion) OVER (ORDER BY Zeitpunkt) - DC_Produktion) AS Produktion
            FROM Alle_PVDaten
        )
        SELECT *
        FROM ProduktionDiff
        WHERE Produktion IS NOT NULL;
        """
        try:
            verbindung.execute(sql_anweisung)
            DB_data = verbindung.fetchall()
        except Exception as e:
            print("Fehler:", e)
            import traceback
            traceback.print_exc()
            print("Die Datei PV_Daten.sqlite fehlt oder ist leer!")
            DB_data = []
            DB_data.append((aktuelle_Std, 0),)
            # Schließe die Verbindung
            verbindung.close()

        Produktion = [] 
        Watt_zuvor = None
        for Stunde, Watt in DB_data:
            # Wenn Aufzeichnung länger ausgefallen ist, entstehen sonst grosse Produktionen
            if (Watt > Max_Leistung * 1.1 and Watt_zuvor != None):
                Watt = Watt_zuvor
            else:
                Watt_zuvor = Watt
            Produktion.extend([(Stunde, 'Produktion', Watt, '0', '')])

        return(Produktion)

    def get_Std_Watt_Faktor(self):
        conn = sqlite3.connect('weatherData.sqlite')
        cursor = conn.cursor()
        query = f"""
        WITH median_raw AS (
        SELECT
            strftime('%H:00', Zeitpunkt) AS stunde,
            Zeitpunkt,
            Prognose_W AS median
        FROM weatherData
        WHERE Quelle = 'Median'
        ),
        produktion_raw AS (
        SELECT
            strftime('%H:00', Zeitpunkt) AS stunde,
            Zeitpunkt,
            Prognose_W AS produktion
        FROM weatherData
        WHERE Quelle = 'Produktion'
        ),
        joined AS (
        SELECT
            m.stunde,
            m.Zeitpunkt,
            m.median,
            p.produktion
        FROM median_raw m
        JOIN produktion_raw p ON m.Zeitpunkt = p.Zeitpunkt
        WHERE m.median > 50
        ),
        max_median AS (
        SELECT
            stunde,
            MAX(median) AS max_median,
            MAX(median) / 1.0 AS drittel
        FROM joined
        GROUP BY stunde
        ),
        mit_bereich AS (
        SELECT
            j.stunde,
            j.Zeitpunkt,
            j.median,
            j.produktion,
            CASE
            WHEN j.median <= m.drittel THEN 1
            WHEN j.median <= 2 * m.drittel THEN 2
            ELSE 3
            END AS bereich,
            m.drittel,
            m.max_median,
            (j.produktion * 1.0 / j.median) AS faktor
        FROM joined j
        JOIN max_median m ON j.stunde = m.stunde
        WHERE m.max_median > 100
        ),
        alle_faktoren AS (
        SELECT
            CAST(substr(stunde, 1, 2) AS INTEGER) AS stunden_nr,
            bereich,
            faktor
        FROM mit_bereich
        ),
        gruppiert_mit_nachbarn AS (
        SELECT
            a1.stunden_nr,
            a1.bereich,
            a2.faktor
        FROM alle_faktoren a1
        JOIN alle_faktoren a2
            ON a1.bereich = a2.bereich
        AND a2.stunden_nr BETWEEN a1.stunden_nr - 1 AND a1.stunden_nr + 1
        ),
        gerankt AS (
        SELECT
            stunden_nr,
            bereich,
            faktor,
            ROW_NUMBER() OVER (PARTITION BY stunden_nr, bereich ORDER BY faktor) AS rn,
            COUNT(*) OVER (PARTITION BY stunden_nr, bereich) AS cnt
        FROM gruppiert_mit_nachbarn
        ),
        mediane AS (
        SELECT
            stunden_nr,
            bereich,
            CASE
            WHEN cnt < 3 THEN 1
            ELSE ROUND(AVG(faktor), 3)
            END AS median_faktor
        FROM gerankt
        WHERE rn IN ((cnt + 1) / 2, (cnt + 2) / 2)
        GROUP BY stunden_nr, bereich
        )
        SELECT
        printf('%02d:00', m.stunden_nr) AS stunde,
        m.bereich,
        ROUND(mx.drittel * (m.bereich - 1), 0) AS von_W,
        ROUND(mx.drittel * m.bereich, 0) AS bis_W,
        m.median_faktor
        FROM mediane m
        JOIN max_median mx ON printf('%02d:00', m.stunden_nr) = mx.stunde
        ORDER BY stunde, bereich
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        return(rows)

    def store_forecast_result(self):
        from collections import defaultdict
        from statistics import median, mean
        print_level = basics.getVarConf('env','print_level','eval')
        ForecastCalcMethod = basics.getVarConf('env','ForecastCalcMethod','str')
        conn = sqlite3.connect('weatherData.sqlite')
        cursor = conn.cursor()
    
        # 'Prognose', 'Median', 'Produktion' ausschließen, da sie nicht zur Mittelbildung verwendet werden
        query = f"""
            SELECT Zeitpunkt, Prognose_W, Gewicht
            FROM weatherData
            WHERE
                Prognose_W IS NOT NULL AND
                Gewicht > 0 AND
                Quelle NOT IN ('Prognose', 'Median', 'Produktion')
            ORDER BY Zeitpunkt ASC
        """
        cursor.execute(query)
        rows = cursor.fetchall()

        stundenwerte = defaultdict(list)
        akt_Std = self.now.strftime("%H:00:00")
        akt_tag_Std = self.now.strftime("%Y-%m-%d %H:00:00")
        von_tag = '2222-01-01'

        # Für jede Stunde und ein Prognosedrittel Faktor Produktion/prognose holen
        if ( ForecastCalcMethod == 'median_opt'):
            Prog_Faktoren = self.get_Std_Watt_Faktor()
            faktoren_dict = {}
            for stunde, bereich, watt_von, watt_bis, faktor in Prog_Faktoren:
                if stunde not in faktoren_dict:
                    faktoren_dict[stunde] = {}
                faktoren_dict[stunde][(watt_von, watt_bis)] = faktor
            # Ergebnis
            if print_level >= 3:
                print("DEBUG Faktoren und Bereiche je Stunde: ", faktoren_dict)

        for zeit_str, wert, gewicht in rows:
            zeit = datetime.fromisoformat(zeit_str)
            akt_tag = zeit.strftime("%Y-%m-%d")
            if akt_tag < von_tag: von_tag = akt_tag
            stunde = zeit.replace(minute=0, second=0, microsecond=0)
            # extend([wert] * gewicht) fügt den wert genau gewicht-mal der Liste hinzu
            # Damit hat man einen gewichteten Median
            if (wert > 10):
                try:
                    gewicht = int(gewicht)
                except (ValueError, TypeError):
                    gewicht = 0
                stundenwerte[stunde].extend([wert] * gewicht)

        result = {}
        result_median = {}
        for stunde in sorted(stundenwerte):
            if stundenwerte.get(stunde):
                zeit_str = stunde.strftime("%Y-%m-%d %H:%M:%S")
                # Median immer speichern, wegen Medianoptimierung
                result_median[zeit_str] = int(median(stundenwerte[stunde]))

                # Statistische Auswertungen nach ForecastCalcMethod
                if ( ForecastCalcMethod == 'median'):
                    result[zeit_str] = int(median(stundenwerte[stunde]))
                if ( ForecastCalcMethod == 'mittel'):
                    result[zeit_str] = int(mean(stundenwerte[stunde]))
                if ( ForecastCalcMethod == 'min'):
                    result[zeit_str] = int(min(stundenwerte[stunde]))
                if ( ForecastCalcMethod == 'max'):
                    result[zeit_str] = int(max(stundenwerte[stunde]))

                # Hier Aufruf der Prognoseoptimierung
                if ( ForecastCalcMethod == 'median_opt'):
                    median_watt = int(median(stundenwerte[stunde]))
                    hour = stunde.strftime("%H:00")

                    # aus faktoren_dict den Faktor holen in dem der Wert median_watt liegt
                    try:
                        ranges = faktoren_dict[hour]
                        # Versuche passenden Bereich zu finden
                        factor_tmp = next(
                            factor_tmp for (low, high),  factor_tmp in ranges.items()
                            if low <= median_watt < high
                        )
                    except StopIteration:
                        # Kein Bereich gefunden → nimm höchsten (letzten) Wert dieser Stunde
                        factor_tmp = list(ranges.values())[-1]
                    except KeyError:
                        # Stunde nicht vorhanden → Standardwert
                        factor_tmp = 1

                    if print_level >= 3:
                        print("DEBUG Std, Factor, Median, Factor * Median: ", zeit_str,  factor_tmp, median_watt, int( factor_tmp * median_watt))
                    result[zeit_str] = int(factor_tmp * median_watt)

        data = []
        data.extend([(ts, 'Median', val, '0', '') for ts, val in result_median.items()])
        data.extend([(ts, 'Prognose', val, '0', '') for ts, val in result.items()])
        # Produktion aus PV_Daten.sqlite holen
        Produktion = self.get_produktion_result(von_tag)
        data.extend(Produktion)
        # Speichern der Resultate 
        self.storeWeatherData_SQL(data, 'Median, Prognose, Produktion')
        conn.close()

        return()

    def getSQLcurrentDayProduction(self, database):
        try:
            verbindung = sqlite3.connect(database)
            zeiger = verbindung.cursor()
            sql_anweisung = "SELECT MAX(DC_Produktion)- MIN(DC_Produktion) AS DC_Produktion from pv_daten where Zeitpunkt LIKE '" + self.now.strftime("%Y-%m-%d")+"%';"
            zeiger.execute(sql_anweisung)
            row = zeiger.fetchall()
            currentDayProduction = round(row[0][0]/1000,1)
        except:
            currentDayProduction = 0

        return (currentDayProduction)

    def sum_pv_data(self, pvdaten_dict):
        # 1. Daten aus allen Blöcken zusammenfassen und Werte addieren
        daten_dict = {}

        for block in pvdaten_dict:
            for zeit, quelle, wert, flag, kommentar in pvdaten_dict.get(block, []):
                key = (zeit, quelle)
                if key in daten_dict:
                    daten_dict[key]['wert'] += wert
                else:
                    daten_dict[key] = {'wert': wert, 'flag': flag, 'kommentar': kommentar}

        # 2. Ergebnisliste ohne Blöcke erzeugen
        dict_watts = []
        for (zeit, quelle), info in daten_dict.items():
            dict_watts.append((zeit, quelle, info['wert'], info['flag'], info['kommentar']))

        # Ergebnis nach Zeit sortieren
        dict_watts.sort(key=lambda x: x[0])

        return(dict_watts)
