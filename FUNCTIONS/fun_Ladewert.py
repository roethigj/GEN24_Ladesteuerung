from datetime import datetime, timedelta
import pytz
import requests
import FUNCTIONS.SymoGen24Connector
from ping3 import ping
from sys import argv
from FUNCTIONS.functions import loadConfig, loadWeatherData, loadPVReservierung, getVarConf, save_SQLite

# Hier die Variablen aus dem Hauptprogramm übergeben und global machen
def globalfrommain(g_now, g_DEBUG_Ausgabe, g_BattVollUm, g_data, g_PV_Reservierung_steuern,\
        g_reservierungdata, g_Grundlast, g_Einspeisegrenze, g_WR_Kapazitaet, g_BattKapaWatt_akt, \
        g_MaxLadung, g_BatSparFaktor, g_PrognoseAbzugswert, g_aktuelleBatteriePower, g_BattganzeLadeKapazWatt, \
        g_LadungAus, g_oldPercent):

        global now, DEBUG_Ausgabe, BattVollUm, data, PV_Reservierung_steuern, \
        reservierungdata, Grundlast, Einspeisegrenze, WR_Kapazitaet, BattKapaWatt_akt, \
        MaxLadung, BatSparFaktor, PrognoseAbzugswert, aktuelleBatteriePower, BattganzeLadeKapazWatt, \
        LadungAus, oldPercent

        now = g_now
        DEBUG_Ausgabe = g_DEBUG_Ausgabe
        BattVollUm = g_BattVollUm
        data = g_data
        PV_Reservierung_steuern = g_PV_Reservierung_steuern
        reservierungdata = g_reservierungdata
        Grundlast = g_Grundlast
        Einspeisegrenze = g_Einspeisegrenze
        WR_Kapazitaet = g_WR_Kapazitaet
        BattKapaWatt_akt = g_BattKapaWatt_akt
        MaxLadung = g_MaxLadung
        BatSparFaktor = g_BatSparFaktor
        PrognoseAbzugswert = g_PrognoseAbzugswert
        aktuelleBatteriePower = g_aktuelleBatteriePower
        BattganzeLadeKapazWatt = g_BattganzeLadeKapazWatt
        LadungAus = g_LadungAus
        oldPercent = g_oldPercent


def getPrognose(Stunde):
        if data['result']['watts'].get(Stunde):
            data_fun = data['result']['watts'][Stunde]
            # Wenn Reservierung eingeschaltet und Reservierungswert vorhanden von Prognose abziehen.
            if ( PV_Reservierung_steuern == 1 and reservierungdata.get(Stunde)):
                data_fun = data['result']['watts'][Stunde] - reservierungdata[Stunde]
                # Minuswerte verhindern
                if ( data_fun< 0): data_fun = 0
            getPrognose = data_fun
        else:
            getPrognose = 0
        return getPrognose

def getLadewertinGrenzen(Ladewert):
        # aktuellerLadewert zwischen 0 und MaxLadung halten
        if Ladewert < 0: Ladewert = 0
        if (Ladewert > MaxLadung): Ladewert = MaxLadung

        return Ladewert

def getRestTagesPrognoseUeberschuss():

        global BatSparFaktor, DEBUG_Ausgabe
        # alle Prognosewerte zwischen aktueller Stunde und 22:00 lesen
        format_Tag = "%Y-%m-%d"
        # aktuelle Stunde und aktuelle Minute
        Akt_Std = int(datetime.strftime(now, "%H"))
        Akt_Minute = int(datetime.strftime(now, "%M"))

        # Gesamte Tagesprognose, Tagesüberschuß aus Prognose ermitteln
        # Schleife laeft von Grundlast nach oben, bis der Prognoseueberschuss die aktuelle Batteriekapazität erreicht
        i = Akt_Std
        Pro_Ertrag_Tag = 0
        Grundlast_Sum = 0
        Prognose_array = list()
        groestePrognose = 0
        Stunden_sum = 0.0001
        Zwangs_Ueberschuss = 0
        DEBUG_Ausgabe += "\nDEBUG *************** Berechnung Abzugswert: \n"

        # in Schleife Prognosewerte bis BattVollUm durchlaufen
        while i < BattVollUm:
            Std = datetime.strftime(now, format_Tag)+" "+ str('%0.2d' %(i)) +":00:00"
            Prognose = getPrognose(Std)
            if groestePrognose < Prognose:
                groestePrognose = Prognose
            Grundlast_fun = Grundlast
            Einspeisegrenze_fun = Einspeisegrenze
            Stunden_fun = 1

            # wenn nicht zur vollen Stunde, Wert anteilsmaessig
            Grundlast_fun = Grundlast
            if i == Akt_Std:
                Prognose = (Prognose / 60 * (60 - Akt_Minute))
                Grundlast_fun = int((Grundlast / 60 * (60 - Akt_Minute)))
                Einspeisegrenze_fun = int((Einspeisegrenze / 60 * (60 - Akt_Minute)))
                Stunden_fun = (60-Akt_Minute)/60

            Prognose_array.append(Prognose)
            Pro_Ertrag_Tag += Prognose

            # Alles über Einspeisegrenze bzw WR_Kapazitaet von BattKapaWatt_akt abziehen,
            # da dies nicht für die Prognoseberechnung zur Verfügung steht.
            Zwangs_Ueberschuss_fun = (Prognose - Einspeisegrenze_fun - Grundlast_fun)
            if ( Prognose - WR_Kapazitaet > Zwangs_Ueberschuss_fun ): Zwangs_Ueberschuss_fun = Prognose - WR_Kapazitaet
            if ( Zwangs_Ueberschuss_fun > 0): Zwangs_Ueberschuss += Zwangs_Ueberschuss_fun

            Stunden_sum += Stunden_fun

            DEBUG_Ausgabe += "DEBUG ##Schleife## Stunden_sum: " + str(round(Stunden_sum, 3)) + ", Prognose: " + str(round(Prognose,2)) + ", Pro_Ertrag_Tag: " + str(round(Pro_Ertrag_Tag,2)) + "\n"
            Grundlast_Sum += Grundlast_fun

            i += 1

        BattKapaWatt_akt_fun = BattKapaWatt_akt - Zwangs_Ueberschuss
        if Stunden_sum < 1: Stunden_sum = 1
        AbzugsWatt = int((Pro_Ertrag_Tag - BattKapaWatt_akt_fun) / Stunden_sum)
        DEBUG_Ausgabe += "DEBUG #### AbzugsWatt incl. MaxLadung Überschuss: " + str(round(AbzugsWatt, 2)) + "\n"

        # hier noch die Ladewerte über MaxLadung ermitteln und Überschuss von AbzugsWatt abziehen
        # damit wird bei niedrigen Prognosen mehr geladen, da bei hohen nicht über MaxLadung geladen werden kann
        Pro_Uberschuss = 0
        Schleifenzaehler = 0
        for Prognose_einzel in Prognose_array:
            if (Prognose_einzel - AbzugsWatt > MaxLadung): 
                Pro_Uberschuss += Prognose_einzel - AbzugsWatt - MaxLadung
                Schleifenzaehler += 1
        if (Pro_Uberschuss > 0 and Schleifenzaehler > 0):
            AbzugsWatt = int(AbzugsWatt - Pro_Uberschuss / Schleifenzaehler)

        if (AbzugsWatt < 0):
            AbzugsWatt = 0

        Pro_Uebersch_Tag = BattKapaWatt_akt_fun
        DEBUG_Ausgabe += "DEBUG ##Ergebnis## AbzugsWatt: " + str(round(AbzugsWatt, 2)) + ",  Pro_Uebersch_Tag: " + str(round(Pro_Uebersch_Tag, 2)) + ", Stunden_sum: "  + str(round(Stunden_sum, 2)) + "\n"

        return int(Pro_Uebersch_Tag), int(Pro_Ertrag_Tag), AbzugsWatt, Grundlast_Sum, groestePrognose

def getPrognoseLadewert( AbzugWatt ):

        global DEBUG_Ausgabe
        format_Tag = "%Y-%m-%d"
        Spreizung = 1
        Akt_Std = int(datetime.strftime(now, "%H"))
        Akt_Minute = int(datetime.strftime(now, "%M"))
        Pro_Akt = 0
        i = Akt_Std - Spreizung
        loop = 0
        while i <= Akt_Std + Spreizung:
            Std = datetime.strftime(now, format_Tag)+" "+ str('%0.2d' %(i)) +":00:00"
            Prognose = getPrognose(Std)
            Pro_Akt_fun = Prognose
            DEBUG_Ausgabe += "\nDEBUG *************** Ladewertmittel LOOP: " + str(loop)
            if loop == 0:
                Pro_Akt_fun = Prognose * (60 - Akt_Minute) / 60
                DEBUG_Ausgabe += "\nDEBUG ########### Pro_Akt_fun: " + str(round(Pro_Akt_fun,2)) + " REST_Akt_Minute: " + str(round(((60 - Akt_Minute) / 60),3))
            if loop == Spreizung * 2:
                Pro_Akt_fun = Prognose * (Akt_Minute) / 60
                DEBUG_Ausgabe += "\nDEBUG ########### Pro_Akt_fun: " + str(round(Pro_Akt_fun,2)) + " Akt_Minute: " + str(round(((Akt_Minute) / 60),3))
            Pro_Akt += Pro_Akt_fun
            DEBUG_Ausgabe += "\nDEBUG  " + str(Std) + " Pro_Akt_fun: " + str(round(Pro_Akt_fun,2)) + " Prognose_gesamt: " + str(round(Pro_Akt,2)) + "\n"
            loop += 1
            i += 1
        Pro_Akt = int(Pro_Akt / Spreizung / 2 )

        # Nun den Aktuellen Ladewert rechnen 
        # Batterieladewert mit allen Einfluessen aus der Prognose rechnen
        aktuellerLadewert = int((Pro_Akt - AbzugWatt) * BatSparFaktor)
        aktuellerLadewert = getLadewertinGrenzen(aktuellerLadewert)

        LadewertGrund = "Prognoseberechnung / BatSparFaktor"

        DEBUG_Ausgabe += "\nDEBUG " + datetime.strftime(now, "%D %H:%M") + " Aktuelle Prognose: " + str(Pro_Akt) + " BatSparFaktor: " + str(BatSparFaktor) + " aktueller Ladewert: " + str(aktuellerLadewert)
        DEBUG_Ausgabe += ", Batteriekapazität: " + str(BattKapaWatt_akt) + ", Abzug: " + str(PrognoseAbzugswert)

        ### Prognose ENDE
        return  aktuellerLadewert, Pro_Akt, LadewertGrund


def getEinspeiseGrenzeLadewert(WRSchreibGrenze_nachOben, aktuellerLadewert, aktuelleEinspeisung, aktuellePVProduktion, LadewertGrund, alterLadewert, PV_Leistung_Watt):
        ### Einspeisegrenze ANFANG
        global DEBUG_Ausgabe
        # Hinweis: aktuelleBatteriePower ist beim Laden der Batterie minus
        # Wenn Einspeisung über Einspeisegrenze, dann könnte WR schon abregeln, desshalb WRSchreibGrenze_nachOben addieren
        # Durch Trägheit des WR wird vereinzelt die Einspeisung durch gleichzeitigen Netzbezug größer als die Produktion, dann nicht anwenden
        if (aktuelleEinspeisung - aktuelleBatteriePower > Einspeisegrenze) and aktuelleEinspeisung < aktuellePVProduktion:
            if (aktuelleEinspeisung - aktuelleBatteriePower - alterLadewert > Einspeisegrenze):
                EinspeisegrenzUeberschuss = int(aktuelleEinspeisung + alterLadewert - Einspeisegrenze + (WRSchreibGrenze_nachOben + 5))
            else:
                EinspeisegrenzUeberschuss = int(aktuelleEinspeisung + alterLadewert - Einspeisegrenze)

            # Damit durch die Pufferaddition nicht die maximale PV_Leistung überschritten wird
            if EinspeisegrenzUeberschuss > PV_Leistung_Watt - Einspeisegrenze:
                EinspeisegrenzUeberschuss = PV_Leistung_Watt - Einspeisegrenze

            EinspeisegrenzUeberschuss = getLadewertinGrenzen(EinspeisegrenzUeberschuss)

            if EinspeisegrenzUeberschuss > aktuellerLadewert and alterLadewert <= (MaxLadung + 100):
                DEBUG_Ausgabe += "\nDEBUG EinspeisegrenzUeberschuss: " + str(EinspeisegrenzUeberschuss) + " aktuellerLadewert: " + str(aktuellerLadewert) + " alterLadewert: " + str(alterLadewert)
                aktuellerLadewert = int(EinspeisegrenzUeberschuss)
                LadewertGrund = "PV_Leistungsüberschuss > Einspeisegrenze"

        aktuellerLadewert = getLadewertinGrenzen(aktuellerLadewert)
        ### Einspeisegrenze ENDE
        return  aktuellerLadewert, LadewertGrund

def getAC_KapaLadewert(WRSchreibGrenze_nachOben, aktuellerLadewert, aktuellePVProduktion, LadewertGrund, alterLadewert, PV_Leistung_Watt):
        ### AC_Kapazitaet WR ANFANG
        # Wenn  PV-Produktion > WR_Kapazitaet (AC)
        if aktuellePVProduktion > WR_Kapazitaet:
            kapazitaetsueberschuss = int(aktuellePVProduktion - WR_Kapazitaet )
            if (kapazitaetsueberschuss > alterLadewert):
                if (kapazitaetsueberschuss < alterLadewert + WRSchreibGrenze_nachOben):
                    kapazitaetsueberschuss = alterLadewert + WRSchreibGrenze_nachOben + 10
                    # Damit der kapazitaetsueberschuss durch die Addition der WRSchreibGrenze_nachOben nicht grösser als die PV_Leistung_Watt wird.
                    if kapazitaetsueberschuss > PV_Leistung_Watt - WR_Kapazitaet:
                        kapazitaetsueberschuss = PV_Leistung_Watt - WR_Kapazitaet
                aktuellerLadewert = kapazitaetsueberschuss
                LadewertGrund = "PV-Produktion > AC_Kapazitaet WR"

        aktuellerLadewert = getLadewertinGrenzen(aktuellerLadewert)
        ### AC_Kapazitaet WR ENDE
        return  aktuellerLadewert, LadewertGrund

def setLadewert(fun_Ladewert, WRSchreibGrenze_nachOben, WRSchreibGrenze_nachUnten):
        fun_Ladewert = getLadewertinGrenzen(fun_Ladewert)

        newPercent = (int(fun_Ladewert/BattganzeLadeKapazWatt*10000))
        if newPercent < LadungAus:
            newPercent = LadungAus

        # Schaltvezögerung
        # mit altem Ladewert vergleichen
        diffLadewert_nachOben = int(fun_Ladewert - oldPercent*BattganzeLadeKapazWatt/10000)
        diffLadewert_nachUnten = int((oldPercent*BattganzeLadeKapazWatt/10000) - fun_Ladewert)

        # Wenn die Differenz in hundertstel Prozent kleiner als die Schreibgrenze nix schreiben
        newPercent_schreiben = 0
        if ( diffLadewert_nachOben > WRSchreibGrenze_nachOben ):
            newPercent_schreiben = 1
        if ( diffLadewert_nachUnten > WRSchreibGrenze_nachUnten ):
            newPercent_schreiben = 1

        # Wenn MaxLadung erstmals erreicht ist immer schreiben
        if (fun_Ladewert == MaxLadung) and (abs(diffLadewert_nachOben) > 3):
            newPercent_schreiben = 1

        return(newPercent, newPercent_schreiben)

def getPrognoseMorgen():
    i = 0
    Prognose_Summe = 0
    while i < 24:
        Std_morgen = datetime.strftime(now + timedelta(days=1), "%Y-%m-%d")+" "+ str('%0.2d' %(i)) +":00:00"
        Prognose_Summe += getPrognose(Std_morgen)
        i  += 1
    return(Prognose_Summe)
    
def getParameter(argv):
    Parameter = ""
    if len(argv) > 1 :
        Parameter = argv[1]
    # Prog_Steuerung.json lesen
    Prog_Steuer_code_tmp = loadPVReservierung('Prog_Steuerung.json')
    Prog_Steuer_code = int(Prog_Steuer_code_tmp['Steuerung'])
    print("Prog_Steuer_code: ", Prog_Steuer_code)
    if Prog_Steuer_code == 1:
        Parameter = 'exit'
    if Prog_Steuer_code == 2:
        Parameter = 'analyse'
    if Prog_Steuer_code == 3:
        Parameter = 'logging'
    if Prog_Steuer_code == 4:
        Parameter = 'schreiben'
    return(Parameter)
