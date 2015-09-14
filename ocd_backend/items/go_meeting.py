from datetime import datetime
import json
from pprint import pprint
from hashlib import sha1
from time import sleep
import re

from lxml import etree
import iso8601

from ocd_backend.items.popolo import EventItem
from ocd_backend.utils.misc import slugify
from ocd_backend import settings
from ocd_backend.extractors import HttpRequestMixin
from ocd_backend.utils.api import FrontendAPIMixin
from ocd_backend.utils.pdf import PDFToTextMixin


class MeetingItem(
        EventItem, HttpRequestMixin, FrontendAPIMixin, PDFToTextMixin):

    @property
    def html(self):
        _old_html = getattr(self, '_html', None)

        if _old_html is not None:
            return _old_html

        self._html = etree.HTML(self.original_item['content'])
        return self._html

    @property
    def full_html(self):
        _old_html = getattr(self, '_full_html', None)

        if _old_html is not None:
            return _old_html

        self._full_html = etree.HTML(self.original_item['full_content'])
        return self._full_html

    def _get_council(self):
        """
        Gets the organisation that represents the council.
        """

        results = self.api_request(
            self.source_definition['index_name'], 'organisations',
            classification='council')
        return results[0]

    def _find_meeting_type_id(self, org):
        results = [x for x in org['identifiers'] if x['scheme'] == u'GemeenteOplossingen']
        return results[0]['identifier']

    def _get_committees(self):
        """
        Gets the committees that are active for the council.
        """

        results = self.api_request(
            self.source_definition['index_name'], 'organisations',
            classification=['committee', 'subcommittee'])
        return {self._find_meeting_type_id(c): c for c in results}

    def _convert_date(self, date_str):
        month_names2int = {
            u'januari': u'01',
            u'februari': u'02',
            u'maart': u'03',
            u'april': u'04',
            u'mei': u'05',
            u'juni': u'06',
            u'juli': u'07',
            u'augustus': u'08',
            u'september': u'09',
            u'oktober': u'10',
            u'november': u'11',
            u'december': u'12',
        }
        output = date_str
        for k, v in month_names2int.iteritems():
            output = output.replace(k, v)
        pprint(output)
        parts = output.split(u' ')
        return u'%s-%s-%s' % (parts[2], parts[1], parts[0],)

    def _get_object_id_for(self, object_id, urls={}):
        """Generates a new object ID which is used within OCD to identify
        the item.

        By default, we use a hash containing the id of the source, the
        original object id of the item (:meth:`~.get_original_object_id`)
        and the original urls (:meth:`~.get_original_object_urls`).

        :raises UnableToGenerateObjectId: when both the original object
            id and urls are missing.
        :rtype: str
        """

        if not object_id and not urls:
            raise UnableToGenerateObjectId('Both original id and urls missing')

        hash_content = self.source_definition['id'] + object_id + u''.join(sorted(urls.values()))

        return sha1(hash_content.decode('utf8')).hexdigest()

    def _get_meeting_item_details(self, contents):
        items = []
        html = etree.HTML(contents)
        for row in html.xpath('//table[@id="agenda_print"]//tr'):
            ap = row.xpath('.//td[@class="print_agendapunt"]')
            if len(ap) <= 0:
                continue
            cells = row.xpath('.//td')
            item = {
                'index': u''.join(cells[1].xpath('.//text()')).strip(),
                'title': u'%s. %s' % (
                    u''.join(cells[1].xpath('.//text()')).strip(),
                    u''.join(cells[2].xpath('.//text()')).strip().split(u'\n')[0],),
                'description': u''.join(cells[2].xpath('.//text()')).strip(),
                'documents': int(
                    u''.join(cells[3].xpath('.//text()')).strip()),

            }
            items.append(item)
        return items

    def get_original_object_id(self):
        if self.original_item['type'] == 'meeting':
            return u''.join(
                self.full_html.xpath('//meta[@property="og:url"]/@content')).strip()
        else:
            return u'https://gemeenteraad.denhelder.nl%s' % (
                u''.join(self.html.xpath('.//div[@class="first"]/a/@href')),)

    def get_original_object_urls(self):
        # FIXME: what to do when there is not an original URL?
        return {"html": self.get_original_object_id()}

    def get_rights(self):
        return u'undefined'

    def get_collection(self):
        return u''.join(self.full_html.xpath('//title/text()')).strip()

    def get_combined_index_data(self):
        combined_index_data = {}

        council = self._get_council()
        committees = self._get_committees()

        combined_index_data['id'] = unicode(self.get_object_id())

        combined_index_data['hidden'] = self.source_definition['hidden']

        if self.original_item['type'] == 'meeting':
            combined_index_data['name'] = u''.join(
                self.full_html.xpath('//title/text()')).strip()
            combined_index_data['classification'] = u'Meeting'
        else:
            combined_index_data['name'] = u'%s. %s' % (
                u''.join(self.html.xpath('.//div[@class="first"]//text()')).strip(),
                u''.join(self.html.xpath('.//div[@class="title"]//text()')).strip(),
            )
            combined_index_data['classification'] = u'Meeting Item'

        combined_index_data['identifiers'] = [
            {
                'identifier': unicode(self.get_original_object_id()),
                'scheme': u'GemeenteOplossingen'
            },
            {
                'identifier': self.get_object_id(),
                'scheme': u'ORI'
            }
        ]

        organisation_name = u''.join(
            self.full_html.xpath('//h2[@class="page_title"]/span//text()'))
        try:
            combined_index_data['organisation_id'] = committees[
                organisation_name]['id']
            combined_index_data['organisation'] = committees[
                organisation_name]
        except KeyError as e:
            combined_index_data['organisation_id'] = council['id']
            combined_index_data['organisation'] = council

        combined_index_data['description'] = u''


        meeting_date = u''.join(
             self.full_html.xpath('//span[@class="date"]//text()')).strip()
        meeting_time = u''.join(
             self.full_html.xpath('//span[@class="time"]//text()')).strip()

        combined_index_data['start_date'] = iso8601.parse_date(u'%sT%s:00Z' % (
            self._convert_date(meeting_date), meeting_time,))
        combined_index_data['end_date'] = combined_index_data['start_date']

        combined_index_data['location'] = u'Gemeentehuis'
        combined_index_data['status'] = u'confirmed'
        combined_index_data['sources'] = []

        if self.original_item['type'] != 'meeting':
            parent_url = u''.join(
                self.full_html.xpath('//meta[@property="og:url"]/@content')).strip()
            combined_index_data['parent_id'] = unicode(self._get_object_id_for(
                parent_url, {"html": parent_url}))

            # FIXME: in order to get the documents for an meeting item you
            # need to do a separate request:
            # https://gemeenteraad.denhelder.nl/modules/risbis/risbis.php?g=get_docs_for_ag&agendapunt_object_id=19110
        else:
            combined_index_data['children'] = [
                unicode(self._get_object_id_for(
                    i, {"html": i}
                )) for i in self.full_html.xpath(
                    '//li[contains(@class, "agendaRow")]/div[@class="first"]/a/@href'
            )]

            base_url = u''.join(
                self.full_html.xpath('//meta[@property="og:url"]/@content')).strip()[:-6]

            for doc in self.full_html.xpath('//div[@id="documenten"]//li/a'):
                doc_url = u''.join(doc.xpath('.//@href')).strip()
                doc_note = u''.join(doc.xpath('.//text()')).strip()
                if doc_note != u'notitie':
                    combined_index_data['sources'].append({
                        'url': u'%s%s' % (base_url, doc_url,),
                        'note': doc_note
                    })

            # FIXME: don't forget the link to the mp3

        #
        # try:
        #     documents = self.original_item['Documents']
        # except KeyError as e:
        #     documents = []
        # if documents is None:
        #     documents = []
        #
        # for document in documents:
        #     # sleep(1)
        #     print u"%s: %s" % (
        #         combined_index_data['name'], document['DisplayName'],)
        #     combined_index_data['sources'].append({
        #         'url': document['PublicDownloadURL'],
        #         'note': document['DisplayName'],
        #         # FIXME: some attachments are huuuuuge (>1,000 pages)
        #         # TODO: what to do about those?
        #         # FIXME: we should have resolver URLs for these ...
        #         #'description': self.pdf_get_contents(
        #         #    document['PublicDownloadURL'])
        #     })

        return combined_index_data

    def get_index_data(self):
        return {}

    def get_all_text(self):
        text_items = []

        return u' '.join(text_items)
