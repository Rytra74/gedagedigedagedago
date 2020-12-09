# coding: utf-8
from __future__ import unicode_literals

import random
import re

from .common import InfoExtractor
from ..utils import ExtractorError, try_get, compat_str
from ..compat import compat_urllib_parse_unquote


class AudiusIE(InfoExtractor):
    _VALID_URL = r'''(?x)^(?:https?://)?
                     (?:(?:(?:www\.)?audius\.co/(?P<uploader>[\w\d-]+)(?!/album|/playlist)/(?P<title>\S+))
                     |(?:discoveryprovider(?:\d)?\.audius\.co/v1/tracks/(?P<track_id>\w+))
                     )
                 '''
    _TESTS = [
        {
            # URL from Chrome address bar which replace backslash to forward slash
            'url': 'https://audius.co/test_acc/t%D0%B5%D0%B5%D0%B5est-1.%5E_%7B%7D/%22%3C%3E.%E2%84%96~%60-198631',
            'md5': '92c35d3e754d5a0f17eef396b0d33582',
            'info_dict': {
                'id': 'xd8gY',
                'title': '''Tеееest/ 1.!@#$%^&*()_+=[]{};'\\\":<>,.?/№~`''',
                'ext': 'mp3',
                'description': 'Description',
                'duration': 30,
                'track': '''Tеееest/ 1.!@#$%^&*()_+=[]{};'\\\":<>,.?/№~`''',
                'artist': 'test',
                'genre': 'Electronic',
                'thumbnail': r're:https?://.*\.jpg',
                'view_count': int,
                'like_count': int,
                'repost_count': int,
            }
        },
        {
            # Regular track
            'url': 'https://audius.co/voltra/radar-103692',
            'md5': '491898a0a8de39f20c5d6a8a80ab5132',
            'info_dict': {
                'id': 'KKdy2',
                'title': 'RADAR',
                'ext': 'mp3',
                'duration': 318,
                'track': 'RADAR',
                'artist': 'voltra',
                'genre': 'Trance',
                'thumbnail': r're:https?://.*\.jpg',
                'view_count': int,
                'like_count': int,
                'repost_count': int,
            }
        },
        {
            # API URL
            'url': 'https://discoveryprovider3.audius.co/v1/tracks/xd8gY',
            'md5': '92c35d3e754d5a0f17eef396b0d33582',
            'info_dict': {
                'id': 'xd8gY',
                'title': '''Tеееest/ 1.!@#$%^&*()_+=[]{};'\\\":<>,.?/№~`''',
                'ext': 'mp3',
                'description': 'Description',
                'duration': 30,
                'track': '''Tеееest/ 1.!@#$%^&*()_+=[]{};'\\\":<>,.?/№~`''',
                'artist': 'test',
                'genre': 'Electronic',
                'thumbnail': r're:https?://.*\.jpg',
                'view_count': int,
                'like_count': int,
                'repost_count': int,
            }
        },
    ]

    _API_BASE = None
    _API_V = '/v1'
    _ARTWORK_MAP = {
        "150x150": 150,
        "480x480": 480,
        "1000x1000": 1000
    }

    def _get_response_data(self, response):
        if isinstance(response, dict):
            response_data = response.get('data')
            if response_data is not None:
                return response_data
            if len(response) == 1 and 'message' in response:
                raise ExtractorError('API error: %s' % response['message'], expected=True)
        raise ExtractorError('Unexpected API response')

    def _select_api_base(self):
        """Selecting one of the currently available API hosts"""
        response = super(AudiusIE, self)._download_json(
            'https://api.audius.co/',
            None,
            note='Requesting available API hosts',
            errnote='Unable to request available API hosts'
        )
        hosts = self._get_response_data(response)
        if isinstance(hosts, list):
            self._API_BASE = random.choice(hosts)
            return
        raise ExtractorError('Unable to get available API hosts', expected=True)

    @staticmethod
    def _prepare_url(url, title):
        """
        Audius removes forward slashes from the uri, but leaves backslashes.
        The problem is that the current version of Chrome replaces backslashes in the address
        bar with a forward slashes, so if you copy the link from there and paste it into youtube-dl,
        you won't be able to download anything from this link, since the Audius API won't be able
        to resolve this url
        """
        url = compat_urllib_parse_unquote(url)
        title = compat_urllib_parse_unquote(title)
        if '/' in title or '%2F' in title:
            fixed_title = title.replace('/', '%5C').replace('%2F', '%5C')
            return url.replace(title, fixed_title)
        return url

    def _api_request(
        self,
        path,
        item_id=None,
        note='Downloading JSON metadata',
        errnote='Unable to download JSON metadata',
        expected_status=None
    ):
        if self._API_BASE is None:
            self._select_api_base()
        response = super(AudiusIE, self)._download_json(
            self._API_BASE + self._API_V + path, item_id, note=note, errnote=errnote,
            expected_status=expected_status
        )
        return self._get_response_data(response)

    def _resolve_url(self, url, item_id):
        return self._api_request('/resolve?url=' + url, item_id, expected_status=404)

    def _real_extract(self, url):
        self._select_api_base()
        mobj = re.match(self._VALID_URL, url)
        uploader, title, track_id = mobj.groups()
        if track_id is None:
            url = self._prepare_url(url, title)
            track_data = self._resolve_url(url, title)
        else:
            track_data = self._api_request('/tracks/%s' % track_id, track_id)

        if not isinstance(track_data, dict):
            raise ExtractorError('Unexpected API response')

        track_id = track_data.get('id')
        if track_id is None:
            raise ExtractorError('Unable to get ID of the track')

        artworks_data = track_data.get('artwork')
        thumbnails = []
        if isinstance(artworks_data, dict):
            for quality_key, thumbnail_url in artworks_data.items():
                thumbnail = {
                    "url": thumbnail_url
                }
                quality_code = self._ARTWORK_MAP.get(quality_key)
                if quality_code is not None:
                    thumbnail['preference'] = quality_code
                thumbnails.append(thumbnail)

        return {
            'id': track_id,
            'title': track_data.get('title', title),
            'url': '%s/v1/tracks/%s/stream' % (self._API_BASE, track_id),
            'ext': 'mp3',
            'description': track_data.get('description'),
            'duration': track_data.get('duration'),
            'track': track_data.get('title'),
            'artist': try_get(track_data, lambda x: x['user']['name'], compat_str),
            'genre': track_data.get('genre'),
            'thumbnails': thumbnails,
            'view_count': track_data.get('play_count'),
            'like_count': track_data.get('favorite_count'),
            'repost_count': track_data.get('repost_count'),
        }


class AudiusPlaylistIE(AudiusIE):
    _VALID_URL = r'(?:https?://)?(?:(?:www\.)?audius\.co/(?P<uploader>[\w\d-]+)/(?:album|playlist)/(?P<title>\S+))'
    IE_NAME = 'audius:playlist'
    _TESTS = [{
        'url': 'https://audius.co/test_acc/playlist/test-playlist-22910',
        'info_dict': {
            'id': 'DNvjN',
            'title': 'test playlist',
            'description': 'Test description\n\nlol',
        },
        'playlist_count': 175,
    }]

    def _build_playlist(self, tracks):
        entries = []
        for track in tracks:
            track_id = track.get('id')
            if not track_id:
                continue
            entries.append(
                self.url_result(
                    '%s%s/tracks/%s' % (self._API_BASE, self._API_V, track_id),
                    ie=AudiusIE.ie_key(),
                    video_id=track_id
                )
            )
        return entries

    def _real_extract(self, url):
        self._select_api_base()
        mobj = re.match(self._VALID_URL, url)
        uploader, title = mobj.groups()
        url = self._prepare_url(url, title)
        playlist_response = self._resolve_url(url, title)

        if not isinstance(playlist_response, list) or len(playlist_response) != 1:
            raise ExtractorError('Unexpected API response')

        playlist_data = playlist_response[0]
        playlist_id = playlist_data.get('id')
        if playlist_id is None:
            raise ExtractorError('Unable to get ID of the playlist')

        playlist_tracks = self._api_request(
            '/playlists/%s/tracks' % playlist_id,
            title,
            'Downloading playlist tracks metadata',
            'Unable to download playlist tracks metadata',
        )
        if not isinstance(playlist_tracks, list):
            raise ExtractorError('Unexpected API response')

        entries = self._build_playlist(playlist_tracks)
        return self.playlist_result(
            entries, playlist_id, playlist_data.get('playlist_name', title), playlist_data.get('description')
        )
