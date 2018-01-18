# -*- coding: utf-8 -*-
import re
import requests
import time
import logging


import voluptuous as vol
import homeassistant.helpers.config_validation as cv

from datetime import timedelta, datetime
from urllib.parse import urlsplit
from urllib.error import HTTPError
from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD)
from homeassistant.helpers import discovery
from homeassistant.helpers.event import track_point_in_utc_time
from homeassistant.util.dt import utcnow
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.icon import icon_for_battery_level


_LOGGER = logging.getLogger(__name__)

DOMAIN = 'volkswagen_carnet'
CARNET_DATA = "volkswagen_carnet"
REQUIREMENTS = ['requests']
CONF_UPDATE_INTERVAL = 'update_interval'

MIN_UPDATE_INTERVAL = timedelta(minutes=2)
DEFAULT_UPDATE_INTERVAL = timedelta(minutes=3)

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

    def update_vehicle(login_session, vehicle):
        """Update vehicle status from Volkswagen Carnet"""
        if not vw._carnet_update_vehicle_status(login_session, vehicle):
            _LOGGER.warning("Could not update vehicle %s" % (vehicle))
            return False
        else:
            return True

    def fetch_vehicles(login_session):
        """Fetch vehicles from Volkswagen Carnet"""
        vw._carnet_get_vehicles(login_session)

        if vw.vehicles:
            for component in ['switch', 'device_tracker', 'sensor', 'binary_sensor']:
                discovery.load_platform(hass, component, DOMAIN, vw.vehicles, config)

    def update(now):
        """Update status from Volkswagen Carnet"""
        try:
            login_session = vw._carnet_get_login_session()
            if not login_session:
                _LOGGER.error("Failed to login to Volkswagen Carnet")
                return False

            if not vw.vehicles:
                fetch_vehicles(login_session)
            else:
                for vehicle in vw.vehicles:
                    if not update_vehicle(login_session, vehicle):
                        return False

            vw._carnet_logout_session(login_session)
            del(login_session)
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
        self.update_timeout_counter = 60
        self.vehicles = {}

    def _vehicle_template(self, vin):
        vehicle_template = {
            'initialized': False,
            'vin': vin.get('vin'),
            'pin': vin.get('enrollmentPin'),
            'name': vin.get('vehicleName'),
            'model_year': False,
            'model_code': False,
            'model_image_url': False,
            'dashboard_url': False,
            'profile_id': False,
            'last_connected': False,
            'last_updated': False,
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
            'sensor_climat_without_hw_power': False,
            'sensor_climat_time_left': False,
        }
        return vehicle_template


    def _carnet_get_login_session(self):
        login_session = {
            'session': requests.Session(),
            'base': 'https://www.volkswagen-car-net.com',
            'headers': { 'Accept': 'application/json, text/plain, */*', 'Content-Type': 'application/json;charset=UTF-8', 'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0.1; D5803 Build/23.5.A.1.291; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/63.0.3239.111 Mobile Safari/537.36' },
            'auth_base': 'https://security.volkswagen.com',
            'auth_headers': {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8', 'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0.1; D5803 Build/23.5.A.1.291; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/63.0.3239.111 Mobile Safari/537.36'},
            'url': False
        }
        # login to carnet
        try:
            _LOGGER.debug("Trying to create login session")

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
            r = login_session['session'].get(login_session['base'] + '/portal/en_GB/web/guest/home')
            if r.status_code != 200:
                return ""
            csrf = extract_csrf(r)

            # Request login page and get CSRF
            login_session['auth_headers']['Referer'] = login_session['base'] + '/portal'
            login_session['auth_headers']["X-CSRF-Token"] = csrf
            r = login_session['session'].post(login_session['base'] + '/portal/web/guest/home/-/csrftokenhandling/get-login-url', headers = login_session['auth_headers'])
            if r.status_code != 200:
                return ""
            responseData = r.json()
            lg_url = responseData.get("loginURL").get("path")

            # no redirect so we can get values we look for
            r = login_session['session'].get(lg_url, allow_redirects = False, headers = login_session['auth_headers'])
            if r.status_code != 302:
                return ""
            ref_url = r.headers.get("location")

            # now get actual login page and get session id and ViewState
            r = login_session['session'].get(ref_url, headers = login_session['auth_headers'])
            if r.status_code != 200:
                return ""
            view_state = extract_view_state(r)

            # Login with user details
            login_session['auth_headers']["Faces-Request"] = "partial/ajax"
            login_session['auth_headers']["Referer"] = ref_url
            login_session['auth_headers']["X-CSRF-Token"] = ''

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

            r = login_session['session'].post(login_session['auth_base'] + '/ap-login/jsf/login.jsf', data=post_data, headers = login_session['auth_headers'])
            if r.status_code != 200:
                return ""
            ref_url = extract_redirect_url(r).replace('&amp;', '&')

            # redirect to link from login and extract state and code values
            r = login_session['session'].get(ref_url, allow_redirects=False, headers = login_session['auth_headers'])
            if r.status_code != 302:
                return ""
            ref_url2 = r.headers.get("location")

            code = extract_code(ref_url2)
            state = extract_state(ref_url2)

            # load ref page
            r = login_session['session'].get(ref_url2, headers = login_session['auth_headers'])
            if r.status_code != 200:
                return ""

            login_session['auth_headers']["Faces-Request"] = ""
            login_session['auth_headers']["Referer"] = ref_url2
            post_data = {
                '_33_WAR_cored5portlet_code': code,
                '_33_WAR_cored5portlet_landingPageUrl': ''
            }
            r = login_session['session'].post(login_session['base'] + urlsplit(ref_url2).path + '?p_auth=' + state + '&p_p_id=33_WAR_cored5portlet&p_p_lifecycle=1&p_p_state=normal&p_p_mode=view&p_p_col_id=column-1&p_p_col_count=1&_33_WAR_cored5portlet_javax.portlet.action=getLoginStatus', data = post_data, allow_redirects = False, headers = login_session['auth_headers'])
            if r.status_code != 302:
                return ""

            ref_url3 = r.headers.get("location")
            r = login_session['session'].get(ref_url3, headers=login_session['auth_headers'])

            # We have a new CSRF
            csrf = extract_csrf(r)

            # Update headers for requests
            login_session['headers']["Referer"] = ref_url3
            login_session['headers']["X-CSRF-Token"] = csrf
            login_session['url'] = ref_url3
            _LOGGER.debug("Login session created")
            return login_session

        except HTTPError as e:
            _LOGGER.error("Unable to create login session")
            _LOGGER.debug("Error msg: %s" % (e))
            return False

    def _carnet_logout_session(self, session):
        self._carnet_post_session(session, '/-/logout/revoke')
        self.session = None
        _LOGGER.debug("Logout from session")

    def _carnet_post_session(self, session, command):
        req = session['session'].post(session['url'] + command, headers = session['headers'])
        return req.json()
        #return req.content

    def _carnet_post_action_session(self, session, command, data):
        req = session['session'].post(session['url'] + command, json = data, headers = session['headers'])
        return req.json()
        #return req.content

    def _carnet_get_owners_verification(self, session):
        url = session['base'] + '/portal/group/se/edit-profile/-/profile/get-vehicles-owners-verification'
        req = session['session'].post(url, headers = session['headers'])
        return req.json()

    def _carnet_post_vehicle(self, session, vehicle, command):
        req = session['session'].post(session['base'] + self.vehicles[vehicle].get('dashboard_url') + command, headers = session['headers'])
        return req.json()

    def _carnet_post_action_vehicle(self, vehicle, command, data):
        # create login session for each action
        login_session = self._carnet_get_login_session()
        if not login_session:
            _LOGGER.error('Could not create login session.')
            return False
        req = login_session['session'].post(login_session['base'] + self.vehicles[vehicle].get('dashboard_url') + command, json=data, headers = login_session['headers'])
        self._carnet_logout_session(login_session)
        del(login_session)
        return req.json()

    def _carnet_start_charge(self, vehicle):
        self._set_state('charge', vehicle, True)
        post_data = {
            'triggerAction': True,
            'batteryPercent': '100'
        }
        return self._carnet_post_action_vehicle(vehicle, '/-/emanager/charge-battery', post_data)

    def _carnet_stop_charge(self, vehicle):
        self._set_state('charge', vehicle, False)
        post_data = {
            'triggerAction': False,
            'batteryPercent': '99'
        }
        return self._carnet_post_action_vehicle(vehicle, '/-/emanager/charge-battery', post_data)


    def _carnet_start_climat(self, vehicle):
        self._set_state('climat', vehicle, True)
        post_data = {
            'triggerAction': True,
            'electricClima': True
        }
        return self._carnet_post_action_vehicle(vehicle, '/-/emanager/trigger-climatisation', post_data)


    def _carnet_stop_climat(self, vehicle):
        self._set_state('climat', vehicle, False)
        post_data = {
            'triggerAction': False,
            'electricClima': True
        }
        return self._carnet_post_action_vehicle(vehicle, '/-/emanager/trigger-climatisation', post_data)

    def _carnet_start_window_melt(self, vehicle):
        self._set_state('melt', vehicle, True)
        post_data = {
            'triggerAction': True
        }
        return self._carnet_post_action_vehicle(vehicle, '/-/emanager/trigger-windowheating', post_data)

    def _carnet_stop_window_melt(self, vehicle):
        self._set_state('melt', vehicle, False)
        post_data = {
            'triggerAction': False
        }
        return self._carnet_post_action_vehicle(vehicle, '/-/emanager/trigger-windowheating', post_data)

    def _carnet_get_vehicles(self, session):
        _LOGGER.debug('Fetching vehicles from Volkswagen Carnet')
        # get vehicles
        try:
            data_owner_verification = self._carnet_get_owners_verification(session)
            for vehicle in data_owner_verification['vehiclesForEnrollmentResponseList']:
                self.vehicles[vehicle.get('vin')] = self._vehicle_template(vehicle)
                _LOGGER.debug('Adding vehicle: %s' % (vehicle.get('vin')))

            # add extra information
            non_loaded_cars = self._carnet_post_session(session, '/-/mainnavigation/get-fully-loaded-cars')
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

        # fetch vehicle status
        for vehicle in self.vehicles:
            self._carnet_update_vehicle_status(session, vehicle)

    def _carnet_update_vehicle_status(self, session, vehicle):
        _LOGGER.debug("Trying to update status for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        try:
            # request car update
            self._carnet_post_vehicle(session, vehicle, '/-/vsr/request-vsr')


            if self.vehicles[vehicle].get('initialized'):
                # wait for update to be completed:
                timeout_counter = 0
                msg_waiting_request = False
                while True:
                    timeout_counter += 1
                    time.sleep(1)

                    if timeout_counter > self.update_timeout_counter:
                        _LOGGER.debug("Failed to fetch latest status from vehicle %s, request timed out." % (self.vehicles[vehicle].get('vin')))
                        break

                    request_status = self._carnet_post_vehicle(session,vehicle, '/-/vsr/get-vsr')['vehicleStatusData']['requestStatus']
                    if request_status == 'REQUEST_IN_PROGRESS':
                        if not msg_waiting_request:
                            _LOGGER.debug("Waiting for update request from vehicle %s" % (self.vehicles[vehicle].get('vin')))
                            msg_waiting_request = True
                        continue
                    elif request_status == 'ERROR':
                        _LOGGER.debug("Failed to fetch latest status from vehicle %s" % (self.vehicles[vehicle].get('vin')))
                        break
                    else:
                        continue
            else:
                self.vehicles[vehicle]['initialized'] = True

            # get data from carnet
            data_emanager = self._carnet_post_vehicle(session, vehicle, '/-/emanager/get-emanager')
            data_location = self._carnet_post_vehicle(session, vehicle, '/-/cf/get-location')
            data_details = self._carnet_post_vehicle(session, vehicle,'/-/vehicle-info/get-vehicle-details')
            data_car = self._carnet_post_vehicle(session, vehicle, '/-/vsr/get-vsr')
            _LOGGER.debug("Status updated for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        except HTTPError as e:
            _LOGGER.error("Failed to fetch status for vehicle %s" % (self.vehicles[vehicle].get('vin')))
            _LOGGER.debug("Error msg: %s" % (e))
            self.carnet_logged_in = False
            return False

        # set new last updated
        self.vehicles[vehicle]['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # set new location data
        try:
            self.vehicles[vehicle]['location_latitude'] = data_location['position']['lat']
            self.vehicles[vehicle]['location_longitude'] = data_location['position']['lng']
        except:
            _LOGGER.debug("Failed to set location status for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set powersupply sensor
        try:
            if data_emanager['EManager']['rbc']['status']['extPowerSupplyState'] == 'UNAVAILABLE':
                self.vehicles[vehicle]['sensor_external_power_connected'] = False
            else:
                self.vehicles[vehicle]['sensor_external_power_connected'] = True
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

        # set climat without external power sensor
        try:
            if data_emanager['EManager']['rpc']['settings']['climatisationWithoutHVPower']:
                self.vehicles[vehicle]['sensor_climat_without_hw_power'] = True
            else:
                self.vehicles[vehicle]['sensor_climat_without_hw_power'] = False
        except:
            _LOGGER.debug("Failed to set climat without hw power sensor for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set climat time left sensor
        try:
            self.vehicles[vehicle]['sensor_climat_time_left'] = int(data_emanager['EManager']['rpc']['status']['climatisationRemaningTime'])
        except:
            self.vehicles[vehicle]['sensor_climat_time_left'] = False
            _LOGGER.debug("Failed to set climat time left sensor for vehicle %s" % (self.vehicles[vehicle].get('vin')))

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
            # only show chargint time left if vehicle is charging
            if self.vehicles[vehicle]['state_charge']:
                self.vehicles[vehicle]['sensor_charging_time_left'] = charging_time_left
            else:
                self.vehicles[vehicle]['sensor_charging_time_left'] = False
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
            self.vehicles[vehicle]['last_connected'] = datetime_object.strftime("%Y-%m-%d %H:%M:%S")
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
                self.vehicles[vehicle]['sensor_door_locked'] = True
            else:
                self.vehicles[vehicle]['sensor_door_locked'] = False
        except:
            self.vehicles[vehicle]['sensor_door_locked'] = False
            _LOGGER.debug("Failed to set door locked sensor for vehicle %s" % (self.vehicles[vehicle].get('vin')))

        # set parking lights sensor
        try:
            if data_car['vehicleStatusData']['carRenderData']['parkingLights'] == 2:
                self.vehicles[vehicle]['sensor_parking_lights'] = False
            else:
                self.vehicles[vehicle]['sensor_parking_lights'] = True
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
                _LOGGER.debug("Starting climatisation on vehicle %s" % (self.vehicles[vehicle].get('vin')))
                self._carnet_start_climat(vehicle)
            else:
                _LOGGER.debug("Stopping climatisation on vehicle %s" % (self.vehicles[vehicle].get('vin')))
                self._carnet_stop_climat(vehicle)
        elif switch == 'charge':
            if state:
                _LOGGER.debug("Starting charge on vehicle %s" % (self.vehicles[vehicle].get('vin')))
                self._carnet_start_charge(vehicle)
            else:
                _LOGGER.debug("Stopping charge on vehicle %s" % (self.vehicles[vehicle].get('vin')))
                self._carnet_stop_charge(vehicle)
        elif switch == 'melt':
            if state:
                _LOGGER.debug("Starting window heating on vehicle %s" % (self.vehicles[vehicle].get('vin')))
                self._carnet_start_window_melt(vehicle)
            else:
                _LOGGER.debug("Stopping window heating on vehicle %s" % (self.vehicles[vehicle].get('vin')))
                self._carnet_stop_window_melt(vehicle)

    def _switch_get_state(self, vehicle, switch):
        if switch == 'climat':
            return self.vehicles[vehicle]['state_climat']
        elif switch == 'charge':
            return self.vehicles[vehicle]['state_charge']
        elif switch == 'melt':
            return self.vehicles[vehicle]['state_melt']


class VolkswagenCarnetEntity(Entity):
    """Representation of a Sensor."""

    def __init__(self, hass, vehicle, sensor):
        """Initialize the sensor."""
        self.vw = hass.data[CARNET_DATA]
        self.hass = hass
        self.sensor = sensor
        self.vehicle = vehicle

    @property
    def _attr(self):
        return self.sensor.get('attr')

    @property
    def _get_vehicle_name(self):
        return self.vehicle

    @property
    def _get_vehicle_data(self):
        return self.vw.vehicles[self.vehicle]

    @property
    def _state(self):
        state = None
        if self._sensor_name == 'battery':
            state = self._get_vehicle_data['sensor_battery_left']

        elif self._sensor_name == 'charge_max_ampere':
            state = self._get_vehicle_data['sensor_charge_max_ampere']

        elif self._sensor_name == 'charging_time_left':
            # return minutes left instead of seconds
            state = int(round(self._get_vehicle_data['sensor_charging_time_left'] / 60))

        elif self._sensor_name == 'climat_target_temperature':
            state = self._get_vehicle_data['sensor_climat_target_temperature']

        elif self._sensor_name == 'electric_range_left':
            state = self._get_vehicle_data['sensor_electric_range_left']

        elif self._sensor_name == 'distance':
            state = self._get_vehicle_data['sensor_distance']

        elif self._sensor_name == 'last_connected':
            state = self._get_vehicle_data['last_connected']

        elif self._sensor_name == 'next_service_inspection':
            state = self._get_vehicle_data['sensor_next_service_inspection']

        if state:
            return state
        else:
            return None

    @property
    def _sensor_name(self):
        return self.sensor.get('name')

    @property
    def _last_updated(self):
        """Return the last update of a device."""
        last_updated = self.vw.vehicles[self.vehicle].get('last_updated')
        if last_updated:
            return last_updated
        else:
            return None

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'vw_%s_%s' % (self.vehicle, self._sensor_name)

    @property
    def icon(self):
        """Return the icon."""
        if self._sensor_name == 'battery':
            return icon_for_battery_level(battery_level=int(self._state), charging = self._get_vehicle_data['state_charge'])
        else:
            return self.sensor.get('icon')

    @property
    def hidden(self):
        """Return True if the entity should be hidden from UIs."""
        return self.sensor.get('hidden')

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {}
        if self._last_updated:
            attrs['time_last_updated'] = self._last_updated
        # add extra attributes
        attrs.update(self._attr)
        if self._sensor_name == 'battery' and self._get_vehicle_data['sensor_battery_left']:
            attrs['battery_level'] = self._get_vehicle_data['sensor_battery_left']
            attrs['battery_icon'] = 'mdi:battery'
        return attrs


