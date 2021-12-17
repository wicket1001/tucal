# 187.B12 VU Denkweisen der Informatik

import typing
import requests
import requests.cookies
import json
import re
import html
import datetime

import tucal
import tucal.db
import tucal.icalendar
import tuwien.sso

RE_TOKEN = re.compile(r'"token": "([^"]*)", "pk": ([0-9]+),')
RE_DATES = re.compile(r'<div class="header collapse[^>]*>([^\n]*)|\s*([^<>]*)\s*<i[^>]* data-block="([^"]*)">',
                      re.DOTALL | re.MULTILINE)
RE_THINKING = re.compile(r'([A-Z][a-z]+) Thinking')

WEBCAL = 'https://p101-caldav.icloud.com/published/2/' \
         'MzgyNDc0ODczODI0NzQ4N6wcQX1kdbFRkK0NDrPux_KFL1TO6WWudBvZC5LkC8jII-EKirQ5vlMF0ygrdaHcTzQMX_rXGyWk6aEK3ptjEaU'

AURORA_HOST = 'aurora.iguw.tuwien.ac.at'
REVIEW_HOST = 'review.iguw.tuwien.ac.at'

AURORA = f'https://{AURORA_HOST}'
LITTLE_AURORA = f'https://{REVIEW_HOST}'


def get_group_nr(semester: tucal.Semester) -> typing.Optional[int]:
    cur = tucal.db.cursor()
    cur.execute("SELECT group_nr FROM tucal.group WHERE (course_nr, semester) = ('187B12', %s)", (str(semester),))
    rows = cur.fetch_all()
    if len(rows) == 0:
        return None
    return rows[0][0]


class Plugin(tucal.Plugin):
    @staticmethod
    def sync():
        group_nr = get_group_nr(tucal.Semester('2021W'))
        r = requests.get(WEBCAL)
        if r.status_code != 200:
            return

        cal = tucal.icalendar.parse_ical(r.text)
        rows = []
        for evt in cal.events:
            if evt.summary.startswith('Abgabe:') or evt.summary.startswith('Ende Reviewing:') or \
                    evt.summary.startswith('Finale Abgabe:') or evt.summary.startswith('Start:'):
                continue
            rows.append({
                'source': '187B12-aurora',
                'id': evt.uid_rec,
                'start': evt.start,
                'end': evt.end,
                'group': group_nr,
                'del': evt.summary.startswith('kein dwi') or 'Pause' in evt.summary,
                'data': json.dumps({
                    'aurora': {
                        'summary': evt.summary,
                        'url': evt.url,
                    },
                }),
            })

        fields = {
            'source': 'source',
            'event_id': 'id',
            'start_ts': 'start',
            'end_ts': 'end',
            'group_nr': 'group',
            'deleted': 'del',
            'data': 'data'
        }
        tucal.db.upsert('tucal.external_event', rows, fields, ('source', 'event_id'), {'data': 'jsonb'})
        tucal.db.commit()

    @staticmethod
    def sync_auth(sso: tuwien.sso.Session):
        group_nr = get_group_nr(tucal.Semester('2021W'))
        # TODO (LITTLE) AURORA HAS TO BE EXTERMINATED

        sso.session.get(AURORA)
        sso.session.get(f'{AURORA}/course/dwi/login/?next=/course/dwi/')
        r = sso.session.get('https://iu.zid.tuwien.ac.at/AuthServ.authenticate?app=131&param=/course/dwi/')
        if r.status_code != 200:
            raise RuntimeError()

        r = sso.session.get(f'{AURORA}/dcall_login/dcall_login.js')
        if r.status_code != 200:
            raise RuntimeError()

        m = RE_TOKEN.findall(r.text)
        if len(m) == 0:
            raise RuntimeError()

        cookies = sso.session.cookies
        session_id = cookies.get('sessionid', domain=AURORA_HOST)
        c = requests.cookies.create_cookie('sessionid', session_id, domain=REVIEW_HOST)
        cookies.set_cookie(c)

        token, pk = m[0]
        sso.session.post(f'{LITTLE_AURORA}/aurora_login/login/', {
            'token': token,
            'pk': pk,
        })

        r = sso.session.get(f'{LITTLE_AURORA}/course/overview')
        if r.status_code != 200:
            raise RuntimeError()

        assignments = {}
        current_assignment = None
        for m in RE_DATES.finditer(r.text):
            new_assignment = m.group(1)
            if new_assignment:
                current_assignment = html.unescape(new_assignment).strip()
                assignments[current_assignment] = {}
            else:
                state = m.group(2).strip().lower()
                deadline = m.group(3).strip()

                if state.startswith('revisions/reflection'):
                    s = 'reflection'
                elif state.startswith('reviewing'):
                    s = 'reviewing'
                elif 'reviewing' in assignments[current_assignment] and state in ('ends', 'end', 'ended'):
                    s = 'reviewing_end'
                elif state in ('starts', 'start', 'started'):
                    s = 'start'
                else:
                    s = 'end'
                dt = datetime.datetime.strptime(deadline, '%d.%m, %H:%M')
                if dt.month >= 6:
                    dt = dt.replace(year=2021)
                else:
                    dt = dt.replace(year=2022)
                assignments[current_assignment][s] = dt

        events = {}
        for ass, data in assignments.items():
            idx = ass
            if ass.startswith('Zusammenfassung'):
                idx = ass
            elif 'Thinking' in ass:
                m = RE_THINKING.findall(ass)
                idx = f'Challenge {m[0]} Thinking'
            if idx not in events:
                events[idx] = {}
                if 'Challenge' in idx:
                    events[idx]['challenges'] = []
            evt = events[idx]
            if 'Challenge' in idx:
                evt['challenges'].append(ass)
            evt.update(data)

        rows = []
        for name, event in events.items():
            for sub in ('end', 'reviewing_end', 'reflection'):
                if sub not in event:
                    break
                evt_id = name.replace(' ', '-')\
                             .replace('Zusammenfassung', 'zsfg')\
                             .replace('Challenge', 'chlge')\
                             .lower() + '-' + sub.replace('_', '-')

                suffix = 'Reviewing' if sub == 'reviewing_end' else 'Reflection' if sub == 'reflection' else None
                data = {'aurora': {'summary': name + ((' - ' + suffix) if suffix else '')}}
                if 'challenges' in event:
                    data['aurora']['challenges'] = event['challenges']
                rows.append({
                    'source': '187B12-review',
                    'id': evt_id,
                    'ts': event[sub],
                    'group': group_nr,
                    'data': json.dumps(data),
                })

        fields = {
            'source': 'source',
            'event_id': 'id',
            'start_ts': 'ts',
            'end_ts': 'ts',
            'group_nr': 'group',
            'data': 'data',
        }
        tucal.db.upsert('tucal.external_event', rows, fields, ('source', 'event_id'), {'data': 'jsonb'})
        tucal.db.commit()

