import re
import json
import urllib
import logging

from urlparse import urlparse

from django.core.management.base import BaseCommand

from chronam.core.models import Page, FlickrUrl

LOGGER = logging.getLogger(__name__)

class Command(BaseCommand):
    args = '<flickr_key>'
    help = 'load links for content that has been pushed to flickr.'

    def handle(self, key, **options):
        LOGGER.debug("looking for chronam page content on flickr")
        create_count = 0

        for flickr_url, chronam_url in flickr_chronam_links(key):
            LOGGER.info("found flickr/chronam link: %s, %s" % 
                         (flickr_url, chronam_url))

            # use the page url to locate the Page model
            path = urlparse(chronam_url).path
            page = Page.lookup(path)
            if not page:
                LOGGER.error("page for %s not found" % chronam_url)
                continue

            # create the FlickrUrl attached to the apprpriate page
            f, created = FlickrUrl.objects.get_or_create(value=flickr_url, 
                                                         page=page)
            if created:
                create_count += 1
                f.save()
                LOGGER.info("updated page (%s) with flickr url (%s)" % 
                          (page, flickr_url))
            else:
                LOGGER.info("already knew about %s" % flickr_url)

        LOGGER.info("created %s flickr urls" % create_count)
    

def photos_in_set(key, set_id):
    """A generator for all the photos in a set. 
    """
    u = 'http://api.flickr.com/services/rest/?method=flickr.photosets.getPhotos&api_key=%s&photoset_id=%s&format=json&nojsoncallback=1' % (key, set_id)
    photos = json.loads(urllib.urlopen(u).read())
    for p in photos['photoset']['photo']:
        yield photo(key, p['id'])


def photo(key, photo_id):
    """Return JSON for a given photo.
    """
    u = 'http://api.flickr.com/services/rest/?method=flickr.photos.getInfo&api_key=%s&photo_id=%s&format=json&nojsoncallback=1' % (key, photo_id)
    return json.loads(urllib.urlopen(u).read())


def flickr_url(photo):
    for url in photo['photo']['urls']['url']:
        if url['type'] == 'photopage':
            return url['_content']
    return None


def chronam_url(photo):
    """Tries to find a chronam link in the photo metadata
    """
    # libraryofcongress photos are uploaded with a machinetag
    for tag in photo['photo']['tags']['tag']:
        if 'chroniclingamerica.loc.gov' in tag['raw']:
            return tag['raw'].replace('dc:identifier=', '')
   
    # some other photos might have a link in the textual description
    m = re.search('"(http://chroniclingamerica.loc.gov/.+?)"',
    photo['photo']['description']['_content'])
    if m:
        return m.group(1)

    return None


def flickr_chronam_links(key):
    """
    A generator that returns a tuple of flickr urls, and their corresponding
    chroniclingamerica.loc.gov page url.
    """
    # these are two flickr sets that have known chronam content
    for set_id in [72157600479553448, 72157619452486566]:
        for photo in photos_in_set(key, set_id):
            chronam = chronam_url(photo)
            # not all photos in set will have a link to chronam
            if chronam:
                yield flickr_url(photo), chronam
