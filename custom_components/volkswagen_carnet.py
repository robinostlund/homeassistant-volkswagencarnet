import re
import requests
import json
import time
import logging

from datetime import timedelta, datetime


import voluptuous as vol
import homeassistant.helpers.config_validation as cv


from urllib.parse import urlsplit,urlsplit
from urllib.error import HTTPError

from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD)
from homeassistant.util import Throttle
from homeassistant.helpers import discovery
from homeassistant.helpers.event import track_point_in_utc_time
from homeassistant.util.dt import utcnow
from homeassistant.helpers.dispatcher import dispatcher_send

_LOGGER = logging.getLogger(__name__)

DOMAIN = 'volkswagen_carnet'
CARNET_DATA = "volkswagen_carnet"
REQUIREMENTS = ['requests']
CONF_UPDATE_INTERVAL = 'update_interval'

MIN_UPDATE_INTERVAL = timedelta(minutes=1)
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=1)
SIGNAL_VEHICLE_SEEN = '{}.vehicle_seen'.format(DOMAIN)

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): (
            vol.All(cv.time_period, vol.Clamp(min=MIN_UPDATE_INTERVAL))),
    }),
}, extra = vol.ALLOW_EXTRA)


def setup(hass, config):
    """Setup Volkswagen Carnet component"""

    #carnet_config = config.get(DOMAIN, {})
    username = config[DOMAIN].get(CONF_USERNAME)
    password = config[DOMAIN].get(CONF_PASSWORD)
    interval = config[DOMAIN].get(CONF_UPDATE_INTERVAL)

    # Store data
    hass.data[CARNET_DATA] = VWCarnet(hass, username, password)
    vw = hass.data[CARNET_DATA]

    # Login to online services
    if not vw.carnet_logged_in:
        _LOGGER.error("Failed to login to Volkswagen Carnet")
        return False

    for component in ['switch', 'device_tracker', 'sensor']:
        discovery.load_platform(hass, component, DOMAIN, {}, config)

    def update_vehicle(vehicle):
        """Revieve updated information on vehicle."""

        dispatcher_send(hass, SIGNAL_VEHICLE_SEEN, vehicle)

    def update(now):
        """Update status from the online service."""
        try:
            for vehicle in vw.vehicles:
                if not vw._carnet_update_vehicle_status(vehicle, force_update=True):
                    _LOGGER.warning("Could not update vehicle %s" % (vehicle))
                    return False

                update_vehicle(vehicle)

            return True
        finally:
            track_point_in_utc_time(hass, update, utcnow() + interval)

    return update(utcnow())


class VWCarnet(object):
    def __init__(self, hass, username, password):
        self.hass = hass
        self.carnet_username = username
        self.carnet_password = password
        self.carnet_logged_in = False
        self.vehicles = {}

        # Fake the VW CarNet mobile app headers
        self.headers = { 'Accept': 'application/json, text/plain, */*', 'Content-Type': 'application/json;charset=UTF-8', 'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0.1; D5803 Build/23.5.A.1.291; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/63.0.3239.111 Mobile Safari/537.36' }
        self.base = "https://www.volkswagen-car-net.com"
        self.session = requests.Session()
        self.update_timeout_counter = 80 # seconds

        # login to carnet
        self._carnet_login()

        # fetch vehicles
        self._carnet_get_vehicles()

    def _vehicle_template(self, vin):
        vehicle_template = {
            'vin': vin.get('vin'),
            'pin': vin.get('enrollmentPin'),
            'name': vin.get('vehicleName'),
            'model_year': False,
            'model_code': False,
            'model_image_url': False,
            'dashboard_url': False,
            'profile_id': False,
            'last_connected': False,
            'state_charge': False,
            'state_climat': False,
            'state_melt': False,
            'location_latitude': False,
            'location_longitude': False,
            'sensor_battery_left': False,
            'sensor_charge_max_ampere': False,
            'sensor_external_power_connected': False,
            'sensor_charging_time_left': False,
            'sensor_climat_target_temperature': False,
            'sensor_electric_range_left': False,
            'sensor_next_service_inspection': False,
            'sensor_distance': False,
            'sensor_door_locked': False,
            'sensor_parking_lights': False,
        }
        return vehicle_template

    def _carnet_login(self):
        # login to carnet
        try:
            _LOGGER.debug("Trying to login to Volkswagen Carnet")
            AUTHHEADERS = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0.1; D5803 Build/23.5.A.1.291; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/63.0.3239.111 Mobile Safari/537.36'}

            auth_base = "https://security.volkswagen.com"

            # Regular expressions to extract data
            csrf_re = re.compile('<meta name="_csrf" content="([^"]*)"/>')
            redurl_re = re.compile('<redirect url="([^"]*)"></redirect>')
            viewstate_re = re.compile('name="javax.faces.ViewState" id="j_id1:javax.faces.ViewState:0" value="([^"]*)"')
            authcode_re = re.compile('code=([^"]*)&')
            authstate_re = re.compile('state=([^"]*)')

            def extract_csrf(r):
                return csrf_re.search(r.text).group(1)

            def extract_redirect_url(r):
                return redurl_re.search(r.text).group(1)

            def extract_view_state(r):
                return viewstate_re.search(r.text).group(1)

            def extract_code(r):
                return authcode_re.search(r).group(1)

            def extract_state(r):
                return authstate_re.search(r).group(1)

            # Request landing page and get CSFR:
            r = self.session.get(self.base + '/portal/en_GB/web/guest/home')
            if r.status_code != 200:
                return ""
            csrf = extract_csrf(r)

            # Request login page and get CSRF
            AUTHHEADERS["Referer"] = self.base + '/portal'
            AUTHHEADERS["X-CSRF-Token"] = csrf
            r = self.session.post(self.base + '/portal/web/guest/home/-/csrftokenhandling/get-login-url', headers=AUTHHEADERS)
            if r.status_code != 200:
                return ""
            responseData = json.loads(r.content)
            lg_url = responseData.get("loginURL").get("path")

            # no redirect so we can get values we look for
            r = self.session.get(lg_url, allow_redirects=False, headers = AUTHHEADERS)
            if r.status_code != 302:
                return ""
            ref_url = r.headers.get("location")

            # now get actual login page and get session id and ViewState
            r = self.session.get(ref_url, headers = AUTHHEADERS)
            if r.status_code != 200:
                return ""
            view_state = extract_view_state(r)

            # Login with user details
            AUTHHEADERS["Faces-Request"] = "partial/ajax"
            AUTHHEADERS["Referer"] = ref_url
            AUTHHEADERS["X-CSRF-Token"] = ''

            post_data = {
                'loginForm': 'loginForm',
                'loginForm:email': self.carnet_username,
                'loginForm:password': self.carnet_password,
                'loginForm:j_idt19': '',
                'javax.faces.ViewState': view_state,
                'javax.faces.source': 'loginForm:submit',
                'javax.faces.partial.event': 'click',
                'javax.faces.partial.execute': 'loginForm:submit loginForm',
                'javax.faces.partial.render': 'loginForm',
                'javax.faces.behavior.event': 'action',
                'javax.faces.partial.ajax': 'true'
            }

            r = self.session.post(auth_base + '/ap-login/jsf/login.jsf', data=post_data, headers = AUTHHEADERS)
            if r.status_code != 200:
                return ""
            ref_url = extract_redirect_url(r).replace('&amp;', '&')

            # redirect to link from login and extract state and code values
            r = self.session.get(ref_url, allow_redirects=False, headers = AUTHHEADERS)
            if r.status_code != 302:
                return ""
            ref_url2 = r.headers.get("location")

            code = extract_code(ref_url2)
            state = extract_state(ref_url2)

            # load ref page
            r = self.session.get(ref_url2, headers = AUTHHEADERS)
            if r.status_code != 200:
                return ""

            AUTHHEADERS["Faces-Request"] = ""
            AUTHHEADERS["Referer"] = ref_url2
            post_data = {
                '_33_WAR_cored5portlet_code': code,
                '_33_WAR_cored5portlet_landingPageUrl': ''
            }
            r = self.session.post(self.base + urlsplit(
                ref_url2).path + '?p_auth=' + state + '&p_p_id=33_WAR_cored5portlet&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&p_p_col_id=column-1&p_p_col_count=1&_33_WAR_cored5portlet_javax.portlet.action=getLoginStatus',
                       data=post_data, allow_redirects=False, headers=AUTHHEADERS)
            if r.status_code != 302:
                return ""

            ref_url3 = r.headers.get("location")
            r = self.session.get(ref_url3, headers=AUTHHEADERS)

            # We have a new CSRF
            csrf = extract_csrf(r)

            # Update headers for requests
            self.headers["Referer"] = ref_url3
            self.headers["X-CSRF-Token"] = csrf
            self.url = ref_url3
            self.carnet_logged_in = True
            _LOGGER.debug("Login to Volkswagen Carnet was successfull")
            return True

        except HTTPError as e:
            _LOGGER.error("Unable to login to Volkswagen CarNet")
            _LOGGER.debug("Error msg: %s" % (e))
            return False

    def _carnet_get_owners_verification(self):
        if not self.carnet_logged_in:
            self._carnet_login()
        if not self.carnet_logged_in:
            _LOGGER.error('Couldnt do action. There was a problem with the login.')
            return False
        url = self.base + '/portal/group/se/edit-profile/-/profile/get-vehicles-owners-verification'
        req = self.session.post(url, headers = self.headers)
        return json.loads(req.content)


    def _carnet_post(self, command):
        if not self.carnet_logged_in:
            self._carnet_login()
        if not self.carnet_logged_in:
            _LOGGER.error('Couldnt do action. There was a problem with the login.')
            return False
        req = self.session.post(self.url + command, headers = self.headers)
        return req.content

    def _carnet_post_action(self, command, data):
        if not self.carnet_logged_in:
            self._carnet_login()
        if not self.carnet_logged_in:
            _LOGGER.error('Couldnt do action. There was a problem with the login.')
            return False
        req = self.session.post(self.url + command, json = data, headers = self.headers)
        return req.content

    def _carnet_post_vehicle(self, vehicle, command):
        if not self.carnet_logged_in:
            self._carnet_login()
        if not self.carnet_logged_in:
            _LOGGER.error('Couldnt do action. There was a problem with the login.')
            return False
        dashboard_url = self.vehicles[vehicle].get('dashboard_url')
        req = self.session.post(self.base + dashboard_url + command, headers=self.headers)
        return req.content

    def _carnet_post_action_vehicle(self, vehicle, command, data):
        if not self.carnet_logged_in:
            self._carnet_login()
        if not self.carnet_logged_in:
            _LOGGER.error('Couldnt do action. There was a problem with the login.')
            return False
        dashboard_url = self.vehicles[vehicle].get('dashboard_url')
        req = self.session.post(self.base + dashboard_url + command, json=data, headers=self.headers)
        return req.content

    def _carnet_start_charge(self, vehicle):
        _LOGGER.debug("Trying to start charging")
        self._set_state('charge', vehicle, True)
        post_data = {
            'triggerAction': True,
            'batteryPercent': '100'
        }
        return json.loads(self._carnet_post_action_vehicle(vehicle, '/-/emanager/charge-battery', post_data))

    def _carnet_stop_charge(self, vehicle):
        _LOGGER.debug("Trying to stop charging")
        self._set_state('charge', vehicle, False)
        post_data = {
            'triggerAction': False,
            'batteryPercent': '99'
        }
        return json.loads(self._carnet_post_action_vehicle(vehicle, '/-/emanager/charge-battery', post_data))


    def _carnet_start_climat(self, vehicle):
        _LOGGER.debug("Trying to start climat")
        self._set_state('climat', vehicle, True)
        post_data = {
            'triggerAction': True,
            'electricClima': True
        }
        return json.loads(self._carnet_post_action_vehicle(vehicle, '/-/emanager/trigger-climatisation', post_data))


    def _carnet_stop_climat(self, vehicle):
        _LOGGER.debug("Trying to stop climat")
        self._set_state('climat', vehicle, False)
        post_data = {
            'triggerAction': False,
            'electricClima': True
        }
        return json.loads(self._carnet_post_action_vehicle(vehicle, '/-/emanager/trigger-climatisation', post_data))

    def _carnet_start_window_melt(self, vehicle):
        _LOGGER.debug("Trying to start window melt")
        self._set_state('melt', vehicle, True)
        post_data = {
            'triggerAction': True
        }
        return json.loads(self._carnet_post_action_vehicle(vehicle, '/-/emanager/trigger-windowheating', post_data))

    def _carnet_stop_window_melt(self, vehicle):
        _LOGGER.debug("Trying to stop window melt")
        self._set_state('melt', vehicle, False)
        post_data = {
            'triggerAction': False
        }
        return json.loads(self._carnet_post_action_vehicle(vehicle, '/-/emanager/trigger-windowheating', post_data))

    @Throttle(timedelta(seconds=1))
    def _carnet_get_vehicles(self):
        _LOGGER.debug('Fetching vehicles from Volkswagen Carnet')
        # get vehicles
        try:
            data_owner_verification = self._carnet_get_owners_verification()
            for vehicle in data_owner_verification['vehiclesForEnrollmentResponseList']:
                self.vehicles[vehicle.get('vin')] = self._vehicle_template(vehicle)
                _LOGGER.debug('Adding vehicle: %s' % (vehicle.get('vin')))

            # add extra information
            non_loaded_cars = json.loads(self._carnet_post('/-/mainnavigation/get-fully-loaded-cars'))
            for vehicle in non_loaded_cars['fullyLoadedVehiclesResponse']['completeVehicles']:
                if vehicle.get('vin') in self.vehicles:
                    self.vehicles[vehicle.get('vin')]['dashboard_url'] = vehicle.get('dashboardUrl')
                    self.vehicles[vehicle.get('vin')]['profile_id'] = vehicle.get('xprofileId')
                    self.vehicles[vehicle.get('vin')]['model_year'] = vehicle.get('modelYear')
                    self.vehicles[vehicle.get('vin')]['model_code'] = vehicle.get('modelCode')
                    self.vehicles[vehicle.get('vin')]['model_image_url'] = vehicle.get('imageUrl')
                    _LOGGER.debug('Adding extra information for vehicle: %s' % (vehicle.get('vin')))

            for vehicle in non_loaded_cars['fullyLoadedVehiclesResponse']['vehiclesNotFullyLoaded']:
                if vehicle.get('vin') in self.vehicles:
                    self.vehicles[vehicle.get('vin')]['dashboard_url'] = vehicle.get('dashboardUrl')
                    self.vehicles[vehicle.get('vin')]['profile_id'] = vehicle.get('xprofileId')
                    self.vehicles[vehicle.get('vin')]['model_year'] = vehicle.get('modelYear')
                    self.vehicles[vehicle.get('vin')]['model_code'] = vehicle.get('modelCode')
                    self.vehicles[vehicle.get('vin')]['model_image_url'] = vehicle.get('imageUrl')
                    _LOGGER.debug('Adding extra information for vehicle: %s' % (vehicle.get('vin')))

        except HTTPError as e:
            _LOGGER.error("Failed to fetch vehicles from Volkswagen Carnet")
            _LOGGER.debug("Error msg: %s" % (e))
            self.carnet_updates_in_progress = False
            self.carnet_logged_in = False
            return False

    @Throttle(timedelta(seconds=1))
    def _carnet_update_vehicle_status(self, vehicle, force_update = False):
        _LOGGER.debug("Trying to update status for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        try:
            # request car update
            self._carnet_post_vehicle(vehicle, '/-/vsr/request-vsr')

            request_status = json.loads(self._carnet_post_vehicle(vehicle, '/-/vsr/get-vsr'))
            # wait for update to be completed:
            #timeout_counter = 0
            #if force_update:
            #    while request_status['vehicleStatusData']['requestStatus'] == 'REQUEST_IN_PROGRESS':
            #        request_status = json.loads(self._carnet_post_vehicle(vehicle, '/-/vsr/get-vsr'))
            #        timeout_counter += 1
            #        time.sleep(1)
            #        if timeout_counter > self.update_timeout_counter:
            #            raise HTTPError(code = '408', msg = 'Request to Volkswagen Carnet timeout.', hdrs = '', fp = None, url = None)

            # get data from carnet
            data_emanager = json.loads(self._carnet_post_vehicle(vehicle, '/-/emanager/get-emanager'))
            data_location = json.loads(self._carnet_post_vehicle(vehicle, '/-/cf/get-location'))
            data_details = json.loads(self._carnet_post_vehicle(vehicle,'/-/vehicle-info/get-vehicle-details'))
            data_car = json.loads(self._carnet_post_vehicle(vehicle, '/-/vsr/get-vsr'))
            _LOGGER.debug("Status updated for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        except HTTPError as e:
            _LOGGER.error("Failed to fetch status for vehicle %s" % (self.vehicles[vehicle].get('vin')))
            _LOGGER.debug("Error msg: %s" % (e))
            self.carnet_logged_in = False
            return False


        # set new location data
        try:
            self.vehicles[vehicle]['location_latitude'] = data_location['position']['lat']
            self.vehicles[vehicle]['location_longitude'] = data_location['position']['lng']
        except:
            _LOGGER.debug("Failed to set location status for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set powersupply sensor
        try:
            if data_emanager['EManager']['rbc']['status']['extPowerSupplyState'] == 'UNAVAILABLE':
                self.vehicles[vehicle]['sensor_external_power_connected'] = 'no'
            else:
                self.vehicles[vehicle]['sensor_external_power_connected'] = 'yes'
        except:
            self.vehicles[vehicle]['sensor_external_power_connected'] = False
            _LOGGER.debug("Failed to set powersupply status for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set battery sensor
        try:
            self.vehicles[vehicle]['sensor_battery_left'] = int(data_emanager['EManager']['rbc']['status']['batteryPercentage'])
        except:
            self.vehicles[vehicle]['sensor_battery_left'] = False
            _LOGGER.debug("Failed to set battery sensor for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set charger max ampere sensor
        try:
            self.vehicles[vehicle]['sensor_charge_max_ampere'] = int(data_emanager['EManager']['rbc']['settings']['chargerMaxCurrent'])
        except:
            _LOGGER.debug("Failed to set charger max ampere sensor for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set target temperatrue sensor
        try:
            self.vehicles[vehicle]['sensor_climat_target_temperature'] = int(data_emanager['EManager']['rpc']['settings']['targetTemperature'])
        except:
            _LOGGER.debug("Failed to set target temperature sensor for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set electric range sensor
        try:
            self.vehicles[vehicle]['sensor_electric_range_left'] = int(data_emanager['EManager']['rbc']['status']['electricRange'])
        except:
            self.vehicles[vehicle]['sensor_electric_range_left'] = False
            _LOGGER.debug("Failed to set target electric range sensor for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set charging time left sensor
        try:
            charging_time_left = int(data_emanager['EManager']['rbc']['status']['chargingRemaningHour']) * 60 * 60
            charging_time_left += int(data_emanager['EManager']['rbc']['status']['chargingRemaningMinute']) * 60
            self.vehicles[vehicle]['sensor_charging_time_left'] = charging_time_left
        except:
            self.vehicles[vehicle]['sensor_charging_time_left'] = False
            _LOGGER.debug("Failed to set charging time sensor for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set next service inspection sensor
        try:
            self.vehicles[vehicle]['sensor_next_service_inspection'] = data_details['vehicleDetails']['serviceInspectionData']
        except:
            _LOGGER.debug("Failed to set next service inspection sensor for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set distance sensor
        try:
            self.vehicles[vehicle]['sensor_distance'] = int(data_details['vehicleDetails']['distanceCovered'].replace('.', ''))
        except:
            _LOGGER.debug("Failed to set distance sensor for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set last connected sensor
        try:
            last_connected = data_details['vehicleDetails']['lastConnectionTimeStamp'][0] + ' ' + data_details['vehicleDetails']['lastConnectionTimeStamp'][1]
            datetime_object = datetime.strptime(last_connected, '%d.%m.%Y %H:%M')
            self.vehicles[vehicle]['last_connected'] = datetime_object
        except:
            _LOGGER.debug("Failed to set distance sensor for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set door locked sensor
        try:
            vehicle_locked = True
            lock_data = data_car['vehicleStatusData']['lockData']
            for lock in lock_data:
                if lock_data[lock] != 2:
                    vehicle_locked = False

            if vehicle_locked:
                self.vehicles[vehicle]['sensor_door_locked'] = 'yes'
            else:
                self.vehicles[vehicle]['sensor_door_locked'] = 'no'
        except:
            self.vehicles[vehicle]['sensor_door_locked'] = False
            _LOGGER.debug("Failed to set door locked sensor for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set parking lights sensor
        try:
            if data_car['vehicleStatusData']['carRenderData']['parkingLights'] == 2:
                self.vehicles[vehicle]['sensor_parking_lights'] = 'off'
            else:
                self.vehicles[vehicle]['sensor_parking_lights'] = 'on'
        except:
            self.vehicles[vehicle]['sensor_parking_lights'] = False
            _LOGGER.debug("Failed to set parking lights sensor for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set climate state
        try:
            if data_emanager['EManager']['rpc']['status']['climatisationState'] == 'OFF':
                self._set_state('climat', vehicle, False)
            else:
                self._set_state('climat', vehicle, True)
        except:
            _LOGGER.debug("Failed to set climat state for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set window heating state
        try:
            if data_emanager['EManager']['rpc']['status']['windowHeatingStateRear'] == 'OFF':
                self._set_state('melt', vehicle, False)
            else:
                self._set_state('melt', vehicle, True)
        except:
            _LOGGER.debug("Failed to set window heating state for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set charging state
        try:
            if data_emanager['EManager']['rbc']['status']['chargingState'] == 'OFF':
                self._set_state('charge', vehicle, False)
            else:
                self._set_state('charge', vehicle, True)
        except:
            _LOGGER.debug("Failed to set charging state for vehicle %s" % (self.vehicles[vehicle].get('vin')))



        _LOGGER.debug("New vehicle data: %s" % (self.vehicles[vehicle]))
        return True


    def _set_state(self, switch, vehicle, state = False):
        if switch == 'climat':
            self.vehicles[vehicle]['state_climat'] = state
        elif switch == 'charge':
            self.vehicles[vehicle]['state_charge'] = state
        elif switch == 'melt':
            self.vehicles[vehicle]['state_melt'] = state


    # switch functions
    def _switch_update_state(self, vehicle, switch, state = False):
        if switch == 'climat':
            if state:
                self._carnet_start_climat(vehicle)
            else:
                self._carnet_stop_climat(vehicle)
        elif switch == 'charge':
            if state:
                self._carnet_start_charge(vehicle)
            else:
                self._carnet_stop_charge(vehicle)
        elif switch == 'melt':
            if state:
                self._carnet_start_window_melt(vehicle)
            else:
                self._carnet_stop_window_melt(vehicle)

    def _switch_get_state(self, vehicle, switch):
        if switch == 'climat':
            return self.vehicles[vehicle]['state_climat']
        elif switch == 'charge':
            return self.vehicles[vehicle]['state_charge']
        elif switch == 'melt':
            return self.vehicles[vehicle]['state_melt']

    def _sensor_get_state(self, vehicle, sensor):
        state = None
        if sensor == 'battery':
            state = self.vehicles[vehicle]['sensor_battery_left']

        elif sensor == 'charge_max_ampere':
            state = self.vehicles[vehicle]['sensor_charge_max_ampere']

        elif sensor == 'external_power_connected':
            state = self.vehicles[vehicle]['sensor_external_power_connected']

        elif sensor == 'charging_time_left':
            # return minutes left instead of seconds
            state = int(round(self.vehicles[vehicle]['sensor_charging_time_left'] / 60))

        elif sensor == 'climat_target_temperature':
            state = self.vehicles[vehicle]['sensor_climat_target_temperature']

        elif sensor == 'electric_range_left':
            state = self.vehicles[vehicle]['sensor_electric_range_left']

        elif sensor == 'distance':
            state = self.vehicles[vehicle]['sensor_distance']

        elif sensor == 'last_update':
            datetime_object = self.vehicles[vehicle]['last_connected']
            if datetime_object:
                state = datetime_object.strftime("%Y-%m-%d %H:%M:%S")

        elif sensor == 'locked':
            state = self.vehicles[vehicle]['sensor_door_locked']

        elif sensor == 'parking_lights':
            state = self.vehicles[vehicle]['sensor_parking_lights']
        elif sensor == 'next_service_inspection':
            state = self.vehicles[vehicle]['sensor_next_service_inspection']

        if state:
            return state
        else:
            return None

