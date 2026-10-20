"""Acquire the original icon artwork without changing desktop packages."""

import hashlib
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from preview import (
    FOOD_ORDER_ICON_ARCHIVE, EVERYDAY_ICON_ARCHIVE, BROAD_ICON_ARCHIVE, COMPANION_ICON_ARCHIVE, FIRST_APP_ICON_ARCHIVE, ICON_ARCHIVE, ICON_CHECKSUMS, LEGACY_ICON_ARCHIVE, MONOCHROME_ICON_ARCHIVE,
    PREVIOUS_ICON_ARCHIVE, SECOND_APP_ICON_ARCHIVE, THIRD_APP_ICON_ARCHIVE, PORTABLE_ARCHIVE, ROOT, preview_files,
)
from themeforge.build import build_release
from themeforge.icons import render_icons


FUNCTIONS = (
    'phone messages contacts camera gallery settings calendar clock files notes mail '
    'browser maps music video store wallet calculator weather health fitness '
    'voice-recorder home search'
).split()
FIRST_APPS = (
    ('google-chrome', 'Google Chrome', 'com.android.chrome'),
    ('youtube', 'YouTube', 'com.google.android.youtube'),
    ('google-maps', 'Google Maps', 'com.google.android.apps.maps'),
    ('gmail', 'Gmail', 'com.google.android.gm'),
    ('google-photos', 'Google Photos', 'com.google.android.apps.photos'),
    ('google-messages', 'Google Messages', 'com.google.android.apps.messaging'),
    ('google-calendar', 'Google Calendar', 'com.google.android.calendar'),
    ('google-drive', 'Google Drive', 'com.google.android.apps.docs'),
    ('samsung-browser', 'Samsung Browser', 'com.sec.android.app.sbrowser'),
    ('samsung-notes', 'Samsung Notes', 'com.samsung.android.app.notes'),
    ('samsung-health', 'Samsung Health', 'com.sec.android.app.shealth'),
    ('garmin-connect', 'Garmin Connect', 'com.garmin.android.apps.connectmobile'),
    ('whatsapp', 'WhatsApp', 'com.whatsapp'),
    ('messenger', 'Messenger', 'com.facebook.orca'),
    ('instagram', 'Instagram', 'com.instagram.android'),
    ('facebook', 'Facebook', 'com.facebook.katana'),
    ('snapchat', 'Snapchat', 'com.snapchat.android'),
    ('tiktok', 'TikTok', 'com.zhiliaoapp.musically'),
    ('discord', 'Discord', 'com.discord'),
    ('reddit', 'Reddit', 'com.reddit.frontpage'),
    ('pinterest', 'Pinterest', 'com.pinterest'),
    ('telegram', 'Telegram', 'org.telegram.messenger'),
    ('spotify', 'Spotify', 'com.spotify.music'),
    ('netflix', 'Netflix', 'com.netflix.mediaclient'),
    ('amazon-shopping', 'Amazon Shopping', 'com.amazon.mShop.android.shopping'),
    ('walmart', 'Walmart', 'com.walmart.android'),
    ('temu', 'Temu', 'com.einnovation.temu'),
    ('uber', 'Uber', 'com.ubercab'),
    ('doordash', 'DoorDash', 'com.dd.doordash'),
    ('paypal', 'PayPal', 'com.paypal.android.p2pmobile'),
    ('outlook', 'Microsoft Outlook', 'com.microsoft.office.outlook'),
    ('chatgpt', 'ChatGPT', 'com.openai.chatgpt'),
    ('firefox', 'Firefox', 'org.mozilla.firefox'),
)
ADDITIONAL_APPS = (
    ('x', 'X', 'com.twitter.android'),
    ('threads', 'Threads', 'com.instagram.barcelona'),
    ('signal', 'Signal', 'org.thoughtcrime.securesms'),
    ('twitch', 'Twitch', 'tv.twitch.android.app'),
    ('capcut', 'CapCut', 'com.lemon.lvoverseas'),
    ('disney-plus', 'Disney+', 'com.disney.disneyplus'),
    ('prime-video', 'Prime Video', 'com.amazon.avod.thirdpartyclient'),
    ('microsoft-teams', 'Teams', 'com.microsoft.teams'),
    ('zoom', 'Zoom', 'us.zoom.videomeetings'),
    ('google-meet', 'Google Meet', 'com.google.android.apps.tachyon'),
    ('google-docs', 'Google Docs', 'com.google.android.apps.docs.editors.docs'),
    ('google-sheets', 'Google Sheets', 'com.google.android.apps.docs.editors.sheets'),
    ('onedrive', 'OneDrive', 'com.microsoft.skydrive'),
    ('google-translate', 'Google Translate', 'com.google.android.apps.translate'),
    ('google-keep', 'Google Keep', 'com.google.android.keep'),
    ('google-wallet', 'Google Wallet', 'com.google.android.apps.walletnfcrel'),
    ('cash-app', 'Cash App', 'com.squareup.cash'),
    ('venmo', 'Venmo', 'com.venmo'),
    ('ebay', 'eBay', 'com.ebay.mobile'),
    ('mcdonalds', "McDonald's", 'com.mcdonalds.app'),
    ('starbucks', 'Starbucks', 'com.starbucks.mobilecard'),
    ('duolingo', 'Duolingo', 'com.duolingo'),
    ('waze', 'Waze', 'com.waze'),
    ('canva', 'Canva', 'com.canva.editor'),
)
THIRD_APPS = (
    ('linkedin', 'LinkedIn', 'com.linkedin.android'),
    ('github', 'GitHub', 'com.github.android'),
    ('notion', 'Notion', 'notion.id'),
    ('microsoft-edge', 'Microsoft Edge', 'com.microsoft.emmx'),
    ('brave', 'Brave', 'com.brave.browser'),
    ('microsoft-authenticator', 'Microsoft Authenticator', 'com.azure.authenticator'),
    ('google-authenticator', 'Google Authenticator', 'com.google.android.apps.authenticator2'),
    ('samsung-smartthings', 'SmartThings', 'com.samsung.android.oneconnect'),
)
COMPANION_APPS = (
    ('good-lock', 'Good Lock', 'com.samsung.android.goodlock'),
    ('connect-iq-store', 'Connect IQ Store', 'com.garmin.connectiq'),
    ('steam', 'Steam', 'com.valvesoftware.android.steam.community'),
    ('reuters', 'Reuters', 'com.thomsonreuters.reuters'),
    ('home-depot', 'Home Depot', 'com.thehomedepot'),
    ('patreon', 'Patreon', 'com.patreon.android'),
)
BROAD_APPS = (
    ('youtube-music', 'YouTube Music', 'com.google.android.apps.youtube.music'),
    ('audible', 'Audible', 'com.audible.application'),
    ('amazon-kindle', 'Amazon Kindle', 'com.amazon.kindle'),
    ('pocket-casts', 'Pocket Casts', 'au.com.shiftyjelly.pocketcasts'),
    ('vlc', 'VLC', 'org.videolan.vlc'),
    ('shazam', 'Shazam', 'com.shazam.android'),
    ('soundcloud', 'SoundCloud', 'com.soundcloud.android'),
    ('hulu', 'Hulu', 'com.hulu.plus'),
    ('target', 'Target', 'com.target.ui'),
    ('costco', 'Costco', 'com.costco.app.android'),
    ('best-buy', 'Best Buy', 'com.bestbuy.android'),
    ('etsy', 'Etsy', 'com.etsy.android'),
    ('aliexpress', 'AliExpress', 'com.alibaba.aliexpresshd'),
    ('shein', 'SHEIN', 'com.zzkko'),
    ('instacart', 'Instacart', 'com.instacart.client'),
    ('airbnb', 'Airbnb', 'com.airbnb.android'),
    ('booking', 'Booking.com', 'com.booking'),
    ('expedia', 'Expedia', 'com.expedia.bookings'),
    ('lyft', 'Lyft', 'me.lyft.android'),
    ('uber-eats', 'Uber Eats', 'com.ubercab.eats'),
    ('google-earth', 'Google Earth', 'com.google.earth'),
    ('google-news', 'Google News', 'com.google.android.apps.magazines'),
    ('galaxy-wearable', 'Galaxy Wearable', 'com.samsung.android.app.watchmanager'),
    ('files-by-google', 'Files by Google', 'com.google.android.apps.nbu.files'),
    ('adobe-acrobat', 'Adobe Acrobat', 'com.adobe.reader'),
    ('microsoft-word', 'Microsoft Word', 'com.microsoft.office.word'),
    ('microsoft-excel', 'Microsoft Excel', 'com.microsoft.office.excel'),
    ('microsoft-powerpoint', 'PowerPoint', 'com.microsoft.office.powerpoint'),
    ('google-slides', 'Google Slides', 'com.google.android.apps.docs.editors.slides'),
    ('google-lens', 'Google Lens', 'com.google.ar.lens'),
    ('roblox', 'Roblox', 'com.roblox.client'),
    ('minecraft', 'Minecraft', 'com.mojang.minecraftpe'),
)
# Independent labels/packages from the frozen official identity intake.
EVERYDAY_APPS = (
    ("slack", "Slack", "com.Slack"),
    ("trello", "Trello", "com.trello"),
    ("todoist", "Todoist", "com.todoist"),
    ("ticktick", "TickTick", "com.ticktick.task"),
    ("evernote", "Evernote", "com.evernote"),
    ("obsidian", "Obsidian", "md.obsidian"),
    ("dropbox", "Dropbox", "com.dropbox.android"),
    ("proton-mail", "Proton Mail", "ch.protonmail.android"),
    ("yahoo-mail", "Yahoo Mail", "com.yahoo.mobile.client.android.mail"),
    ("google-tasks", "Google Tasks", "com.google.android.apps.tasks"),
    ("google-one", "Google One", "com.google.android.apps.subscriptions.red"),
    ("microsoft-copilot", "Microsoft Copilot", "com.microsoft.office.officehubrow"),
    ("google-gemini", "Google Gemini", "com.google.android.apps.bard"),
    ("claude", "Claude", "com.anthropic.claude"),
    ("perplexity", "Perplexity", "ai.perplexity.app.android"),
    ("bitwarden", "Bitwarden", "com.x8bit.bitwarden"),
    ("apple-music", "Apple Music", "com.apple.android.music"),
    ("apple-tv", "Apple TV", "com.apple.atve.androidtv.appletv"),
    ("hbo-max", "HBO Max", "com.wbd.stream"),
    ("peacock", "Peacock", "com.peacocktv.peacockandroid"),
    ("paramount-plus", "Paramount+", "com.cbs.app"),
    ("plex", "Plex", "com.plexapp.android"),
    ("tubi", "Tubi", "com.tubitv"),
    ("pluto-tv", "Pluto TV", "tv.pluto.android"),
    ("crunchyroll", "Crunchyroll", "com.crunchyroll.crunchyroid"),
    ("pandora", "Pandora", "com.pandora.android"),
    ("iheartradio", "iHeart", "com.clearchannel.iheartradio.controller"),
    ("siriusxm", "SiriusXM", "com.sirius"),
    ("adobe-lightroom", "Adobe Lightroom", "com.adobe.lrmobile"),
    ("photoshop-express", "Photoshop Express", "com.adobe.psmobile"),
    ("snapseed", "Snapseed", "com.niksoftware.snapseed"),
    ("picsart", "Picsart", "com.picsart.studio"),
    ("strava", "Strava", "com.strava"),
    ("fitbit", "Google Health (Fitbit)", "com.fitbit.FitbitMobile"),
    ("google-fit", "Google Fit", "com.google.android.apps.fitness"),
    ("myfitnesspal", "MyFitnessPal", "com.myfitnesspal.android"),
    ("alltrails", "AllTrails", "com.alltrails.alltrails"),
    ("komoot", "Komoot", "de.komoot.android"),
    ("amazon-alexa", "Amazon Alexa", "com.amazon.dee.app"),
    ("ring", "Ring", "com.ringapp"),
    ("blink", "Blink", "com.immediasemi.android.blink"),
    ("google-home", "Google Home", "com.google.android.apps.chromecast.app"),
    ("zillow", "Zillow", "com.zillow.android.zillowmap"),
    ("chase", "Chase", "com.chase.sig.android"),
    ("capital-one", "Capital One", "com.konylabs.capitalone"),
    ("chime", "Chime", "com.onedebit.chime"),
    ("ups", "UPS", "com.ups.mobile.android"),
    ("fedex", "FedEx", "com.fedex.ida.android"),
)
FOOD_ORDER_APPS = (
    ('chipotle', 'Chipotle', 'com.chipotle.ordering'),
    ('taco-bell', 'Taco Bell', 'com.tacobell.ordering'),
    ('wendys', "Wendy's", 'com.wendys.nutritiontool'),
    ('burger-king', 'Burger King', 'com.emn8.mobilem8.nativeapp.bk'),
    ('dunkin', "Dunkin'", 'com.dunkinbrands.otgo'),
    ('chick-fil-a', 'Chick-fil-A', 'com.chickfila.cfaflagship'),
    ('dominos', "Domino's", 'com.dominospizza'),
    ('pizza-hut', 'Pizza Hut', 'com.yum.pizzahut'),
    ('subway', 'Subway', 'com.subway.mobile.subwayapp03'),
    ('panera-bread', 'Panera Bread', 'com.panera.bread'),
    ('kfc-us', 'KFC US', 'com.kfc.us.mobile'),
    ('grubhub', 'Grubhub', 'com.grubhub.android'),
)
TRAVEL_APPS = (
    ('fly-delta', 'Fly Delta', 'com.delta.mobile.android'),
    ('united-airlines', 'United Airlines', 'com.united.mobile.android'),
    ('american-airlines', 'American Airlines', 'com.aa.android'),
    ('southwest-airlines', 'Southwest Airlines', 'com.southwestairlines.mobile'),
    ('amtrak', 'Amtrak', 'com.amtrak.rider'),
    ('transit', 'Transit', 'com.thetransitapp.droid'),
    ('moovit', 'Moovit', 'com.tranzmate'),
    ('citymapper', 'Citymapper', 'com.citymapper.app.release'),
    ('tripit', 'TripIt', 'com.tripit'),
    ('hopper', 'Hopper', 'com.hopper.mountainview.play'),
)
APPS = FIRST_APPS + ADDITIONAL_APPS + THIRD_APPS + COMPANION_APPS + BROAD_APPS + EVERYDAY_APPS + FOOD_ORDER_APPS + TRAVEL_APPS
CURRENT_IDS = FUNCTIONS + [row[0] for row in APPS]
GALLERY_IDS = [row[0] for row in APPS] + FUNCTIONS
LABELS = {**{name: name.replace('-', ' ').title() for name in FUNCTIONS},
          **{name: label for name, label, _ in APPS}}


def snapshot(directory):
    return {path.relative_to(directory).as_posix(): path.read_bytes()
            for path in directory.rglob('*') if path.is_file()}


class IconMarkup(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.cards, self.links = [], []
        self.card = None
        self.heading = False
        self.code = False
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'article' and 'icon-card' in attrs.get('class', '').split():
            self.card = {'attrs': attrs, 'images': [], 'heading': '', 'links': [], 'buttons': [], 'package': ''}
            self.cards.append(self.card)
        elif tag == 'img' and self.card is not None:
            self.card['images'].append(attrs)
        elif tag == 'h4' and self.card is not None:
            self.heading = True
        elif tag == 'code' and self.card is not None:
            self.code = True
        elif tag == 'button' and self.card is not None:
            self.card['buttons'].append(attrs)
        if tag == 'a':
            self.links.append(attrs)
            if self.card is not None:
                self.card['links'].append(attrs)

    def handle_endtag(self, tag):
        if tag == 'article':
            self.card = None
        if tag == 'h4':
            self.heading = False
        if tag == 'code':
            self.code = False

    def handle_data(self, data):
        if self.heading and self.card is not None:
            self.card['heading'] += data
        if self.code and self.card is not None:
            self.card['package'] += data


class PreviewIconTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.artifacts = Path(self.temporary.name) / 'artifacts'
        build_release(ROOT / 'tokens.json', self.artifacts)
        self.original = snapshot(self.artifacts)

    def test_current_artwork_archive_matches_gallery_and_preserves_original_archive(self):
        files = preview_files(ROOT, self.artifacts)
        document = json.loads((ROOT / 'tokens.json').read_bytes())
        monochrome = json.loads((ROOT / 'tokens-monochrome.json').read_bytes())
        expected = render_icons(monochrome)
        retained = render_icons(document, version='0.5.0')
        manifest = json.loads(expected['manifest.json'])
        self.assertEqual(manifest['version'], '0.11.0')
        self.assertEqual(manifest['functions'], CURRENT_IDS)
        self.assertEqual(len(expected), len(CURRENT_IDS) * 2 + 1)
        expected['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        for name, payload in expected.items():
            self.assertEqual(files[f'icons/{name}'], payload)
        with zipfile.ZipFile(io.BytesIO(files[ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), len(CURRENT_IDS) * 2 + 2)
            self.assertEqual(set(archive.namelist()), set(expected))
            for name, payload in expected.items():
                self.assertEqual(archive.read(name), payload)
        legacy = render_icons(document, version='0.1.0')
        legacy['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[LEGACY_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 50)
            self.assertEqual(set(archive.namelist()), set(legacy))
            for name, payload in legacy.items():
                self.assertEqual(archive.read(name), payload)
        self.assertEqual(hashlib.sha256(files[LEGACY_ICON_ARCHIVE]).hexdigest(),
                         '040d7f472ca12d6cf115daaf2631b83477183dee42f0b91c6133e62322014e34')
        previous = render_icons(document, version='0.2.0')
        previous['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[PREVIOUS_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 50)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous)
        self.assertEqual(hashlib.sha256(files[PREVIOUS_ICON_ARCHIVE]).hexdigest(),
                         '6ae67a5aab7f4e0a50537bb6dcf3b383c5fc6e9e001d68db12a7413aaa376312')
        first_apps = render_icons(document, version='0.3.0')
        first_apps['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[FIRST_APP_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 116)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, first_apps)
            self.assertEqual(json.loads(archive.read('manifest.json'))['functions'],
                             FUNCTIONS + [row[0] for row in FIRST_APPS])
        self.assertEqual(hashlib.sha256(files[FIRST_APP_ICON_ARCHIVE]).hexdigest(),
                         'd217cab68c1c118511078c189ec672b80cbcb29be285bf5cc58123516791e756')
        for path, payload in first_apps.items():
            if path.endswith('.svg'):
                self.assertEqual(retained[path], payload)
        second_apps = render_icons(document, version='0.4.0')
        second_apps['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[SECOND_APP_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 164)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, second_apps)
            self.assertEqual(json.loads(archive.read('manifest.json'))['functions'],
                             FUNCTIONS + [row[0] for row in FIRST_APPS + ADDITIONAL_APPS])
        self.assertEqual(hashlib.sha256(files[SECOND_APP_ICON_ARCHIVE]).hexdigest(),
                         'fc2540a7bf9a6d580a3238904b6e7e4f6b77ca5df5797cc7ce3a6de782cda0cf')
        for path, payload in second_apps.items():
            if path.endswith('.svg'):
                self.assertEqual(retained[path], payload)
        retained['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[THIRD_APP_ICON_ARCHIVE])) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, retained)
        self.assertEqual(hashlib.sha256(files[THIRD_APP_ICON_ARCHIVE]).hexdigest(),
                         '2310c0151c0c3215e99d24a7aa92616a55dc726b2e38466427890223d778307a')
        previous_monochrome = render_icons(monochrome, version='0.6.0')
        previous_monochrome['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[MONOCHROME_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 180)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_monochrome)
        self.assertEqual(hashlib.sha256(files[MONOCHROME_ICON_ARCHIVE]).hexdigest(),
                         '241efb1fe6584df4f66c84571bfe671059404e83be8d67876f415af6564a56bb')
        for path, payload in previous_monochrome.items():
            if path.endswith('.svg'):
                self.assertEqual(expected[path], payload)
        previous_companion = render_icons(monochrome, version='0.7.0')
        previous_companion['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[COMPANION_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 192)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_companion)
        self.assertEqual(hashlib.sha256(files[COMPANION_ICON_ARCHIVE]).hexdigest(),
                         'aa18db922e824cd2bfa1ada2fbc08125af2605d9c5acb2ad8bfdb439985f4f05')
        for path, payload in previous_companion.items():
            if path.endswith('.svg'):
                self.assertEqual(expected[path], payload)
        previous_broad = render_icons(monochrome, version='0.8.0')
        previous_broad['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[BROAD_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 256)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_broad)
            self.assertEqual(hashlib.sha256(archive.read('manifest.json')).hexdigest(),
                             '7a8a35d6ba1186a718e970e26c5c6b7b19bf4949010c7bc89af3cb6063b95252')
        self.assertEqual(hashlib.sha256(files[BROAD_ICON_ARCHIVE]).hexdigest(),
                         'fcdaec582be7508b3e62bd9168695ea1650e33c8e53c3de46f3614ae53d833cf')
        self.assertEqual(json.loads(previous_broad['manifest.json'])['catalog'], manifest['catalog'][:127])
        for path, payload in previous_broad.items():
            if path.endswith('.svg'):
                self.assertEqual(expected[path], payload)
        previous_everyday = render_icons(monochrome, version='0.9.0')
        previous_everyday['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[EVERYDAY_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 352)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_everyday)
        self.assertEqual(hashlib.sha256(files[EVERYDAY_ICON_ARCHIVE]).hexdigest(),
                         '994ce1d819414b06062d5cd32a03eeb8891e9074b09491dfb2c774a55ae5a3b1')
        self.assertEqual(json.loads(previous_everyday['manifest.json'])['catalog'], manifest['catalog'][:175])
        for path, payload in previous_everyday.items():
            if path.endswith('.svg'):
                self.assertEqual(expected[path], payload)
        previous_food_order = render_icons(monochrome, version='0.10.0')
        previous_food_order['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[FOOD_ORDER_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 376)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_food_order)
        self.assertEqual(hashlib.sha256(files[FOOD_ORDER_ICON_ARCHIVE]).hexdigest(),
                         'a81ffb8c4fb3ef32f3c8391c53016e99246b755ce9079fdee84b5948790ab8e0')
        previous_food_manifest = json.loads(previous_food_order['manifest.json'])
        self.assertEqual(previous_food_manifest['catalog'], manifest['catalog'][:187])
        self.assertEqual(previous_food_manifest['catalog_date'], '2026-10-19')
        self.assertEqual([(row['id'], row['label'], row['android_package'])
                          for row in manifest['catalog'][187:]], list(TRAVEL_APPS))
        for path, payload in previous_food_order.items():
            if path.endswith('.svg'):
                self.assertEqual(expected[path], payload)
        self.assertNotEqual(files[ICON_ARCHIVE], files[LEGACY_ICON_ARCHIVE])
        self.assertEqual(files[ICON_CHECKSUMS],
                         ''.join(f'{hashlib.sha256(files[path]).hexdigest()}  {Path(path).name}\n'
                                 for path in (ICON_ARCHIVE, FOOD_ORDER_ICON_ARCHIVE, EVERYDAY_ICON_ARCHIVE, BROAD_ICON_ARCHIVE, COMPANION_ICON_ARCHIVE, MONOCHROME_ICON_ARCHIVE, THIRD_APP_ICON_ARCHIVE, SECOND_APP_ICON_ARCHIVE, FIRST_APP_ICON_ARCHIVE,
                                              PREVIOUS_ICON_ARCHIVE, LEGACY_ICON_ARCHIVE)).encode())
        repeated = preview_files(ROOT, self.artifacts)
        for path in (ICON_ARCHIVE, FOOD_ORDER_ICON_ARCHIVE, EVERYDAY_ICON_ARCHIVE, BROAD_ICON_ARCHIVE, COMPANION_ICON_ARCHIVE, MONOCHROME_ICON_ARCHIVE, THIRD_APP_ICON_ARCHIVE, SECOND_APP_ICON_ARCHIVE, FIRST_APP_ICON_ARCHIVE,
                     PREVIOUS_ICON_ARCHIVE, LEGACY_ICON_ARCHIVE):
            self.assertEqual(repeated[path], files[path])

    def test_published_and_portable_pages_show_both_appearances_with_local_acquisition(self):
        files = preview_files(ROOT, self.artifacts)
        with zipfile.ZipFile(io.BytesIO(files[PORTABLE_ARCHIVE])) as archive:
            portable = {name: archive.read(name) for name in archive.namelist()}
        for delivery in (files, portable):
            with self.subTest(kind='published' if delivery is files else 'portable'):
                page = delivery['index.html'].decode()
                self.assertNotIn('{{', page)
                markup = IconMarkup(page)
                self.assertEqual([card['attrs']['data-icon-function'] for card in markup.cards], GALLERY_IDS)
                app_packages = {identifier: package for identifier, _, package in APPS}
                for function, card in zip(GALLERY_IDS, markup.cards):
                    label = LABELS[function]
                    self.assertEqual(card['heading'], label)
                    self.assertEqual(card['attrs']['data-icon-kind'], 'function' if function in FUNCTIONS else 'app')
                    self.assertEqual(card['attrs']['data-icon-version'], '0.11.0')
                    package = app_packages.get(function, '')
                    self.assertEqual(card['package'], package)
                    self.assertEqual(card['links'], [] if not package else [{
                        'href': f'https://play.google.com/store/apps/details?id={package}',
                        'rel': 'noreferrer',
                    }])
                    self.assertNotIn('hidden', card['attrs'])
                    self.assertEqual(len(card['images']), 2)
                    self.assertEqual(len(card['buttons']), 2)
                    for appearance, button in zip(('Clair', 'Obscur'), card['buttons']):
                        self.assertEqual(button['type'], 'button')
                        self.assertIn('data-icon-png', button)
                        self.assertEqual(button['data-icon-appearance'], appearance)
                        self.assertEqual(button['data-icon-filename'],
                                         f'Clair-Obscur-0.11.0-{appearance}-{function}-512.png')
                        self.assertIn('hidden', button, 'Unenhanced PNG controls must not be inert visible buttons')
                        self.assertNotIn('data-appearance', button,
                                         'Icon acquisition must not join the page-appearance switcher')
                        self.assertIn(appearance, button['aria-label'])
                        self.assertIn(label, button['aria-label'])
                    for appearance, image in zip(('Clair', 'Obscur'), card['images']):
                        path = f'icons/{appearance}/{function}.svg'
                        self.assertEqual(image['src'], path)
                        self.assertEqual(image['alt'], f'{appearance} {label} icon')
                        self.assertEqual((image['width'], image['height']), ('512', '512'))
                        self.assertEqual(image['decoding'], 'async')
                        self.assertNotIn('loading', image)
                        self.assertNotIn('hidden', image)
                        self.assertEqual(delivery[path], files[path])
                for identifier, _, package in APPS:
                    self.assertIn(f'https://play.google.com/store/apps/details?id={package}', page)
                    self.assertIn(f'<code>{package}</code>', page)
                for path in (ICON_ARCHIVE, FOOD_ORDER_ICON_ARCHIVE, EVERYDAY_ICON_ARCHIVE, BROAD_ICON_ARCHIVE, COMPANION_ICON_ARCHIVE, MONOCHROME_ICON_ARCHIVE, THIRD_APP_ICON_ARCHIVE, SECOND_APP_ICON_ARCHIVE, FIRST_APP_ICON_ARCHIVE,
                             PREVIOUS_ICON_ARCHIVE, LEGACY_ICON_ARCHIVE, ICON_CHECKSUMS):
                    links = [link for link in markup.links if link.get('href') == path]
                    self.assertEqual(len(links), 1)
                    self.assertIn('download', links[0])
                    self.assertEqual(delivery[path], files[path])
                history = {link['id']: link['href'] for link in markup.links if 'id' in link}
                self.assertEqual(history['icon-artwork-download'], ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-food-order-download'], FOOD_ORDER_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-everyday-download'], EVERYDAY_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-broad-download'], BROAD_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-companion-download'], COMPANION_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-monochrome-download'], MONOCHROME_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-second-app-download'], SECOND_APP_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-first-app-download'], FIRST_APP_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-previous-download'], PREVIOUS_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-legacy-download'], LEGACY_ICON_ARCHIVE)
                self.assertEqual([link['id'] for link in markup.links
                                  if link.get('id', '').startswith('icon-artwork-')], [
                    'icon-artwork-download', 'icon-artwork-checksums', 'icon-artwork-food-order-download', 'icon-artwork-everyday-download', 'icon-artwork-broad-download',
                    'icon-artwork-companion-download', 'icon-artwork-monochrome-download',
                    'icon-artwork-third-app-download', 'icon-artwork-second-app-download', 'icon-artwork-first-app-download',
                    'icon-artwork-previous-download',
                    'icon-artwork-legacy-download',
                ])
                manifest = json.loads(delivery['site-manifest.json'])
                for path, payload in delivery.items():
                    if path.startswith('icons/'):
                        self.assertEqual(manifest['files'][path], hashlib.sha256(payload).hexdigest())

    def test_artwork_delivery_keeps_the_original_desktop_tree_and_release_inventory(self):
        files = preview_files(ROOT, self.artifacts)
        self.assertEqual(len(self.original), 32)
        self.assertEqual(snapshot(self.artifacts), self.original)
        downloads = {name.removeprefix('downloads/'): payload
                     for name, payload in files.items() if name.startswith('downloads/')}
        self.assertEqual(downloads, self.original)
        manifest = json.loads(files['downloads/artifact-manifest.json'])
        self.assertEqual(len(manifest['downloads']), 17)
        self.assertEqual(len({item['path'] for item in manifest['downloads']}), 13)
        self.assertFalse(any('icon' in item['path'] for item in manifest['downloads']))
        self.assertNotIn(b'icons/', files['release-SHA256SUMS'])
        self.assertEqual(files['index.html'].count(b'class="download-card"'), 17)

    def test_an_icon_license_read_after_source_capture_cannot_replace_the_captured_grant(self):
        for changed_version in ('0.1.0', '0.2.0', '0.3.0', '0.4.0', '0.5.0', '0.6.0', '0.7.0', '0.8.0', '0.9.0', '0.10.0', '0.11.0'):
            with self.subTest(version=changed_version):
                def changed_grant(document, *, version='0.11.0'):
                    icons = render_icons(document, version=version)
                    if version == changed_version:
                        last = 'Obscur/search.svg'
                        icons[last] = icons[last].replace(b'MIT License', b'Changed grant', 1)
                    return icons

                with patch('preview.render_icons', side_effect=changed_grant):
                    with self.assertRaisesRegex(ValueError, 'Source license differs from the generated icon grant'):
                        preview_files(ROOT, self.artifacts)
                self.assertEqual(snapshot(self.artifacts), self.original)

    def test_current_catalog_cannot_silently_omit_an_app_or_its_visible_label(self):
        for identifier, mutation in (
                ('youtube', 'missing-app'), ('youtube', 'missing-label'),
                ('canva', 'missing-app'), ('canva', 'missing-label'),
                ('samsung-smartthings', 'missing-app'), ('samsung-smartthings', 'missing-label'),
                ('good-lock', 'missing-app'), ('patreon', 'missing-label'),
                ('youtube-music', 'missing-app'), ('minecraft', 'missing-label'),
                ('slack', 'missing-app'), ('fedex', 'missing-label'),
                ('chipotle', 'missing-app'), ('grubhub', 'missing-label'),
                ('fly-delta', 'missing-app'), ('hopper', 'missing-label')):
            def changed_catalog(document, *, version='0.11.0'):
                files = render_icons(document, version=version)
                if version == '0.11.0':
                    manifest = json.loads(files['manifest.json'])
                    if mutation == 'missing-app':
                        manifest['catalog'] = [entry for entry in manifest['catalog'] if entry['id'] != identifier]
                    else:
                        next(entry for entry in manifest['catalog'] if entry['id'] == identifier)['label'] = ''
                    files['manifest.json'] = json.dumps(manifest).encode()
                return files
            with self.subTest(identifier=identifier, mutation=mutation), patch('preview.render_icons', side_effect=changed_catalog):
                with self.assertRaisesRegex(ValueError, 'Icon catalog differs'):
                    preview_files(ROOT, self.artifacts)
            self.assertEqual(snapshot(self.artifacts), self.original)

    def test_current_app_labels_are_escaped_in_headings_and_image_alternatives(self):
        def changed_label(document, *, version='0.11.0'):
            files = render_icons(document, version=version)
            if version == '0.11.0':
                manifest = json.loads(files['manifest.json'])
                next(entry for entry in manifest['catalog'] if entry['id'] == 'youtube')['label'] = '<App & "Name">'
                files['manifest.json'] = json.dumps(manifest).encode()
            return files
        with patch('preview.render_icons', side_effect=changed_label):
            page = preview_files(ROOT, self.artifacts)['index.html'].decode()
        self.assertIn('<h4>&lt;App &amp; &quot;Name&quot;&gt;</h4>', page)
        self.assertIn('alt="Clair &lt;App &amp; &quot;Name&quot;&gt; icon"', page)
        self.assertNotIn('<h4><App', page)


if __name__ == '__main__':
    unittest.main()
