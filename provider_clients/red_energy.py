import json
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from pydantic import BaseModel, RootModel

TOKEN_FILE = 'token_info.json'


class Interval(BaseModel):
    intervalStart: str
    primaryConsumptionTariffComponent: str
    consumptionKwh: float
    consumptionDollarIncGst: float
    generationKwh: float
    generationDollar: float
    demandDetail: Optional[None] = None
    isPricingReliable: bool
    pricingUnavailabilityReasons: List
    isPricingAvailable: bool


class UsageData(BaseModel):
    usageDate: str
    halfHours: List[Interval]
    maxDemandDetail: Optional[None] = None
    carbonEmissionTonne: float
    minTemperatureC: float
    maxTemperatureC: float
    isPricingReliable: bool
    numUnreliablyPricedIntervals: int
    quality: str
    pricingUnavailabilityReasons: List
    hasUnpricedUsage: bool
    numUnpricedIntervals: int


UsageDataArray = RootModel[List[UsageData]]


def days_ago(days: int) -> str:
    # Get today's date
    today = datetime.today()

    # Subtract one day to get yesterday's date
    target_date = today - timedelta(days=days)

    # Convert to ISO format (YYYY-MM-DD)
    return target_date.isoformat()[:10]


def load_token() -> dict:
    try:
        with open(TOKEN_FILE, 'r') as file:
            token_info = json.load(file)
            token_info['expires_at'] = datetime.fromisoformat(token_info['expires_at'])
            return token_info
    except FileNotFoundError:
        return {
            'access_token': '',
            'refresh_token': '',
            'expires_in': 0,
            'expires_at': datetime.min
        }


def save_token(token_info: dict) -> None:
    token_info['expires_at'] = (datetime.now() + timedelta(seconds=token_info['expires_in'])).isoformat()
    with open(TOKEN_FILE, 'w') as file:
        json.dump(token_info, file)


def is_token_expired(token_info: dict) -> bool:
    return datetime.now() >= token_info['expires_at']


def refresh_token(refresh_token: str, client_id: str) -> dict:
    url = 'https://login.redenergy.com.au/oauth2/default/v1/token'
    body = {
        'refresh_token': refresh_token,
        'client_id': client_id,
        'grant_type': 'refresh_token'
    }
    response = requests.post(url, data=body)
    return response.json()


def get_authenticated_data(consumer_number: str = '', from_date: str = '2024-07-17',
                           to_date: str = '2024-07-18',
                           correlation_id: str = '') -> dict:
    token_info = load_token()
    if not token_info or is_token_expired(token_info):
        token_info = refresh_token(token_info['refresh_token'], '0oa1apu62kkqeet4C3l7')
        save_token(token_info)

    headers = {
        'Host': 'selfservice.services.retail.energy',
        'Accept': '*/*',
        'X-Self-Service-Correlation-ID': correlation_id,
        'User-Agent': 'RedEnergy/1.5 (au.com.redenergy.app; build:614; iOS 17.5.1) Alamofire/5.9.0',
        'Accept-Language': 'en-AU;q=1.0, es-MX;q=0.9',
        'Authorization': f"Bearer {token_info['access_token']}",
        'X-Self-Service-Client-ID': 'ios-red'
    }
    url = f"https://selfservice.services.retail.energy/v1/usage/interval?consumerNumber={consumer_number}&fromDate={from_date}&toDate={to_date}"
    response = requests.get(url, headers=headers)
    response_json = response.json()
    save_response_to_disk(response_json)
    return response_json


def save_response_to_disk(data: dict, filename: str = 'response.json') -> None:
    with open(filename, 'w') as file:
        json.dump(data, file)


def get_most_recent_data() -> None:
    key_date = days_ago(1)
    res = get_authenticated_data(from_date=key_date, to_date=key_date)
    uda = UsageDataArray(res)
    print(f"Data from: {uda.root[0]['usageDate']} - {len(uda.root[0]['halfHours'])}")

# Example usage
# get_authenticated_data()
# Example usage
# data = UsageDataArray.parse_obj(json_data)
