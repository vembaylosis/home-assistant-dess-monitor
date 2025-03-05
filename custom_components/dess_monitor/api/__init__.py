import hashlib
import time
import urllib

import aiohttp


async def auth_user(username, password_hash):
    async with aiohttp.ClientSession() as session:
        # print('auth_user', username)
        params = {
            'action': 'authSource',
            'usr': username,
            'source': '1',
            'company-key': 'bnrl_frRFjEz8Mkn',
        }
        qs = urllib.parse.urlencode(params, doseq=False, safe='@')
        salt = int(time.time())
        sign = hashlib.sha1(f'{salt}{password_hash}&{qs}'.encode()).hexdigest()
        payload = {
            'sign': sign,
            'salt': salt,
            **params,
        }
        url = f'https://web.dessmonitor.com/public/?{urllib.parse.urlencode(payload, doseq=False, safe="@")}'
        response = (await (await session.get(url)).json())
        if response['err'] != 0:
            print(f'Error {response["err"]} while authenticating user: {response["desc"]}')
            raise Exception(
                f'ErrorAuthFailed'
            )
        data = response['dat']
        return {
            'token': data['token'],
            'secret': data['secret'],
            'expire': data['expire'],
            'uid': data['uid'],
            'usr': data['usr'],
        }


def generate_signature(salt, secret, token, params):
    qs = urllib.parse.urlencode(params, doseq=False, safe='@')
    return hashlib.sha1(f'{salt}{secret}{token}&{qs}'.encode()).hexdigest()


def generate_params_signature(token, secret, params):
    salt = int(time.time())
    return {
        'sign': generate_signature(salt, secret, token, params),
        'salt': salt,
        'token': token,
        **params,
    }


async def create_auth_api_request(token, secret, params):
    async with aiohttp.ClientSession() as session:
        payload = generate_params_signature(token, secret, params)
        # print(payload)
        params_path = urllib.parse.urlencode(payload, doseq=False, safe="@")
        url = f'https://web.dessmonitor.com/public/?{params_path}'
        json = (await (await session.get(url)).json())
        if json['err'] == 0:
            return json['dat']
        else:
            raise Exception(
                f'Error {json["err"]} while creating auth api request: {json["desc"]}'
            )


async def get_devices(token, secret, params=None):
    if params is None:
        params = {}
    payload = {
        'action': 'webQueryDeviceEs',
        'i18n': 'en_US',
        'source': '1',
        'page': '0',
        'pagesize': '15',
        # 'status': '0',
        **params,
    }
    devices_response = await create_auth_api_request(token, secret, payload)

    return devices_response['device']


def extract_device_identity(device):
    return {
        'devaddr': device['devaddr'],
        'devcode': device['devcode'],
        'pn': device['pn'],
        'sn': device['sn'],
    }


async def get_device_energy_flow(token, secret, device_identity):
    payload = {
        'action': 'webQueryDeviceEnergyFlowEs',
        'i18n': 'en_US',
        'source': '1',
        **extract_device_identity(device_identity)
    }
    response = await create_auth_api_request(token, secret, payload)

    return response


async def get_device_last_data(token, secret, device_identity):
    payload = {
        'action': 'querySPDeviceLastData',
        'i18n': 'en_US',
        'source': '1',
        **extract_device_identity(device_identity)
    }
    response = await create_auth_api_request(token, secret, payload)

    return response


async def get_device_pars(token, secret, device_identity):
    payload = {
        'action': 'queryDeviceParsEs',
        'i18n': 'en_US',
        'source': '1',
        **extract_device_identity(device_identity)
    }
    response = await create_auth_api_request(token, secret, payload)

    return response


async def get_device_ctrl_value(token, secret, device_identity, id):
    payload = {
        'action': 'queryDeviceCtrlValue',
        'i18n': 'en_US',
        'source': '1',
        'id': id,
        **extract_device_identity(device_identity),
    }
    response = await create_auth_api_request(token, secret, payload)

    return response


async def get_device_ctrl_fields(token, secret, device_identity):
    payload = {
        'action': 'queryDeviceCtrlField',
        'i18n': 'en_US',
        'source': '1',
        'id': id,
        **extract_device_identity(device_identity),
    }
    response = await create_auth_api_request(token, secret, payload)

    return response


async def get_collectors(token, secret, params):
    payload = {
        'action': 'webQueryCollectorsEs',
        'source': '1',
        'devtype': '2304',
        'page': '0',
        'pagesize': '15',
        **params,
    }
    response = await create_auth_api_request(token, secret, payload)

    return response
