
from __future__ import annotations
import random
import typing
import json
import requests
import re
import datetime
import time

TISS_DOMAIN = 'tiss.tuwien.ac.at'
TISS_URL = f'https://{TISS_DOMAIN}'

OPTION_BUILDING = re.compile(r'<option value="([A-Z]+)".*?>([A-Z]+) - (.*?) \(([^()]*?)\)</option>')
OPTION_ROOM = re.compile(r'<option value="([^"]+)"[^>]*>(.*?)( \(([0-9]+)\))?</option>')
CDATA = re.compile(r'<!\[CDATA\[(.*?)]]>')
UPDATE_VIEW_STATE = re.compile(r'<update id="j_id__v_0:javax.faces.ViewState:1"><!\[CDATA\[(.*?)]]></update>')
TABLE_TR = re.compile(r'<tr.*?>(.*?)</tr>')
TABLE_TD = re.compile(r'<td.*?>(.*?)</td>')
TAGS = re.compile(r'<.*?>')
SPACES = re.compile(r'\s+')


def iso_to_datetime(iso_str: str) -> (datetime.datetime, datetime.timezone):
    td = datetime.timedelta(hours=int(iso_str[-4:-3]), minutes=int(iso_str[-2:-1]))
    if iso_str[-5] == '-':
        td = -td
    tz = datetime.timezone(td)
    dt = datetime.datetime.fromisoformat(iso_str[:19])
    return dt, tz


class Building:
    id: str
    name: str
    tiss_name: str
    address: typing.Optional[str]
    _global_rooms: typing.Dict[str, Room]

    def __init__(self, building_id: str, tiss_name: str, name: typing.Optional[str] = None,
                 address: typing.Optional[str] = None, global_rooms: typing.Dict[str, Room] = None):
        self.id = building_id
        self.tiss_name = tiss_name
        self.name = name or tiss_name
        self.address = address if address is None or len(address) > 0 else None
        self._global_rooms = global_rooms

    @property
    def rooms(self) -> [Room]:
        return [room for room in self._global_rooms.values() if room.building.id == self.id]

    def __str__(self) -> str:
        return f'<Building#{self.id}{{{self.name}}}>'

    def __repr__(self) -> str:
        return f'<Building#{self.id}{{{self.name};{self.address};{self.tiss_name}}}>'


class Room:
    id: str
    name: str
    tiss_name: str
    capacity: typing.Optional[int]
    global_id: typing.Optional[str]
    _building_id: str
    _global_buildings: typing.Dict[str, Building]

    def __init__(self, room_id: str, building_id: str, tiss_name: str, name: typing.Optional[str] = None,
                 capacity: typing.Optional[int] = None, global_buildings: {str: Building} = None):
        self.id = room_id
        self.tiss_name = tiss_name
        self.name = name or tiss_name.split(' - Achtung!')[0]
        self._building_id = building_id
        self.capacity = capacity
        self._global_buildings = global_buildings
        self.global_id = None

    @property
    def building(self) -> Building:
        if self._global_buildings is None:
            raise RuntimeError('_global_buildings not initialized')
        return self._global_buildings[self._building_id]

    def __str__(self) -> str:
        return f'<Room#{self.id}{{{self._building_id},{self.name}}}>'

    def __repr__(self) -> str:
        return f'<Room#{self.id}{{{self._building_id},{self.name},{self.capacity},{self.tiss_name}}}>'


class Event:
    id: str
    start: datetime.datetime
    end: datetime.datetime
    all_day: bool
    title: str
    description: typing.Optional[str]
    type: str
    room: Room

    def __init__(self, event_id: str, start: datetime.datetime, end: datetime.datetime, title: str, event_type: str,
                 room: Room, description: typing.Optional[str] = None, all_day: bool = False):
        self.id = event_id
        self.start = start
        self.end = end
        self.title = title
        self.type = event_type
        self.description = description
        self.all_day = all_day
        self.room = room

    @staticmethod
    def from_json_obj(obj: typing.Dict[str], room: Room) -> Event:
        return Event(obj['id'], iso_to_datetime(obj['start'])[0], iso_to_datetime(obj['end'])[0], obj['title'],
                     obj['className'], room, obj['allDay'])


class Session:
    _win_id: int
    _req_token: int
    _view_state: typing.Optional[str]
    _session: requests.Session
    _buildings: typing.Optional[typing.Dict[str, Building]]
    _rooms: typing.Optional[typing.Dict[str, Room]]

    def __init__(self):
        self._win_id = Session.gen_win_id()
        self._req_token = Session.gen_req_token()
        self._buildings = None
        self._rooms = None
        self._view_state = None
        self._session = requests.Session()
        self._session.cookies.set(f'dsrwid-{self._req_token}', f'{self._win_id}', domain=TISS_DOMAIN)
        self._session.cookies.set('TISS_LANG', 'de', domain=TISS_DOMAIN)

    @staticmethod
    def gen_req_token() -> int:
        return random.randint(0, 999)

    @staticmethod
    def gen_win_id() -> int:
        return random.randint(1000, 9999)

    def update_endpoint(self, endpoint: str) -> str:
        endpoint += '&' if '?' in endpoint else '?'
        endpoint += f'dswid={self._win_id}&dsrid={self._req_token}'
        if endpoint[0] != '/':
            endpoint = f'/{endpoint}'
        return endpoint

    def get(self, endpoint: str, headers: typing.Dict[str, object] = None) -> requests.Response:
        r = self._session.get(f'{TISS_URL}{self.update_endpoint(endpoint)}', headers=headers)
        return r

    def post(self, endpoint: str, data: typing.Dict[str, object],
             headers: typing.Dict[str, object] = None) -> requests.Response:
        headers = headers or {}
        headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'

        data['javax.faces.ClientWindow'] = self._win_id
        data['dspwid'] = self._win_id
        data['X-Requested-With'] = 'XMLHttpRequest'
        data['Faces-Request'] = 'partial/ajax'
        if self._view_state is not None:
            data['javax.faces.ViewState'] = self._view_state
        elif 'javax.faces.ViewState' in data:
            del data['javax.faces.ViewState']

        r = self._session.post(f'{TISS_URL}{endpoint}',
                               data=data, headers=headers)

        for update in UPDATE_VIEW_STATE.finditer(r.text):
            self._view_state = update.group(1)

        return r

    def _get_buildings(self) -> [Building]:
        r = self.get('/events/selectRoom.xhtml')
        return [
            Building(opt.group(2), opt.group(3), address=opt.group(4), global_rooms=self._rooms)
            for opt in OPTION_BUILDING.finditer(r.text)
        ]

    def _get_rooms_for_building(self, building: Building) -> [Room]:
        data = {
            'filterForm:roomFilter:selectBuildingLb': building.id,
            'javax.faces.behavior.event': 'valueChange',
            'javax.faces.partial.event': 'change',
            'javax.faces.source': 'filterForm:roomFilter:selectBuildingLb',
            'javax.faces.partial.ajax': 'true',
            'javax.faces.partial.execute': 'filterForm:roomFilter',
            'javax.faces.partial.render': 'filterForm:roomFilter',
        }

        # Retrieve view_state
        self._view_state = None
        self.post('/events/selectRoom.xhtml', data)

        r = self.post('/events/selectRoom.xhtml', data)
        rooms = [
            Room(option.group(1), building.id, tiss_name=option.group(2), global_buildings=self._buildings)
            for option in OPTION_ROOM.finditer(r.text[r.text.find('filterForm:roomFilter:selectRoomLb'):])
        ]

        for room in rooms:
            self._get_room_details(room)

        return rooms

    def _get_room_details(self, room: Room):
        data = {
            'filterForm:roomFilter:selectBuildingLb': room.building.id,
            'filterForm:roomFilter:selectRoomLb': room.id,
            'javax.faces.behavior.event': 'action',
            'javax.faces.partial.event': 'click',
            'javax.faces.source': 'filterForm:roomFilter:searchButton',
            'javax.faces.partial.ajax': 'true',
            'javax.faces.partial.execute': 'filterForm:roomFilter filterForm:roomFilter:searchButton',
            'javax.faces.partial.render': 'filterForm tableForm',
        }

        # Retrieve view_state
        self._view_state = None
        self.post('/events/selectRoom.xhtml', data)

        r = self.post('/events/selectRoom.xhtml', data)
        for tr in TABLE_TR.finditer(r.text):
            row = [TAGS.sub('', td.group(1)) for td in TABLE_TD.finditer(tr.group(1))]
            if len(row) == 0:
                continue
            room.global_id = row[-1].strip().replace(' ', '')
            if room.global_id == '':
                room.global_id = room.id
            room.capacity = int(row[1].strip())

    @property
    def buildings(self) -> typing.Dict[str, Building]:
        if self._buildings is None:
            self._buildings = {}
            for building in self._get_buildings():
                self._buildings[building.id] = building
        return self._buildings

    @property
    def rooms(self) -> typing.Dict[str, Room]:
        if self._rooms is None:
            self._rooms = {}
            for building in self.buildings.values():
                for room in self._get_rooms_for_building(building):
                    self._rooms[room.id] = room
        return self._rooms

    def get_room_schedule(self, room: Room) -> [Event]:
        self._view_state = None
        self.get(f'/events/roomSchedule.xhtml?roomCode={room.id}')

        start = datetime.datetime.fromisoformat('2021-10-01T00:00:00')
        end = datetime.datetime.fromisoformat('2022-02-01T00:00:00')
        r = self.post('/events/roomSchedule.xhtml', {
            'calendarForm:schedule_start': int(time.mktime(start.timetuple())) * 1000,
            'calendarForm:schedule_end': int(time.mktime(end.timetuple())) * 1000,
            'javax.faces.source': 'calendarForm:schedule',
            'javax.faces.partial.ajax': 'true',
            'javax.faces.partial.execute': 'calendarForm:schedule',
            'javax.faces.partial.render': 'calendarForm:schedule',
            'calendarForm:schedule': 'calendarForm:schedule',
        })

        events = []
        for cdata in CDATA.finditer(r.text):
            d = cdata.group(1)
            if d.startswith('{"events":'):
                events = [Event.from_json_obj(event, room) for event in json.loads(cdata.group(1))['events']]
                break

        for event in events[1:]:
            data = {
                'javax.faces.partial.ajax': 'true',
                'javax.faces.source': 'calendarForm:schedule',
                'javax.faces.partial.execute': 'calendarForm:schedule',
                'javax.faces.partial.render': 'calendarForm:eventDetails',
                'javax.faces.behavior.event': 'eventSelect',
                'javax.faces.partial.event': 'eventSelect',
                'calendarForm:schedule_selectedEventId': event.id,
            }
            self._view_state = None
            self.post('/events/roomSchedule.xhtml', data)
            r = self.post('/events/roomSchedule.xhtml', data)

            print(r.text)
            print(self._session.cookies)
            print(r.request.url)
            print(r.request.body)

        return events


if __name__ == '__main__':
    s = Session()
    for evt in s.get_room_schedule(s.rooms['AUDI']):
        print(f'{str(evt.all_day):5} {evt.start} {evt.end} {evt.type:16} {evt.id}  {evt.title:32}')

