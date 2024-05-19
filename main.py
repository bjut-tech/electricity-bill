import sys
import time

from aliyun.log import LogClient, PutLogsRequest, LogItem
from environs import Env
from httpx import Client


class YdappClient:
    def __init__(self, openid: str):
        self.openid = openid
        self.client = Client(base_url='https://ydapp.bjut.edu.cn', params={
            'openid': openid,
            'orgid': 2
        }, headers={
            'User-Agent': 'Mozilla/5.0'
        })
        self.authenticate()

    def authenticate(self):
        self.client.get('/home/openHomePageApp')  # initialize cookies

    def query_balance(self, room_id: int) -> float:
        response = self.client.get('/channel/querySydl', params={
            'group_id': room_id,
            'factorycode': 'N002'
        }, follow_redirects=False)
        if response.has_redirect_location and 'error' in response.headers['Location'].lower():
            self.authenticate()
            response = self.client.get('/channel/querySydl', params={
                'group_id': room_id,
                'factorycode': 'N002'
            }, follow_redirects=False)
        response.raise_for_status()
        return float(response.json()['resultData']['MeterBalance'])


class MetricClient:
    def __init__(self, access_key_id: str, access_key_secret: str, endpoint: str, project: str, store: str):
        self.client = LogClient(endpoint, access_key_id, access_key_secret)
        self.project = project
        self.store = store
        self.entries = []

    def __del__(self):
        if len(self.entries) > 0:
            self.flush()

    def write(self, name: str, labels: dict, value: float):
        nano = 10 ** 9
        now = time.time_ns()
        self.entries.append(LogItem(
            timestamp=now // nano,
            time_nano_part=now % nano,
            contents=[
                ('__name__', name),
                ('__labels__', '|'.join([f'{k}#$#{v}' for k, v in labels.items() if v])),
                ('__time_nano__', str(now)),
                ('__value__', str(value))
            ]
        ))
        print(f'[{now // nano}] meter balance: {value}')
        if len(self.entries) >= 10:
            self.flush()

    def flush(self):
        items = self.entries.copy()
        self.entries.clear()
        if len(items) == 0:
            return
        print(f'flushing {len(items)} entries')
        req = PutLogsRequest(self.project, self.store, logitems=items)
        self.client.put_logs(req)


def main():
    env = Env()
    env.read_env()

    client = YdappClient(env.str('YDAPP_OPENID'))
    metric_client = MetricClient(
        env.str('ALIBABA_CLOUD_ACCESS_KEY_ID'),
        env.str('ALIBABA_CLOUD_ACCESS_KEY_SECRET'),
        env.str('ALIBABA_CLOUD_SLS_ENDPOINT'),
        env.str('ALIBABA_CLOUD_SLS_PROJECT'),
        env.str('ALIBABA_CLOUD_SLS_STORE')
    )
    room_id = env.int('YDAPP_ROOM_ID')
    while True:
        try:
            balance = client.query_balance(room_id)
            metric_client.write('ac_meter_balance', {
                'room_id': room_id
            }, balance)
        except Exception as e:
            print(e, file=sys.stderr)
        time.sleep(30)


if __name__ == '__main__':
    main()
