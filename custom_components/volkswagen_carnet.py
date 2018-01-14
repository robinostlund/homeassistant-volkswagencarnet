import re
import requests
import json
import time
import logging

from datetime import timedelta


import voluptuous as vol
import homeassistant.helpers.config_validation as cv


from urllib.parse import urlsplit,urlsplit
from urllib.error import HTTPError

from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD)
from homeassistant.util import Throttle
from homeassistant.helpers import discovery



_LOGGER = logging.getLogger(__name__)


SCAN_INTERVAL = timedelta(seconds=20)
DOMAIN = 'volkswagen_carnet'
CARNET_DATA = "volkswagen_carnet"
REQUIREMENTS = ['requests']
SLOW_UPDATE_WARNING = 20


CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,

    }),
}, extra = vol.ALLOW_EXTRA)


def setup(hass, config):
    """Setup Volkswagen Carnet component"""

    carnet_config = config.get(DOMAIN, {})
    username = carnet_config.get(CONF_USERNAME)
    password = carnet_config.get(CONF_PASSWORD)


    # Store data
    hass.data[CARNET_DATA] = VWCarnet(hass, username, password)
    vw = hass.data[CARNET_DATA]

    if not vw._carnet_login():
        _LOGGER.error("Failed to login to Volkswagen Carnet")
        return False

    vw._carnet_update_status()

    for component in ['switch', 'device_tracker']:
        discovery.load_platform(hass, component, DOMAIN, {}, config)

    return vw.carnet_logged_in


class VWCarnet(object):
    def __init__(self, hass, username, password):
        self.hass = hass
        self.carnet_username = username
        self.carnet_password = password

        self.carnet_logged_in = False
        self.carnet_updates_in_progress = False

        self.vehicles = {} # adding support in case we need to have support for multiple cars lateron
        self.vehicle_data = {
            'name': 'vehicle01',
            'state_charge': False,
            'state_climat': False,
            'state_melt': False,
            'latitude': False,
            'longitude': False,
            'sensor_battery_left': False,
            'sensor_charge_max_ampere': False,
            'sensor_external_power_connected': False,
            'sensor_charging_time_left': False,
            'sensor_climat_target_temperature': False,
            'sensor_electric_range_left': False,
        }
        self.vehicles['vehicle01'] = self.vehicle_data
        self.vehicle_current = 'vehicle01'

        # Fake the VW CarNet mobile app headers
        self.headers = { 'Accept': 'application/json, text/plain, */*', 'Content-Type': 'application/json;charset=UTF-8', 'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0.1; D5803 Build/23.5.A.1.291; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/63.0.3239.111 Mobile Safari/537.36' }
        self.session = requests.Session()
        self.timeout_counter = 30 # seconds

    def _carnet_login(self):
        # login to carnet
        try:
            _LOGGER.debug("Trying to login to Volkswagen Carnet")
            AUTHHEADERS = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
                'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0.1; D5803 Build/23.5.A.1.291; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/63.0.3239.111 Mobile Safari/537.36'}

            auth_base = "https://security.volkswagen.com"
            base = "https://www.volkswagen-car-net.com"

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
            r = self.session.get(base + '/portal/en_GB/web/guest/home')
            if r.status_code != 200:
                return ""
            csrf = extract_csrf(r)

            # Request login page and get CSRF
            AUTHHEADERS["Referer"] = base + '/portal'
            AUTHHEADERS["X-CSRF-Token"] = csrf
            r = self.session.post(base + '/portal/web/guest/home/-/csrftokenhandling/get-login-url', headers=AUTHHEADERS)
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
            r = self.session.post(base + urlsplit(
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
            return True

        except HTTPError:
            _LOGGER.error("Unable to login to Volkswagen CarNet")
            return False


    def _carnet_post(self, command):
        if not self.carnet_logged_in:
            self._carnet_login()
        if not self.carnet_logged_in:
            _LOGGER.error('Couldnt do action. There was a problem with the login.')
        req = self.session.post(self.url + command, headers = self.headers)
        return req.content

    def _carnet_post_action(self, command, data):
        if not self.carnet_logged_in:
            self._carnet_login()
        if not self.carnet_logged_in:
            _LOGGER.error('Couldnt do action. There was a problem with the login.')
        req = self.session.post(self.url + command, json = data, headers = self.headers)
        return req.content

    def _carnet_start_charge(self, vehicle):
        _LOGGER.debug("Trying to start charging")
        self._set_state_charge(vehicle, True)
        post_data = {
            'triggerAction': True,
            'batteryPercent': '100'
        }
        return json.loads(self._carnet_post_action('/-/emanager/charge-battery', post_data))

    def _carnet_stop_charge(self, vehicle):
        _LOGGER.debug("Trying to stop charging")
        self._set_state_charge(vehicle, False)
        post_data = {
            'triggerAction': False,
            'batteryPercent': '99'
        }
        return json.loads(self._carnet_post_action('/-/emanager/charge-battery', post_data))


    def _carnet_start_climat(self, vehicle):
        _LOGGER.debug("Trying to start climat")
        self._set_state_climat(vehicle, True)
        post_data = {
            'triggerAction': True,
            'electricClima': True
        }
        return json.loads(self._carnet_post_action('/-/emanager/trigger-climatisation', post_data))


    def _carnet_stop_climat(self, vehicle):
        _LOGGER.debug("Trying to stop climat")
        self._set_state_climat(vehicle, False)
        post_data = {
            'triggerAction': False,
            'electricClima': True
        }
        return json.loads(self._carnet_post_action('/-/emanager/trigger-climatisation', post_data))

    def _carnet_start_window_melt(self, vehicle):
        _LOGGER.debug("Trying to start window melt")
        self._set_state_melt(vehicle, True)
        post_data = {
            'triggerAction': True
        }
        return json.loads(self._carnet_post_action('/-/emanager/trigger-windowheating', post_data))

    def _carnet_stop_window_melt(self, vehicle):
        _LOGGER.debug("Trying to stop window melt")
        self._set_state_melt(vehicle, False)
        post_data = {
            'triggerAction': False
        }
        return json.loads(self._carnet_post_action('/-/emanager/trigger-windowheating', post_data))

    @Throttle(timedelta(seconds=10))
    def _carnet_update_status(self):
        if self.carnet_updates_in_progress:
            _LOGGER.debug("Volkswagen Carnet updates already in progress")
            return

        self.carnet_updates_in_progress = True
        _LOGGER.debug("Trying to update status from Volkswagen Carnet")
        try:
            # request car data
            self._carnet_post('/-/vsr/request-vsr')

            # wait for update to be completed:
            request_status = json.loads(self._carnet_post('/-/vsr/get-vsr'))
            timeout_counter = 0
            while request_status['vehicleStatusData']['requestStatus'] == 'REQUEST_IN_PROGRESS':
                request_status = json.loads(self._carnet_post('/-/vsr/get-vsr'))
                timeout_counter += 1
                time.sleep(1)
                if timeout_counter > 30:
                    raise ('Could not get status in time')


            # parse data
            data_emanager = json.loads(self._carnet_post('/-/emanager/get-emanager'))
            data_location = json.loads(self._carnet_post('/-/cf/get-location'))

            # set new location data
            latitude = data_location['position']['lat']
            longitude = data_location['position']['lng']
            self.vehicles[self.vehicle_current]['latitude'] = latitude
            self.vehicles[self.vehicle_current]['longitude'] = longitude

            # set new values
            self.vehicles[self.vehicle_current]['sensor_battery_left'] = int(data_emanager['EManager']['rbc']['status']['batteryPercentage'])
            self.vehicles[self.vehicle_current]['sensor_charge_max_ampere'] = int(data_emanager['EManager']['rbc']['settings']['chargerMaxCurrent'])
            self.vehicles[self.vehicle_current]['sensor_external_power_connected'] = int(data_emanager['EManager']['rbc']['status']['extPowerSupplyState'])
            self.vehicles[self.vehicle_current]['sensor_climat_target_temperature'] = int(data_emanager['EManager']['rpc']['settings']['targetTemperature'])
            self.vehicles[self.vehicle_current]['sensor_electric_range_left'] = int(data_emanager['EManager']['rbc']['status']['electricRange']) * 10

            # calculate charging time left
            charging_time_left = int(data_emanager['EManager']['rbc']['status']['chargingRemaningHour']) * 60 * 60
            charging_time_left += int(data_emanager['EManager']['rbc']['status']['chargingRemaningMinute']) * 60
            self.vehicles[self.vehicle_current]['sensor_charging_time_left'] = charging_time_left

            # update states
            if data_emanager['EManager']['rpc']['status']['climatisationState'] == 'OFF':
                self._set_state_climat(self.vehicle_current, False)
            else:
                self._set_state_climat(self.vehicle_current, True)

            if data_emanager['EManager']['rpc']['status']['windowHeatingStateRear'] == 'OFF':
                self._set_state_melt(self.vehicle_current, False)
            else:
                self._set_state_melt(self.vehicle_current, True)

            if data_emanager['EManager']['rbc']['status']['chargingState'] == 'OFF':
                self._set_state_charge(self.vehicle_current, False)
            else:
                self._set_state_charge(self.vehicle_current, True)
            _LOGGER.debug("Status updated from Volkswagen Carnet")
            self.carnet_updates_in_progress = False
            return True
        except:
            _LOGGER.error("Failed to update status from Volkswagen Carnet")
            self.carnet_updates_in_progress = False
            return False

    def _set_state_charge(self, vehicle, state = False):
        self.vehicles[vehicle]['state_charge'] = state

    def _set_state_melt(self, vehicle, state = False):
        self.vehicles[vehicle]['state_melt'] = state

    def _set_state_climat(self, vehicle, state = False):
        self.vehicles[vehicle]['state_climat'] = state

    def _switch_set_state(self, vehicle, switch, state = False):
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





