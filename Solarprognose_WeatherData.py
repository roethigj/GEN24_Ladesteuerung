import requests
import json
import os.path
import pytz
import time
from pathlib import Path
from datetime import datetime, timedelta
import FUNCTIONS.functions

def loadLatestWeatherData():
    url = 'http://www.solarprognose.de/web/solarprediction/api/v1?access-token={}&item={}&id={}&type={}&algorithm={}'.format(accesstoken, item, id, type, algorithm)
    # Hier wieder ABHOLEN EIN
    try:
        apiResponse = requests.get(url, timeout=99)
        apiResponse.raise_for_status()
        if apiResponse.status_code != 204:
            json_data1 = dict(json.loads(apiResponse.text))
        else:
            print("### ERROR:  Keine forecasts-Daten von www.solarprognose.de")
            exit()
    except requests.exceptions.Timeout:
        print("### ERROR:  Timeout von www.solarprognose.de")
        exit()
    dict_watts = {}
    dict_watts['result'] = {}
    dict_watts['result']['watts'] = {}

    for key, value in json_data1.get('data',{}).items():
        key_neu = str(datetime.fromtimestamp(value[0]) + timedelta(hours=Zeitversatz))
        dict_watts['result']['watts'][key_neu] = int(value[1]*1000*KW_Faktor)
    return(dict_watts, json_data1)

if __name__ == '__main__':
    basics = FUNCTIONS.functions.basics()
    config = basics.loadConfig(['default', 'weather'])
    # Benoetigte Variablen definieren und prüfen
    id = basics.getVarConf('solarprognose', 'id', 'eval')
    KW_Faktor = basics.getVarConf('solarprognose', 'KW_Faktor', 'eval')
    dataAgeMaxInMinutes = basics.getVarConf('solarprognose', 'dataAgeMaxInMinutes', 'eval')
    WaitSec = basics.getVarConf('solarprognose', 'WaitSec', 'eval')
    weatherfile = basics.getVarConf('solarprognose', 'weatherfile', 'str')
    accesstoken = basics.getVarConf('solarprognose', 'accesstoken', 'str')
    item = basics.getVarConf('solarprognose', 'item', 'str')
    type = basics.getVarConf('solarprognose', 'type', 'str')
    Zeitversatz = int(basics.getVarConf('solarprognose', 'Zeitversatz', 'eval'))
    algorithm = basics.getVarConf('solarprognose', 'algorithm', 'str')

    time.sleep(WaitSec)
    
    format = "%Y-%m-%d %H:%M:%S"    
    now = datetime.now()    
    
    data = basics.loadWeatherData(weatherfile)
    dataIsExpired = True
    if (data):
        dateCreated = None
        if (data['messageCreated']):
            dateCreated = datetime.strptime(data['messageCreated'], format)
        
        if (dateCreated):
            diff = now - dateCreated
            dataAgeInMinutes = diff.total_seconds() / 60
            if (dataAgeInMinutes < dataAgeMaxInMinutes):                
                print_level = basics.getVarConf('env','print_level','eval')
                if ( print_level != 0 ):
                    print('solarprognose.de: Die Minuten aus "dataAgeMaxInMinutes" ', dataAgeMaxInMinutes ,' Minuten sind noch nicht abgelaufen!!')
                    print(f'[Now: {now}] [Data created:  {dateCreated}] -> age in min: {dataAgeInMinutes}')
                dataIsExpired = False

    if (dataIsExpired):
        data_all = loadLatestWeatherData()
        data = data_all[0]
        data_err = data_all[1]
        if(data['result']['watts'] != {}):
            if not data == "False":
                # hier evtl Begrenzungen der Prognose anbringen
                MaximalPrognosebegrenzung = basics.getVarConf('env','MaximalPrognosebegrenzung','eval')
                if (MaximalPrognosebegrenzung == 1):
                    data = basics.checkMaxPrognose(data)
                if (MaximalPrognosebegrenzung == 2):
                    data = basics.Prognoseoptimierung(data)
                basics.storeWeatherData(weatherfile, data, now, 'solarprognose.de')
        else:
            print("Fehler bei Datenanforderung solarprognose.de:")
            print(data_err)
