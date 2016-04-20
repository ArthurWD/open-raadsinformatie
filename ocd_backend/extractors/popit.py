import json
from pprint import pprint

from ocd_backend.extractors import HttpRequestMixin
from ocd_backend.exceptions import ConfigurationError
from .staticfile import StaticJSONExtractor


class PopItExtractor(StaticJSONExtractor, HttpRequestMixin):
    """
    Extract items from an OData Feed.
    """

    def extract_items(self, static_content):
        """
        Extracts items from the result of a popit call. Does paging.
        """
        static_json = json.loads(static_content)

        for item in static_json['result']:
            print "%s - %s" % (item.get('meta', {}).get('_type', '-'), item.get('name', '-'),)
            yield 'application/json', json.dumps(item)

        while static_json.get('next_url'):
            result = self.http_session.get(
                static_json['next_url'])
            static_json = result.json()

            for item in static_json['result']:
                print "%s - %s" % (item.get('meta', {}).get('_type', '-'), item.get('name', '-'),)
                yield 'application/json', json.dumps(item)
