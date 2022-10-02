# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..utils import unified_timestamp, parse_duration


class VXXXIE(InfoExtractor):
    _VALID_URL = r'https?://vxxx\.com/video-(?P<id>\d+)'
    _TESTS = [{
        'url': 'https://vxxx.com/video-80747',
        'md5': '4736e868b0e008b4ff9dc09585c26c52',
        'info_dict': {
            'id': '80747',
            'ext': 'mp4',
            'title': 'Monica Aka Selina',
            'display_id': 'monica-aka-selina',
            'thumbnail': 'https://tn.vxxx.com/contents/videos_screenshots/80000/80747/420x236/1.jpg',
            'description': '',
            'timestamp': 1607167706,
            'upload_date': '20201205',
            'duration': 2373.0,
            'view_count': 1071,
            'like_count': 1,
            'dislike_count': 0,
            'average_rating': 5.0,
            'categories': ['Anal', 'Asian', 'BDSM', 'Brunette', 'Toys',
                           'Fetish', 'HD', 'Interracial', 'MILF'],
        }}]

    def _download_info_object(self, video_id):
        return self._download_json(
            'https://vxxx.com/api/json/video/86400/0/{}/{}.json'.format(
                int(video_id) // 10000 * 10000,
                video_id,
            ), video_id, headers={'Referer': 'https://vxxx.com'})['video']

    def _download_format_object(self, video_id):
        return self._download_json(
            'https://vxxx.com/api/videofile.php?video_id={}'.format(video_id),
            video_id,
            headers={'Referer': 'https://vxxx.com'}
        )

    def _get_video_host(self):
        return 'vxxx.com'

    def _decode_base164(self, text):
        alphabet = [*'АВСDЕFGHIJKLМNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.,~']
        bit_str = ''
        text_str = ''

        for char in text:
            if char in alphabet:
                bin_char = bin(alphabet.index(char)).lstrip("0b")
                bin_char = bin_char.zfill(6)
                bit_str += bin_char

        brackets = [bit_str[x:x + 8] for x in range(0, len(bit_str), 8)]

        for bracket in brackets:
            text_str += chr(int(bracket, 2))

        return text_str

    def _extract_info(self, url):
        mobj = re.match(self._VALID_URL, url)
        id = mobj.group('id')

        info_object = self._download_info_object(id)

        info = {
            'id': id,
            'title': info_object['title'],
            'display_id': info_object['dir'],
            'thumbnail': info_object['thumb'],
            'description': info_object['description'],
            'timestamp': unified_timestamp(info_object['post_date']),
            'duration': parse_duration(info_object['duration']),
            'view_count': int(info_object['statistics']['viewed']),
            'like_count': int(info_object['statistics']['likes']),
            'dislike_count': int(info_object['statistics']['dislikes']),
            'average_rating': float(info_object['statistics']['rating']),
            'categories': [category['title'] for category in info_object['categories'].values()],
            'formats': None
        }

        qualities = {
            '_hd.mp4': -1,
            '_sd.mp4': -2
        }

        format_object = self._download_format_object(id)
        formats = list(map(lambda f: {
            'url': "https://{}{}".format(
                self._get_video_host(),
                self._decode_base164(f['video_url'])
            ),
            'format_id': f['format'],
            'quality': qualities.get(f['format'], -1)
        }, format_object))
        self._sort_formats(formats)

        info['formats'] = formats
        return info

    def _real_extract(self, url):
        info = self._extract_info(url)

        if not info['formats']:
            return self.url_result(url, 'Generic')

        return info
