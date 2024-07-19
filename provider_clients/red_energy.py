import json
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from pydantic import BaseModel, RootModel

CUSTOMER_DATA_JSON = 'customer_data.json'
TOKEN_DATA_JSON = 'token_info.json'


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


class Customer(BaseModel):
    consumer_number: str
    connection_date: str


class Request(BaseModel):
    correlation_id: str
    user_agent: str
    self_service_client_id: str


class OAuthConfig(BaseModel):
    client_id: str
    grant_type: str
    refresh_endpoint: str


class Credentials(BaseModel):
    refresh_token: str


class CustomerData(BaseModel):
    customer: Customer
    credentials: Credentials
    request: Request
    oauth: OAuthConfig

    @staticmethod
    def load_from_disk(filname: str) -> 'CustomerData':
        try:
            with open(filname, 'r') as file:
                raw_customer_data = json.load(file)
                return CustomerData(**raw_customer_data)
        except FileNotFoundError:
            raise Exception("No customer data found")


class RawTokenData(BaseModel):
    token_type: str
    access_token: str
    scope: str
    id_token: str
    expires_in: int
    refresh_token: str


class ActiveTokenData(BaseModel):
    token_type: str
    access_token: str
    id_token: str
    scope: str
    expires_at: datetime

    def is_expired(self) -> bool:
        return datetime.now() >= self.expires_at

    @staticmethod
    def from_raw(raw_token_data: RawTokenData) -> 'ActiveTokenData':
        return ActiveTokenData(**{
            'token_type': raw_token_data.token_type,
            'access_token': raw_token_data.access_token,
            'id_token': raw_token_data.id_token,
            'scope': raw_token_data.scope,
            'expires_at': datetime.now() + timedelta(seconds=raw_token_data.expires_in)
        })

    @staticmethod
    def load_from_disk(filename: str) -> 'ActiveTokenData':
        try:
            with open(filename, 'r') as file:
                token_info = json.load(file)
                token_info['expires_at'] = datetime.fromisoformat(token_info['expires_at'])

                return ActiveTokenData(**token_info)
        except FileNotFoundError:
            return ActiveTokenData(**{
                'token_type': 'Bearer',
                'access_token': '',
                'id_token': '',
                'scope': '',
                'expires_at': datetime.min,
            })


class RefreshData(BaseModel):
    credentials: Credentials
    config: OAuthConfig

    def url(self) -> str:
        return self.config.refresh_endpoint

    def payload(self) -> dict:
        return {
            'refresh_token': self.credentials.refresh_token,
            'client_id': self.config.client_id,
            'grant_type': self.config.grant_type,
        }


class TokenData(BaseModel):
    active_token_data: ActiveTokenData
    refresh_data: RefreshData

    def auth_header(self) -> dict:
        return {
            'Authorization': self.auth_header_value()
        }

    def auth_header_value(self) -> str:
        return f"{self.active_token_data.token_type} {self.access_token()}"

    def access_token(self) -> str:
        if self.is_expired():
            self.refresh_auth_token()

        return self.active_token_data.access_token

    def refresh_auth_token(self) -> None:
        try:
            response = requests.post(self.refresh_data.url(), data=self.refresh_data.payload())
        except requests.exceptions.RequestException as e:
            print(f"Failed to refresh token: {e}")
            raise e

        raw_token_data = RawTokenData(**response.json())
        self.active_token_data = ActiveTokenData.from_raw(raw_token_data)
        if self.refresh_data.credentials.refresh_token != raw_token_data.refresh_token:
            print(f"Warning: Refresh token has changed - new token: {raw_token_data.refresh_token}")
            self.refresh_data.credentials.refresh_token = raw_token_data.refresh_token

    def is_expired(self) -> bool:
        return self.active_token_data.is_expired()

    def save_to_disk(self, filename: str) -> None:
        with open(filename, 'w') as file:
            file.write(self.active_token_data.model_dump_json())


def days_ago(days: int) -> str:
    # Get today's date
    today = datetime.today()

    # Subtract one day to get yesterday's date
    target_date = today - timedelta(days=days)

    # Convert to ISO format (YYYY-MM-DD)
    return target_date.isoformat()[:10]


def get_authenticated_data(
        from_date: str = '2024-07-17',
        to_date: str = '2024-07-18',
) -> dict:
    customer_info = CustomerData.load_from_disk(CUSTOMER_DATA_JSON)

    refresh_data = RefreshData(credentials=customer_info.credentials, config=customer_info.oauth)
    active_token_data = ActiveTokenData.load_from_disk(TOKEN_DATA_JSON)
    token_data = TokenData(refresh_data=refresh_data, active_token_data=active_token_data)

    headers = {
                  'Host': 'selfservice.services.retail.energy',
                  'Accept': '*/*',
                  'X-Self-Service-Correlation-ID': customer_info.request.correlation_id,
                  'User-Agent': customer_info.request.user_agent,
                  'Accept-Language': 'en-AU;q=1.0, es-MX;q=0.9',
                  'X-Self-Service-Client-ID': customer_info.request.self_service_client_id,
              } | token_data.auth_header()

    url_base = "https://selfservice.services.retail.energy/v1/usage/interval"

    params = {
        'consumerNumber': customer_info.customer.consumer_number,
        'fromDate': from_date,
        'toDate': to_date,
    }

    url = f"{url_base}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"

    response = requests.get(url, headers=headers)
    response_json = response.json()

    save_response_to_disk(data=response_json, filename=f'response_{from_date}_{to_date}.json')
    return response_json


def save_response_to_disk(data: dict, filename: str = 'response.json') -> None:
    with open(filename, 'w') as file:
        json.dump(data, file)


def get_most_recent_data() -> None:
    key_date = days_ago(1)
    res = get_authenticated_data(from_date=key_date, to_date=key_date)
    uda = UsageDataArray(res)
    print(f"Data from: {uda.root[0].usageDate} - {len(uda.root[0].halfHours)}")

# Example usage
# get_authenticated_data()
# Example usage
# data = UsageDataArray.parse_obj(json_data)
