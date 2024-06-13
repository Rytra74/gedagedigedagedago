import json
import re

from .common import InfoExtractor

from ..utils import (
    ExtractorError,
    update_url_query,
)


class SafariBaseIE(InfoExtractor):
    _LOGIN_URL = 'https://learning.oreilly.com/accounts/login/'
    _NETRC_MACHINE = 'safari'

    _API_BASE = 'https://learning.oreilly.com/api/v1'
    _API_FORMAT = 'json'

    LOGGED_IN = False

    def is_logged_in(self, fatal=True):
        auth, urlh = self._download_json_handle(
            'https://api.oreilly.com/api/v2/me/', None, note='Checking if logged in', fatal=False,
            headers={'Accept': 'application/json'}, expected_status=401)
        if urlh.status == 401:
            msg = 'Unable to login: %s' % auth['detail']
            if fatal:
                raise ExtractorError(msg)
            self.write_debug(msg)
            self.LOGGED_IN = False
            return self.LOGGED_IN
        self.LOGGED_IN = True
        return self.LOGGED_IN

    def _initialize_pre_login(self):
        self.is_logged_in(fatal=False)

    def _perform_login(self, username, password):

        if self.LOGGED_IN:
            return

        auth, urlh = self._download_json_handle(
            'https://www.oreilly.com/member/auth/login/', None, 'Logging in',
            data=json.dumps({
                'email': username,
                'password': password
            }).encode(), headers={
                'Content-Type': 'application/json'
            }, expected_status=400)

        credentials = auth.get('credentials')
        if (not auth.get('logged_in') and not auth.get('redirect_uri')
                and credentials):
            raise ExtractorError('Unable to login: %s' % credentials, expected=True)

        # oreilly serves two same instances of the following cookies
        # in Set-Cookie header and expects first one to be actually set
        for cookie in ('groot_sessionid', 'orm-jwt', 'orm-rt'):
            self._apply_first_set_cookie_header(urlh, cookie)

        self.is_logged_in()


class SafariIE(SafariBaseIE):
    IE_NAME = 'safari'
    IE_DESC = 'safaribooksonline.com online video'
    _VALID_URL = r'''(?x)
                        https?://
                            (?:www\.)?(?:safaribooksonline|(?:learning\.)?oreilly)\.com/
                            (?:
                                library/view/[^/]+/(?P<course_id>[^/]+)/(?P<part>[^/?\#&]+)\.html|
                                videos/[^/]+/[^/]+/(?P<reference_id>[^-]+-[^/?\#&]+)
                            )
                    '''

    _TESTS = [{
        'url': 'https://www.safaribooksonline.com/library/view/hadoop-fundamentals-livelessons/9780133392838/part00.html',
        'md5': '592d0e6d0b03d9b981b3f7306ffc5ca9',
        'info_dict': {
            'id': '0_qbqx90ic',
            'ext': 'mp4',
            'title': 'Introduction to Hadoop Fundamentals LiveLessons',
            'timestamp': 1437758058,
            'upload_date': '20150724',
            'uploader_id': 'stork',
            'duration': 149,
            'view_count': int,
            'thumbnail': 'http://cfvod.kaltura.com/p/1926081/sp/192608100/thumbnail/entry_id/0_qbqx90ic/version/100000'
        },
    }, {
        # non-digits in course id
        'url': 'https://www.safaribooksonline.com/library/view/create-a-nodejs/100000006A0210/part00.html',
        'only_matching': True,
    }, {
        'url': 'https://www.safaribooksonline.com/library/view/learning-path-red/9780134664057/RHCE_Introduction.html',
        'only_matching': True,
    }, {
        'url': 'https://www.safaribooksonline.com/videos/python-programming-language/9780134217314/9780134217314-PYMC_13_00',
        'only_matching': True,
    }, {
        'url': 'https://learning.oreilly.com/videos/hadoop-fundamentals-livelessons/9780133392838/9780133392838-00_SeriesIntro',
        'only_matching': True,
    }, {
        'url': 'https://www.oreilly.com/library/view/hadoop-fundamentals-livelessons/9780133392838/00_SeriesIntro.html',
        'only_matching': True,
    }]

    _PARTNER_ID = '1926081'
    _UICONF_ID = '29375172'

    def _real_extract(self, url):
        entry_id = ''
        mobj = self._match_valid_url(url)

        reference_id = mobj.group('reference_id')
        if reference_id:
            video_id = reference_id
            partner_id = self._PARTNER_ID
            ui_id = self._UICONF_ID
        else:
            video_id = '{}-{}'.format(mobj.group('course_id'), mobj.group('part'))

            webpage, urlh = self._download_webpage_handle(url, video_id)

            mobj = re.match(self._VALID_URL, urlh.geturl())
            reference_id = mobj.group('reference_id')
            if not reference_id:
                reference_id = self._search_regex(
                    r'data-reference-id=(["\'])(?P<id>(?:(?!\1).)+)\1',
                    webpage, 'kaltura reference id', default='', group='id')
                entry_id = self._search_regex(
                    r'data-entry-id=(["\'])(?P<id>(?:(?!\1).)+)\1',
                    webpage, 'kaltura entry id', default='', group='id')
                if not any((entry_id, reference_id)):
                    raise ExtractorError('Unable to find kaltura "reference id" or "entry id"')
            partner_id = self._search_regex(
                r'data-partner-id=(["\'])(?P<id>(?:(?!\1).)+)\1',
                webpage, 'kaltura widget id', default=self._PARTNER_ID,
                group='id')
            ui_id = self._search_regex(
                r'data-ui-id=(["\'])(?P<id>(?:(?!\1).)+)\1',
                webpage, 'kaltura uiconf id', default=self._UICONF_ID,
                group='id')

        query = {
            'wid': f'_{partner_id}',
            'uiconf_id': ui_id,
            'entry_id': entry_id,
            'flashvars[referenceId]': reference_id
        }

        if self.LOGGED_IN:
            kaltura_session = self._download_json(
                f'{self._API_BASE}/player/kaltura_session/?reference_id={reference_id}',
                video_id, 'Downloading kaltura session JSON',
                'Unable to download kaltura session JSON', fatal=False,
                headers={'Accept': 'application/json'})
            if kaltura_session:
                session = kaltura_session.get('session')
                if session:
                    query['flashvars[ks]'] = session

        return self.url_result(update_url_query(
            'https://cdnapisec.kaltura.com/html5/html5lib/v2.37.1/mwEmbedFrame.php', query),
            'Kaltura')


class SafariApiIE(SafariBaseIE):
    IE_NAME = 'safari:api'
    _VALID_URL = r'https?://(?:www\.)?(?:safaribooksonline|(?:learning\.)?oreilly)\.com/api/v1/book/(?P<course_id>[^/]+)/chapter(?:-content)?/(?P<part>[^/?#&]+)\.html'

    _TESTS = [{
        'url': 'https://www.safaribooksonline.com/api/v1/book/9780133392838/chapter/part00.html',
        'only_matching': True,
    }, {
        'url': 'https://www.safaribooksonline.com/api/v1/book/9780134664057/chapter/RHCE_Introduction.html',
        'only_matching': True,
    }]

    def _real_extract(self, url):
        mobj = self._match_valid_url(url)
        part = self._download_json(
            url, '{}/{}'.format(mobj.group('course_id'), mobj.group('part')),
            'Downloading part JSON')
        web_url = part['web_url']
        if 'library/view' in web_url:
            web_url = web_url.replace('library/view', 'videos')
            natural_keys = part['natural_key']
            web_url = f'{web_url.rsplit("/", 1)[0]}/{natural_keys[0]}-{natural_keys[1][:-5]}'
        return self.url_result(web_url, SafariIE.ie_key())


class SafariCourseIE(SafariBaseIE):
    IE_NAME = 'safari:course'
    IE_DESC = 'safaribooksonline.com online courses'

    _VALID_URL = r'''(?x)
                    https?://
                        (?:
                            (?:www\.)?(?:safaribooksonline|(?:learning\.)?oreilly)\.com/
                            (?:
                                library/view/[^/]+|
                                api/v1/book|
                                videos/[^/]+
                            )|
                            techbus\.safaribooksonline\.com
                        )
                        /(?P<id>[^/]+)
                    '''

    _TESTS = [{
        'url': 'https://www.safaribooksonline.com/library/view/hadoop-fundamentals-livelessons/9780133392838/',
        'info_dict': {
            'id': '9780133392838',
            'title': 'Hadoop Fundamentals LiveLessons',
        },
        'playlist_count': 22,
        'skip': 'Requires safaribooksonline account credentials',
    }, {
        'url': 'https://www.safaribooksonline.com/api/v1/book/9781449396459/?override_format=json',
        'only_matching': True,
    }, {
        'url': 'http://techbus.safaribooksonline.com/9780134426365',
        'only_matching': True,
    }, {
        'url': 'https://www.safaribooksonline.com/videos/python-programming-language/9780134217314',
        'only_matching': True,
    }, {
        'url': 'https://learning.oreilly.com/videos/hadoop-fundamentals-livelessons/9780133392838',
        'only_matching': True,
    }, {
        'url': 'https://www.oreilly.com/library/view/hadoop-fundamentals-livelessons/9780133392838/',
        'only_matching': True,
    }]

    @classmethod
    def suitable(cls, url):
        return (False if SafariIE.suitable(url) or SafariApiIE.suitable(url)
                else super().suitable(url))

    def _real_extract(self, url):
        course_id = self._match_id(url)

        course_json = self._download_json(
            f'{self._API_BASE}/book/{course_id}/?override_format={self._API_FORMAT}',
            course_id, 'Downloading course JSON')

        if 'chapters' not in course_json:
            raise ExtractorError(
                'No chapters found for course %s' % course_id, expected=True)

        entries = [
            self.url_result(chapter, SafariApiIE.ie_key())
            for chapter in course_json['chapters']]

        course_title = course_json['title']

        return self.playlist_result(entries, course_id, course_title)
