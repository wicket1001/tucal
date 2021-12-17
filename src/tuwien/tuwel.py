
from typing import Optional, Dict
import requests
import re
import json

from tucal import Semester
import tucal.icalendar
import tuwien.sso

TUWEL_DOMAIN = 'tuwel.tuwien.ac.at'
TUWEL_URL = f'https://{TUWEL_DOMAIN}'

LINK_COURSE = re.compile(rf'<a href="https://tuwel\.tuwien\.ac\.at/course/view\.php\?id=([0-9]+)" '
                         r'title="([0-9]{3}\.[0-9A-Z]{3})\s*(.*?)\s*([0-9]{4}[SW])">')
AUTH_TOKEN = re.compile(r'authtoken=([^&]*)')
INPUT_SESS_KEY = re.compile(r'<input name="sesskey" type="hidden" value="([^"]*)" */?>')
USER_ID = re.compile(r'data-userid="([0-9]+)"')
SESS_KEY = re.compile(r'"sesskey":"([^"]*)"')

H1 = re.compile(r'<h1>([0-9]{3}\.[0-9A-Z]{3})\s*(.*?)\s*([0-9]{4}[SW])</h1>')
SPAN = re.compile(r'<span class="media-body font-weight-bold">\s*([^<>]*)\s*</span>')


class Course:
    id: int
    semester: Semester
    nr: str
    name: str
    suffix: str
    short: str

    def __init__(self, course_id: int, semester: Semester, nr: str, name: str, short: str):
        self.id = course_id
        self.semester = Semester(str(semester))
        self.nr = nr.replace('.', '')
        name = name.rsplit(' (', 1)
        self.name = name[0].strip()
        self.suffix = name[1].replace(')', '').strip() if len(name) > 1 else None
        self.short = short


class Session:
    _session: requests.Session
    _sso: tuwien.sso.Session
    _courses: Optional[Dict[str, Course]]
    _user_id: Optional[int]
    _sess_key: Optional[str]
    _calendar_token: Optional[str]
    _timeout: float

    def __init__(self, session: tuwien.sso.Session = None, timeout: float = 20):
        self._sso = session
        self._session = session and session.session or requests.Session()
        self._courses = None
        self._user_id = None
        self._sess_key = None
        self._calendar_token = None
        self._timeout = timeout

    def get(self, uri: str) -> requests.Response:
        r = self._session.get(f'{TUWEL_URL}{uri}', timeout=self._timeout)

        for user_id in USER_ID.finditer(r.text):
            self._user_id = int(user_id.group(1))
        for key in SESS_KEY.finditer(r.text):
            self._sess_key = key.group(1)

        return r

    def post(self, uri: str, data=None, headers=None) -> requests.Response:
        return self._session.post(f'{TUWEL_URL}{uri}', data=data, headers=headers, timeout=self._timeout)

    def ajax(self, method: str, **args) -> Dict:
        data = [{
            'index': 0,
            'methodname': method,
            'args': args,
        }]

        if self._sess_key is None:
            self.get('/my/')

        r = self.post(f'/lib/ajax/service.php?sesskey={self._sess_key}', data=json.dumps(data),
                      headers={'Content-Type': 'application/json; encoding=UTF-8'})
        return json.loads(r.text)[0]

    def sso_login(self) -> bool:
        if self._sso is None:
            raise RuntimeError('No SSO session provided')
        return self._sso.login(f'{TUWEL_URL}/auth/saml2/login.php')

    def _get_calendar_token(self) -> str:
        self.get('/calendar/export.php')

        r = self.post('/calendar/export.php', {
            '_qf__core_calendar_export_form': '1',
            'events[exportevents]': 'all',
            'period[timeperiod]': 'custom',
            'sesskey': self._sess_key,
            'generateurl': 'Kalender-URL abfragen',
        })
        return AUTH_TOKEN.findall(r.text)[0]

    def _get_course(self, course_id: int) -> Course:
        r = self.get(f'/course/view.php?id={course_id}')

        course_nr, name, semester = H1.findall(r.text)[0]
        short = SPAN.findall(r.text)[0]

        return Course(course_id, Semester(semester), course_nr, name, short)

    def _get_courses(self) -> Dict[str, Course]:
        r = self.get('/my/')
        courses = {
            (link.group(1), link.group(2), link.group(3), link.group(4))
            for link in LINK_COURSE.finditer(r.text)
        }
        return {
            f'{course[1].replace(".", "")}-{course[3]}': self._get_course(course[0])
            for course in courses
        }

    @property
    def courses(self) -> Dict[str, Course]:
        if self._courses is None:
            self._courses = self._get_courses()
        return self._courses

    @property
    def user_id(self) -> int:
        if self._user_id is None:
            self.get('/my/')
        return self._user_id

    @property
    def calendar_token(self) -> str:
        if self._calendar_token is None:
            self._calendar_token = self._get_calendar_token()
        return self._calendar_token

    def get_personal_calendar(self, token: str, what: str = 'all', time: str = 'custom',
                              user_id: int = None) -> Optional[tucal.icalendar.Calendar]:
        r = self.get(f'/calendar/export_execute.php?userid={user_id or self.user_id}&authtoken={token}&'
                     f'preset_what={what}&preset_time={time}')
        if r.status_code == 200:
            return tucal.icalendar.parse_ical(r.text)
        else:
            return None
