
from typing import Optional, Dict, List, Tuple
import requests
import re
import json
import html

from tucal import Semester
import tucal.icalendar
import tuwien.sso

TUWEL_DOMAIN = 'tuwel.tuwien.ac.at'
TUWEL_URL = f'https://{TUWEL_DOMAIN}'

AUTH_TOKEN = re.compile(r'authtoken=([^&]*)')
INPUT_SESS_KEY = re.compile(r'<input name="sesskey" type="hidden" value="([^"]*)" */?>')
USER_ID = re.compile(r'data-userid="([0-9]+)"')
SESS_KEY = re.compile(r'"sesskey":"([^"]*)"')

COURSE_NR = re.compile(r'^[A-z0-9]{3}\.[A-Z0-9]{3} (.*)$')
SPAN = re.compile(r'<span class="media-body font-weight-bold">\s*([^<>]*)\s*</span>')
GROUP_OPTION = re.compile(r'<option value="([0-9]+)">([^<]*)</option>')
GROUP_TOOL_LINK = re.compile(r'href="https://tuwel\.tuwien\.ac\.at/mod/grouptool/view\.php\?id=([0-9]+)"')
GROUP_MEMBERS = re.compile(r'>(Gruppenmitglieder anzeigen|Angemeldet auf Platz)')
GROUP_NAME = re.compile(r'<h2 class="panel-title">\s*([^<]*)\s*</h2>')


class Course:
    id: int
    semester: Optional[Semester]
    nr: Optional[str]
    name: str
    suffix: str
    short: str

    def __init__(self, course_id: int, semester: Optional[Semester], nr: Optional[str], name: str, short: str):
        self.id = course_id
        self.semester = Semester(str(semester)) if semester else None
        self.nr = nr.replace('.', '') if nr else None
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

    def _get_courses(self) -> Dict[str, Course]:
        data1 = self.ajax('core_course_get_enrolled_courses_by_timeline_classification',
                          classification='all', limit=0, offset=0, sort='fullname')
        data2 = self.ajax('core_course_get_enrolled_courses_by_timeline_classification',
                          classification='hidden', limit=0, offset=0, sort='fullname')
        courses = {}
        for c in data1['data']['courses'] + data2['data']['courses']:
            c.pop('courseimage', None)
            part = c['idnumber'].split('-')
            if len(part) == 2:
                num = part[0]
                sem = Semester(part[1])
            else:
                num, sem = None, None
            m = COURSE_NR.match(c['fullname'])
            name = html.unescape(m.group(1)) if m else c['fullname']
            courses[c['idnumber']] = Course(c['id'], sem, num, name, c['shortname'])
        return courses

    def get_course_user_groups(self, course_id: int) -> List[Tuple[int, str]]:
        r = self.get(f'/user/index.php?id={course_id}')
        p1 = r.text.find('<select multiple="multiple" data-field-name="groups"')
        if p1 != -1:
            p2 = r.text.find('</select>', p1)
            data = r.text[p1:p2]
            groups = [(int(opt.group(1)), opt.group(2)) for opt in GROUP_OPTION.finditer(data)]
            if '<option value="-1">Keine Gruppe</option>' not in data:
                return groups
            all_groups = {g[1]: g[0] for g in groups}
        else:
            return []

        r = self.get(f'/course/view.php?id={course_id}')
        groups = []
        for link in GROUP_TOOL_LINK.finditer(r.text):
            r = self.get(f'/mod/grouptool/view.php?id={link.group(1)}')
            for member in GROUP_MEMBERS.finditer(r.text):
                pos = r.text.rfind('<h2 class="panel-title">', 0, member.start())
                group_name = html.unescape(GROUP_NAME.findall(r.text, pos)[0]).strip()
                groups.append((all_groups[group_name], group_name))
        return groups

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
