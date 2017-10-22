import http.client
from time import sleep
import json
import datetime
import secrets


class NestLogger:
    def __init__(self, nest_token, nest_thermostat, wunderground_key, zip_code):
        self.nest_token = nest_token
        self.nest_thermostat = nest_thermostat
        self.wunderground_key = wunderground_key
        self.logging_file = open("nest_data.txt", "a")
        self.nest_endpoint = "developer-api.nest.com"
        self.wunderground_endpoint = "api.wunderground.com"
        self.loc = zip_code  # can actually be lat/lon, state abbr/city, or zip code

    def execute(self):
        collection_iteration = 0
        while True:
            json_data = self.get_nest_json()
            self.clean_nest_data(json_data)
            json_data['timestamp'] = int(datetime.datetime.utcnow().timestamp())
            wunderground_json = self.get_wunderground_json()
            try:
                print(str(datetime.datetime.now()) + ': current indoor temp: ' + str(json_data['ambient_temperature_f']))
                json_data['outdoor_temp'] = str(wunderground_json['temp_f'])
                json_data['outdoor_rel_humidity'] = str(wunderground_json['relative_humidity'])
            except Exception as exception:
                print('ERR!' + str(exception))  # if the API failed, just silently don't log anything
            self.logging_file.write(str(json_data).replace('\'', '"') + ',\n')
            self.logging_file.flush()
            collection_iteration += 1
            sleep(60 * 5)

    def get_nest_json(self):
        headers = {
            'content-type': "application/json",
            'authorization': self.nest_token,
        }
        try:
            conn = http.client.HTTPSConnection(self.nest_endpoint)
            conn.request("GET", "/devices/thermostats/" + self.nest_thermostat, headers=headers)
            raw_res = conn.getresponse()
            if raw_res.status == 307:  # redirect to new endpoint. follow and update endpoint
                new_location = raw_res.getheader('Location')
                self.nest_endpoint = new_location[new_location.find("//") + 2:new_location.find("/devices")]
                print('followed 307 to: ' + self.nest_endpoint)
                conn = http.client.HTTPSConnection(self.nest_endpoint)
                conn.request("GET", "/devices/thermostats/" + self.nest_thermostat, headers=headers)
                raw_res = conn.getresponse()
            return json.loads(raw_res.read().decode("utf-8"))
        except (ConnectionError, TimeoutError) as err:
            print('Error during nest API call: ' + str(err))
            return json.loads('{}')

    @staticmethod
    def clean_nest_data(nest_json):
        try:
            del nest_json['fan_timer_timeout']
            del nest_json['previous_hvac_mode']
            del nest_json['time_to_target_training']
            del nest_json['ambient_temperature_c']
            del nest_json['where_name']
            del nest_json['target_temperature_high_c']
            del nest_json['target_temperature_low_f']
            del nest_json['can_heat']
            del nest_json['away_temperature_low_c']
            del nest_json['away_temperature_high_c']
            del nest_json['temperature_scale']
            del nest_json['locked_temp_max_c']
            del nest_json['can_cool']
            del nest_json['eco_temperature_low_f']
            del nest_json['locked_temp_min_c']
            del nest_json['where_id']
            del nest_json['is_locked']
            del nest_json['away_temperature_low_f']
            del nest_json['eco_temperature_high_f']
            del nest_json['fan_timer_duration']
            del nest_json['sunlight_correction_enabled']
            del nest_json['has_fan']
            del nest_json['name_long']
            del nest_json['structure_id']
            del nest_json['eco_temperature_high_c']
            del nest_json['target_temperature_high_f']
            del nest_json['is_using_emergency_heat']
            del nest_json['target_temperature_c']
            del nest_json['name']
            del nest_json['label']
            del nest_json['device_id']
            del nest_json['locked_temp_max_f']
            del nest_json['away_temperature_high_f']
            del nest_json['fan_timer_active']
        except Exception as ex:
            print(ex)

    def get_wunderground_json(self):
        try:
            conn = http.client.HTTPConnection(self.wunderground_endpoint)
            conn.request('GET', '/api/' + self.wunderground_key + '/conditions/q/' + self.loc + '.json')
            raw_res = conn.getresponse().read().decode("utf-8")
            return json.loads(raw_res)['current_observation']
        except (ConnectionError, TimeoutError) as err:
            print('Error during Wunderground API call: ' + str(err))
            return json.loads('{}')

if __name__ == '__main__':
    instance = NestLogger(nest_token=secrets.bearer_token, nest_thermostat=secrets.thermostat_id,
                          wunderground_key=secrets.wunderground_secret, zip_code=secrets.zip_code)
    instance.execute()
