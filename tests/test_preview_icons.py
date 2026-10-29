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
    CRAFT_ICON_ARCHIVE, ART_DIRECTION_ICON_ARCHIVE, IDENTITY_ICON_ARCHIVE, ROUTE_ICON_ARCHIVE, COMMUNICATION_ICON_ARCHIVE, MESSAGING_ICON_ARCHIVE, CONTACT_SPACED_ICON_ARCHIVE, CONTAINED_ICON_ARCHIVE, SPACED_ICON_ARCHIVE, POLISHED_ICON_ARCHIVE, VIDEO_EDITING_ICON_ARCHIVE, GBOARD_ICON_ARCHIVE, REFINED_ICON_ARCHIVE, PHONE_SERVICE_ICON_ARCHIVE, READING_ICON_ARCHIVE, LEARNING_ICON_ARCHIVE, RUNNING_TRAINING_ICON_ARCHIVE, WEATHER_ICON_ARCHIVE, FINANCE_ICON_ARCHIVE, TRAVEL_ICON_ARCHIVE, FOOD_ORDER_ICON_ARCHIVE, EVERYDAY_ICON_ARCHIVE, BROAD_ICON_ARCHIVE, COMPANION_ICON_ARCHIVE, FIRST_APP_ICON_ARCHIVE, ICON_ARCHIVE, ICON_CHECKSUMS, LEGACY_ICON_ARCHIVE, MONOCHROME_ICON_ARCHIVE,
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
FINANCE_APPS = (
    ('bank-of-america', 'Bank of America', 'com.infonow.bofa'),
    ('wells-fargo', 'Wells Fargo', 'com.wf.wellsfargomobile'),
    ('us-bank', 'U.S. Bank', 'com.usbank.mobilebanking'),
    ('pnc', 'PNC', 'com.pnc.ecommerce.mobile'),
    ('discover', 'Discover', 'com.discoverfinancial.mobile'),
    ('amex', 'Amex', 'com.americanexpress.android.acctsvcs.us'),
    ('fidelity-investments', 'Fidelity Investments', 'com.fidelity.android'),
    ('schwab', 'Schwab', 'com.schwab.mobile'),
    ('sofi', 'SoFi', 'com.sofi.mobile'),
    ('robinhood', 'Robinhood', 'com.robinhood.android'),
)
WEATHER_APPS = (
    ('accuweather', 'AccuWeather', 'com.accuweather.android'),
    ('weather-channel', 'The Weather Channel', 'com.weather.Weather'),
    ('weather-underground', 'Weather Underground', 'com.wunderground.android.weather'),
    ('windy-com', 'Windy.com', 'com.windyty.android'),
    ('myradar', 'MyRadar', 'com.acmeaom.android.myradar'),
    ('weatherbug', 'WeatherBug', 'com.aws.android'),
    ('one-weather', '1Weather', 'com.handmark.expressweather'),
    ('clime', 'Clime', 'com.apalon.weatherradar.free'),
    ('windfinder', 'Windfinder', 'com.studioeleven.windfinder'),
    ('rainviewer', 'RainViewer', 'com.lucky_apps.RainViewer'),
)
RUNNING_TRAINING_APPS = (
    ('nike-run-club', 'Nike Run Club', 'com.nike.plusgps'),
    ('adidas-running', 'adidas Running', 'com.runtastic.android'),
    ('asics-runkeeper', 'ASICS Runkeeper', 'com.fitnesskeeper.runkeeper.pro'),
    ('map-my-run', 'Map My Run', 'com.mapmyrun.android2'),
    ('runna', 'Runna', 'com.runbuddy.prod'),
    ('trainingpeaks', 'TrainingPeaks', 'com.peaksware.trainingpeaks'),
    ('zwift-companion', 'Zwift Companion', 'com.zwift.android.prod'),
    ('relive', 'Relive', 'cc.relive.reliveapp'),
)
LEARNING_APPS = (
    ('google-classroom', 'Google Classroom', 'com.google.android.apps.classroom'),
    ('khan-academy', 'Khan Academy', 'org.khanacademy.android'),
    ('coursera', 'Coursera', 'org.coursera.android'),
    ('udemy', 'Udemy', 'com.udemy.android'),
    ('edx', 'edX', 'org.edx.mobile'),
    ('quizlet', 'Quizlet', 'com.quizlet.quizletandroid'),
    ('photomath', 'Photomath', 'com.microblink.photomath'),
    ('brainly', 'Brainly', 'co.brainly'),
)
READING_APPS = (
    ('google-play-books', 'Google Play Books', 'com.google.android.apps.books'),
    ('libby', 'Libby', 'com.overdrive.mobile.android.libby'),
    ('kobo-books', 'Kobo Books', 'com.kobobooks.android'),
    ('goodreads', 'Goodreads', 'com.goodreads'),
    ('wattpad', 'Wattpad', 'wp.wattpad'),
    ('webtoon', 'WEBTOON', 'com.naver.linewebtoon'),
    ('readera', 'ReadEra', 'org.readera'),
    ('moon-reader', 'Moon+ Reader', 'com.flyersoft.moonreader'),
)
PHONE_SERVICE_APPS = (
    ("ace-hardware","Ace Hardware","com.acehardware.rewards"),
    ("ai-dungeon","AI Dungeon","com.aidungeon"),
    ("gaming-hub","Gaming Hub","com.samsung.android.game.gamehome"),
    ("kroger","Kroger","com.kroger.mobile"),
    ("affirm","Affirm","com.affirm.central"),
    ("usaa","USAA","com.usaa.mobile.android.usaa"),
    ("proton-authenticator","Proton Authenticator","proton.android.authenticator"),
    ("wikipedia","Wikipedia","org.wikipedia"),
    ("xbox","Xbox","com.microsoft.xboxone.smartglass"),
    ("shop","Shop","com.shopify.arrive"),
    ("fandom","Fandom","com.fandom.app"),
    ("shonen-jump","Shonen Jump","com.viz.wsj.android"),
    ("smart-switch","Smart Switch","com.sec.android.easyMover"),
    ("steam-chat","Steam Chat","com.valvesoftware.android.steam.friendsui"),
    ("sonic","Sonic","com.sonic.sonicdrivein"),
    ("samsung-global-goals","Samsung Global Goals","com.samsung.sree"),
    ("theme-park","Theme Park","com.samsung.android.themedesigner"),
    ("zillow-rentals","Zillow Rentals","com.zillow.android.rentals"),
    ("samsung-find","Samsung Find","com.samsung.android.app.find"),
    ("dollar-general","Dollar General","com.dollargeneral.android"),
    ("sound-connect","Sound Connect","com.sony.songpal.mdr"),
    ("samsung-pass","Samsung Pass","com.samsung.android.samsungpass"),
    ("va","VA","gov.va.mobileapp"),
    ("battle-net","Battle.net","com.blizzard.messenger"),
    ("coinbase","Coinbase","com.coinbase.android"),
    ("credit-one","Credit One","com.creditonebank.mobile"),
    ("samsung-members","Samsung Members","com.samsung.android.voc"),
    ("proton-vpn","Proton VPN","ch.protonvpn.android"),
    ("t-life","T-Life","com.tmobile.tuesdays"),
    ("my-spectrum","My Spectrum","com.brighthouse.mybhn"),
    ("g2a","G2A","com.g2a.marketplace"),
    ("samsung-tv-plus","Samsung TV Plus","com.samsung.android.tvplus"),
    ("ap-news","AP News","mnn.Android"),
    ("link-to-windows","Link to Windows","com.microsoft.appmanager"),
    ("tips","Tips","com.samsung.android.app.tips"),
    ("proton-pass","Proton Pass","proton.android.pass"),
    ("shop-samsung","Shop Samsung","com.samsung.ecomm"),
    ("wallpaper-engine","Wallpaper Engine","io.wallpaperengine.weclient"),
    ("asus-router","ASUS Router","com.asus.aihome"),
    ("mochi-health","Mochi Health","com.mochihealth.mochihealth"),
)

GBOARD_APPS = (('gboard', 'Gboard', 'com.google.android.inputmethod.latin'),)
HISTORICAL_APPS = FIRST_APPS + ADDITIONAL_APPS + THIRD_APPS + COMPANION_APPS + BROAD_APPS + EVERYDAY_APPS + FOOD_ORDER_APPS + TRAVEL_APPS + FINANCE_APPS + WEATHER_APPS + RUNNING_TRAINING_APPS + LEARNING_APPS + READING_APPS + PHONE_SERVICE_APPS
VIDEO_EDITING_APPS = (
    ('inshot', 'InShot', 'com.camerasideas.instashot'),
    ('youcut', 'YouCut', 'com.camerasideas.trimmer'),
    ('vn-video-editor', 'VN', 'com.frontrow.vlog'),
    ('kinemaster', 'KineMaster', 'com.nexstreaming.app.kinemasterfree'),
    ('powerdirector', 'PowerDirector', 'com.cyberlink.powerdirector.DRA140225_01'),
    ('filmora', 'Filmora', 'com.wondershare.filmorago'),
    ('vivavideo', 'VivaVideo', 'com.quvideo.xiaoying'),
    ('gopro-quik', 'GoPro Quik', 'com.gopro.smarty'),
    ('videoshow', 'VideoShow', 'com.xvideostudio.videoeditor'),
    ('alight-motion', 'Alight Motion', 'com.alightcreative.motion'),
)
MESSAGING_APPS = (
    ('line', 'LINE', 'jp.naver.line.android'),
    ('viber', 'Viber', 'com.viber.voip'),
    ('wechat', 'WeChat', 'com.tencent.mm'),
    ('kakaotalk', 'KakaoTalk', 'com.kakao.talk'),
)
EXTENDED_COMMUNICATION_APPS = (
    ('imo', 'imo', 'com.imo.android.imoim'),
    ('zalo', 'Zalo', 'com.zing.zalo'),
    ('bip', 'BiP', 'com.turkcell.bip'),
    ('google-chat', 'Google Chat', 'com.google.android.apps.dynamite'),
)
APPS = HISTORICAL_APPS + GBOARD_APPS + VIDEO_EDITING_APPS + MESSAGING_APPS + EXTENDED_COMMUNICATION_APPS
CURRENT_IDS = FUNCTIONS + [row[0] for row in APPS]
MANUAL_MAPPING_IDS = {
    'panera-bread', 'amtrak', 'tripit', 'hopper', 'us-bank', 'schwab',
    'weather-underground', 'weatherbug', 'windfinder', 'asics-runkeeper', 'map-my-run', 'zwift-companion',
    'calendar', 'notes', 'mail', 'browser', 'maps', 'music', 'video', 'wallet', 'health', 'fitness', 'home',
}
REFINED_IDS = {'google-messages', 'google-translate', 'fandom', 'ace-hardware',
               'dollar-general', 'myfitnesspal', 'wallpaper-engine', 'webtoon'}
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
        previous_communication = render_icons(monochrome, version='0.26.0')
        previous_communication['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        previous_contacts = render_icons(monochrome, version='0.24.0')
        previous_contacts['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        previous_contained = render_icons(monochrome, version='0.23.0')
        previous_contained['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        previous_spaced = render_icons(monochrome, version='0.22.0')
        previous_spaced['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        previous_polished = render_icons(monochrome, version='0.21.0')
        previous_polished['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        previous_video_editing = render_icons(monochrome, version='0.20.0')
        previous_video_editing['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        previous_phone_service = render_icons(monochrome, version='0.17.0')
        retained = render_icons(document, version='0.5.0')
        manifest = json.loads(expected['manifest.json'])
        self.assertEqual(manifest['version'], '0.31.0')
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
        previous_craft = render_icons(monochrome, version='0.30.0')
        previous_craft['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[CRAFT_ICON_ARCHIVE])) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_craft)
        self.assertEqual(hashlib.sha256(files[CRAFT_ICON_ARCHIVE]).hexdigest(),
                         '97c0e51b4374be54c739f5c47da9628229d6bdc6c12435963e5f9e0acd17e734')
        previous_art_direction = render_icons(monochrome, version='0.29.0')
        previous_art_direction['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[ART_DIRECTION_ICON_ARCHIVE])) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_art_direction)
        self.assertEqual(hashlib.sha256(files[ART_DIRECTION_ICON_ARCHIVE]).hexdigest(),
                         '1ef292dc97f91593bb134439302663bd9fa0824ef04295e880c4aecabd8e3f50')
        previous_identity = render_icons(monochrome, version='0.28.0')
        previous_identity['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[IDENTITY_ICON_ARCHIVE])) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_identity)
        self.assertEqual(hashlib.sha256(files[IDENTITY_ICON_ARCHIVE]).hexdigest(),
                         'fe021dff47c0927fcd8098f8da688309d734b40317d72d6ae876f3c4d36dd92a')
        self.assertEqual({name for name in previous_art_direction if name.endswith('.svg')
                          and previous_art_direction[name] != previous_identity[name]},
                         {f'{appearance}/{identifier}.svg' for appearance in ('Clair', 'Obscur')
                          for identifier in ('fly-delta', 'american-airlines', 'southwest-airlines',
                                             'wikipedia', 'google-earth')})
        self.assertEqual(sum(name.endswith('.svg') and previous_art_direction[name] == previous_identity[name]
                             for name in previous_identity), 590)
        previous_route = render_icons(monochrome, version='0.27.0')
        previous_route['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[ROUTE_ICON_ARCHIVE])) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_route)
        self.assertEqual(hashlib.sha256(files[ROUTE_ICON_ARCHIVE]).hexdigest(),
                         '96fc1be033628ec1df75d8fd6302f6ede55e65ac617719a1742c1e41ad673592')
        self.assertEqual({name for name in previous_identity if name.endswith('.svg')
                          and previous_identity[name] != previous_route[name]},
                         {'Clair/claude.svg', 'Obscur/claude.svg',
                          'Clair/perplexity.svg', 'Obscur/perplexity.svg'})
        with zipfile.ZipFile(io.BytesIO(files[COMMUNICATION_ICON_ARCHIVE])) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_communication)
        self.assertEqual(hashlib.sha256(files[COMMUNICATION_ICON_ARCHIVE]).hexdigest(),
                         '937a707475e5f63aadd1c371f8f9a7bc399bca1c417e4c94f016924bd0a0bbf4')
        self.assertEqual(hashlib.sha256(previous_communication['manifest.json']).hexdigest(),
                         '806c65811646c28929a741f15dd7070d9ae412c674009dc0a82db224f2095663')
        self.assertEqual(set(expected), set(previous_communication))
        self.assertEqual({name for name in previous_route if name.endswith('.svg')
                          and previous_route[name] != previous_communication[name]},
                         {'Clair/united-airlines.svg', 'Obscur/united-airlines.svg'})
        self.assertEqual(json.loads(previous_communication['manifest.json'])['catalog'], manifest['catalog'])
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
                self.assertEqual(previous_phone_service[path], payload)
        previous_companion = render_icons(monochrome, version='0.7.0')
        previous_companion['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[COMPANION_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 192)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_companion)
        self.assertEqual(hashlib.sha256(files[COMPANION_ICON_ARCHIVE]).hexdigest(),
                         'aa18db922e824cd2bfa1ada2fbc08125af2605d9c5acb2ad8bfdb439985f4f05')
        for path, payload in previous_companion.items():
            if path.endswith('.svg'):
                self.assertEqual(previous_phone_service[path], payload)
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
                self.assertEqual(previous_phone_service[path], payload)
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
                self.assertEqual(previous_phone_service[path], payload)
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
                          for row in manifest['catalog'][187:197]], list(TRAVEL_APPS))
        for path, payload in previous_food_order.items():
            if path.endswith('.svg'):
                self.assertEqual(previous_phone_service[path], payload)
        previous_travel = render_icons(monochrome, version='0.11.0')
        previous_travel['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[TRAVEL_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 396)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_travel)
        self.assertEqual(hashlib.sha256(files[TRAVEL_ICON_ARCHIVE]).hexdigest(),
                         '04cce2b812ad4f6ed7bcfda172a9bfe5a6d63d058b6899570a1dbe94f162884d')
        self.assertEqual(json.loads(previous_travel['manifest.json'])['catalog'], manifest['catalog'][:197])
        self.assertEqual([(row['id'], row['label'], row['android_package'])
                          for row in manifest['catalog'][197:207]], list(FINANCE_APPS))
        for path, payload in previous_travel.items():
            if path.endswith('.svg'):
                self.assertEqual(previous_phone_service[path], payload)
        previous_finance = render_icons(monochrome, version='0.12.0')
        previous_finance['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[FINANCE_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 416)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_finance)
        self.assertEqual(hashlib.sha256(files[FINANCE_ICON_ARCHIVE]).hexdigest(),
                         'db8ed7e2c62d36786b2c2d510fdf68f83649fda512f6bb018f5043491cb8f0cf')
        previous_finance_catalog = json.loads(previous_finance['manifest.json'])
        self.assertEqual(len(previous_finance_catalog['catalog']), 207)
        self.assertEqual(previous_finance_catalog['catalog'], manifest['catalog'][:207])
        self.assertEqual([(row['id'], row['label'], row['android_package'])
                          for row in manifest['catalog'][207:217]], list(WEATHER_APPS))
        for path, payload in previous_finance.items():
            if path.endswith('.svg'):
                self.assertEqual(previous_phone_service[path], payload)
        previous_weather = render_icons(monochrome, version='0.13.0')
        previous_weather['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[WEATHER_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 436)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_weather)
        self.assertEqual(hashlib.sha256(files[WEATHER_ICON_ARCHIVE]).hexdigest(),
                         'e6f7c532d0c625666a0f3403ee27842ac8612e6368d49f64fb3e84b667a42ca1')
        previous_weather_catalog = json.loads(previous_weather['manifest.json'])
        self.assertEqual(len(previous_weather_catalog['catalog']), 217)
        self.assertEqual(previous_weather_catalog['catalog'], manifest['catalog'][:217])
        self.assertEqual([(row['id'], row['label'], row['android_package'])
                          for row in manifest['catalog'][217:225]], list(RUNNING_TRAINING_APPS))
        for path, payload in previous_weather.items():
            if path.endswith('.svg'):
                self.assertEqual(previous_phone_service[path], payload)
        previous_running = render_icons(monochrome, version='0.14.0')
        previous_running['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[RUNNING_TRAINING_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 452)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_running)
        self.assertEqual(hashlib.sha256(files[RUNNING_TRAINING_ICON_ARCHIVE]).hexdigest(),
                         '4b3324d30b0b6e94a52e0d51a206e499e6e2b6be82052752963da9446c44e6c1')
        self.assertEqual(hashlib.sha256(previous_running['manifest.json']).hexdigest(),
                         '4ac31c55d2723a0e27ee4892eb29d59dbdcb179443f496fced7b69337c0699df')
        self.assertEqual(json.loads(previous_running['manifest.json'])['catalog'], manifest['catalog'][:225])
        self.assertEqual([(row['id'], row['label'], row['android_package'])
                          for row in manifest['catalog'][225:233]], list(LEARNING_APPS))
        for path, payload in previous_running.items():
            if path.endswith('.svg'):
                self.assertEqual(previous_phone_service[path], payload)
        previous_learning = render_icons(monochrome, version='0.15.0')
        previous_learning['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[LEARNING_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 468)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_learning)
        self.assertEqual(hashlib.sha256(files[LEARNING_ICON_ARCHIVE]).hexdigest(),
                         'df05503c0f1825d09e5b5fb96fcb87401490fef601518ca4e526a6e6d564197c')
        self.assertEqual(hashlib.sha256(previous_learning['manifest.json']).hexdigest(),
                         '3979cc7eaf90a5cf8aab82bd711fc8d2ff92388856cbb41b9321442693b88b2b')
        self.assertEqual(json.loads(previous_learning['manifest.json'])['catalog'], manifest['catalog'][:233])
        self.assertEqual([(row['id'], row['label'], row['android_package'])
                          for row in manifest['catalog'][233:241]], list(READING_APPS))
        for path, payload in previous_learning.items():
            if path.endswith('.svg'):
                self.assertEqual(previous_phone_service[path], payload)
        previous_reading = render_icons(monochrome, version='0.16.0')
        previous_reading['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[READING_ICON_ARCHIVE])) as archive:
            self.assertEqual(len(archive.namelist()), 484)
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_reading)
        self.assertEqual(hashlib.sha256(files[READING_ICON_ARCHIVE]).hexdigest(),
                         '3fbf8b53e12ddae6ea354d6ed20a1464c4874192a24f5dee7f231baed0e7f3a0')
        self.assertEqual(json.loads(previous_reading['manifest.json'])['catalog'], manifest['catalog'][:241])
        self.assertEqual([(row['id'], row['label'], row['android_package'])
                          for row in manifest['catalog'][241:281]], list(PHONE_SERVICE_APPS))
        for path, payload in previous_reading.items():
            if path.endswith('.svg'):
                self.assertEqual(previous_phone_service[path], payload)
        previous_phone_service['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[PHONE_SERVICE_ICON_ARCHIVE])) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_phone_service)
        self.assertEqual(hashlib.sha256(files[PHONE_SERVICE_ICON_ARCHIVE]).hexdigest(),
                         '0e638e99a265b7b3d5c04e77c3611c732e6b36fa3d26a674e255d89e0c1fd346')
        self.assertEqual(hashlib.sha256(previous_phone_service['manifest.json']).hexdigest(),
                         'e1be7375d5697623c539b0b08989be070edf3df5a501a95753d0c78fc44ff503')
        self.assertEqual(json.loads(previous_phone_service['manifest.json'])['catalog'], manifest['catalog'][:281])
        changed = {path for path in previous_phone_service if path.endswith('.svg')
                   and previous_video_editing[path] != previous_phone_service[path]}
        self.assertEqual(changed, {f'{appearance}/{name}.svg' for appearance in ('Clair', 'Obscur')
                                   for name in REFINED_IDS})
        previous_refined = render_icons(monochrome, version='0.18.0')
        previous_refined['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[REFINED_ICON_ARCHIVE])) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_refined)
        self.assertEqual(hashlib.sha256(files[REFINED_ICON_ARCHIVE]).hexdigest(),
                         '5bbf577f50b3dae894405e598d9ca7d8e6246cac9e7f2859c7b5f5ba0771e985')
        self.assertEqual(json.loads(previous_refined['manifest.json'])['catalog'], manifest['catalog'][:281])
        self.assertEqual([(row['id'], row['label'], row['android_package'])
                          for row in manifest['catalog'][281:282]], list(GBOARD_APPS))
        for path, payload in previous_refined.items():
            if path.endswith('.svg'):
                self.assertEqual(previous_video_editing[path], payload)
        self.assertEqual(set(expected) - set(previous_refined), {f'{appearance}/{name}.svg'
            for appearance in ('Clair', 'Obscur') for name in ('gboard', *[row[0] for row in VIDEO_EDITING_APPS], *[row[0] for row in MESSAGING_APPS], *[row[0] for row in EXTENDED_COMMUNICATION_APPS])})
        previous_gboard = render_icons(monochrome, version='0.19.0')
        previous_gboard['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[GBOARD_ICON_ARCHIVE])) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_gboard)
        self.assertEqual(hashlib.sha256(files[GBOARD_ICON_ARCHIVE]).hexdigest(),
                         '22ffaf915634a27adc9608e77d8c0d5bd885bc3bfae323a509f2f566a330334e')
        self.assertEqual(hashlib.sha256(previous_gboard['manifest.json']).hexdigest(),
                         'a956a0abf1c478bd0ed9772eeab1f141bf20e1ecf359118db4e149337d0d2cee')
        self.assertEqual(json.loads(previous_gboard['manifest.json'])['catalog'], manifest['catalog'][:282])
        self.assertEqual([(row['id'], row['label'], row['android_package'])
                          for row in manifest['catalog'][282:292]], list(VIDEO_EDITING_APPS))
        for path, payload in previous_gboard.items():
            if path.endswith('.svg'):
                self.assertEqual(previous_video_editing[path], payload)
        self.assertEqual(set(previous_contacts) - set(previous_gboard), {f'{appearance}/{name}.svg'
            for appearance in ('Clair', 'Obscur') for name, _, _ in VIDEO_EDITING_APPS})
        with zipfile.ZipFile(io.BytesIO(files[VIDEO_EDITING_ICON_ARCHIVE])) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_video_editing)
        self.assertEqual(hashlib.sha256(files[VIDEO_EDITING_ICON_ARCHIVE]).hexdigest(),
                         'db1e52859497c2d4852362c1bd5d365a2aab2b6473069bc6aa49c4895d3e0ffa')
        self.assertEqual(hashlib.sha256(previous_video_editing['manifest.json']).hexdigest(),
                         'f451ea0520367d0f3b4057c87d6f1204e381122a8da4cd57f8f00d8dbf00efbe')
        self.assertEqual(json.loads(previous_video_editing['manifest.json'])['catalog'], manifest['catalog'][:292])
        self.assertEqual(set(previous_video_editing), set(previous_contacts))
        polished = {path for path in previous_video_editing if path.endswith('.svg')
                    and previous_polished[path] != previous_video_editing[path]}
        self.assertEqual(polished, {f'{appearance}/{name}.svg' for appearance in ('Clair', 'Obscur')
                                   for name in ('ai-dungeon', 'usaa', 'discord', 'link-to-windows', 'chatgpt', 'prime-video', 'g2a')})
        with zipfile.ZipFile(io.BytesIO(files[POLISHED_ICON_ARCHIVE])) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_polished)
        self.assertEqual(hashlib.sha256(files[POLISHED_ICON_ARCHIVE]).hexdigest(),
                         '504402b2f2b93ea6315a92738487fd4545c949b7f28a10fcaa79f383e7db7caf')
        self.assertEqual(hashlib.sha256(previous_polished['manifest.json']).hexdigest(),
                         '3c2a4316d0a118dfa585c637c3e8caebc0b961f9ab097d2950639475b5155b03')
        self.assertEqual(json.loads(previous_polished['manifest.json'])['catalog'], manifest['catalog'][:292])
        self.assertEqual(set(previous_polished), set(previous_contacts))
        spaced = {path for path in previous_polished if path.endswith('.svg')
                  and previous_spaced[path] != previous_polished[path]}
        self.assertEqual(spaced, {f'{appearance}/{name}.svg' for appearance in ('Clair', 'Obscur')
                                 for name in ('threads', 'evernote', 'myradar', 'goodreads')})
        with zipfile.ZipFile(io.BytesIO(files[SPACED_ICON_ARCHIVE])) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_spaced)
        self.assertEqual(hashlib.sha256(files[SPACED_ICON_ARCHIVE]).hexdigest(),
                         '04d4d2bb80f61efff1b809a2b2253cca9bb4bea0bc7d254668518b6b13df5217')
        self.assertEqual(hashlib.sha256(previous_spaced['manifest.json']).hexdigest(),
                         '8b6eaabd574d2618c693ccd72b46a3ef738dd5af72e0041a940543b8accd3ea0')
        self.assertEqual(json.loads(previous_spaced['manifest.json'])['catalog'], manifest['catalog'][:292])
        contained = {path for path in previous_spaced if path.endswith('.svg')
                     and previous_contained[path] != previous_spaced[path]}
        self.assertEqual(contained, {f'{appearance}/proton-pass.svg' for appearance in ('Clair', 'Obscur')})
        with zipfile.ZipFile(io.BytesIO(files[CONTAINED_ICON_ARCHIVE])) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_contained)
        self.assertEqual(hashlib.sha256(files[CONTAINED_ICON_ARCHIVE]).hexdigest(),
                         '89a9f0806580d981d539437d2374b700704f832c3e786d0e4cf3ee80e6d5e22e')
        self.assertEqual(hashlib.sha256(previous_contained['manifest.json']).hexdigest(),
                         'fd7baed90d161be794dc7ff88cdecba4534a2975b68e2b7a199dcfe68e9529c8')
        self.assertEqual(json.loads(previous_contained['manifest.json'])['catalog'], manifest['catalog'][:292])
        self.assertEqual(set(previous_contained), set(previous_contacts))
        contact_refinements = {path for path in previous_contained if path.endswith('.svg')
                               and previous_contacts[path] != previous_contained[path]}
        self.assertEqual(contact_refinements, {f'{appearance}/{name}.svg'
            for appearance in ('Clair', 'Obscur') for name in ('va', 'dunkin', 'samsung-pass', 'sonic')})
        self.assertEqual(sum(path.endswith('.svg') and previous_contacts[path] == previous_contained[path]
                             for path in previous_contained), 576)
        with zipfile.ZipFile(io.BytesIO(files[CONTACT_SPACED_ICON_ARCHIVE])) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_contacts)
        self.assertEqual(hashlib.sha256(files[CONTACT_SPACED_ICON_ARCHIVE]).hexdigest(),
                         'a20f93736ad0b5665f135dfa6de0fecbb14150dbadd026f402c2d3704f463cb2')
        self.assertEqual(hashlib.sha256(previous_contacts['manifest.json']).hexdigest(),
                         '919c7fcd13e01d83194baedea14ac2729384a9394f8fb1346d5f48a31ea3c52e')
        self.assertEqual(json.loads(previous_contacts['manifest.json'])['catalog'], manifest['catalog'][:292])
        self.assertEqual([(row['id'], row['label'], row['android_package'])
                          for row in manifest['catalog'][292:296]], list(MESSAGING_APPS))
        self.assertEqual(set(expected) - set(previous_contacts), {f'{appearance}/{name}.svg'
            for appearance in ('Clair', 'Obscur') for name, _, _ in (*MESSAGING_APPS, *EXTENDED_COMMUNICATION_APPS)})
        for path, payload in previous_contacts.items():
            if path.endswith('.svg'):
                self.assertEqual(previous_communication[path], payload, path)
        self.assertEqual(sum(path.endswith('.svg') for path in previous_contacts), 584)
        previous_messaging = render_icons(monochrome, version='0.25.0')
        previous_messaging['LICENSE.txt'] = (ROOT / 'LICENSE').read_bytes()
        with zipfile.ZipFile(io.BytesIO(files[MESSAGING_ICON_ARCHIVE])) as archive:
            self.assertEqual({name: archive.read(name) for name in archive.namelist()}, previous_messaging)
        self.assertEqual(hashlib.sha256(files[MESSAGING_ICON_ARCHIVE]).hexdigest(),
                         'f7ac7719af8b742a89bdffd5cf80fd0eb78a3b4fbed2f937b29a79b2f5f8e7d9')
        self.assertEqual(json.loads(previous_messaging['manifest.json'])['catalog'], manifest['catalog'][:296])
        self.assertEqual(sum(name.endswith('.svg') for name in previous_messaging), 592)
        self.assertEqual(set(expected) - set(previous_messaging), {f'{appearance}/{name}.svg'
            for appearance in ('Clair', 'Obscur') for name, _, _ in EXTENDED_COMMUNICATION_APPS})
        self.assertEqual([(row['id'], row['label'], row['android_package'])
                          for row in manifest['catalog'][296:]], list(EXTENDED_COMMUNICATION_APPS))
        for name, payload in previous_messaging.items():
            if name.endswith('.svg'):
                self.assertEqual(previous_communication[name], payload, name)
        self.assertNotEqual(files[ICON_ARCHIVE], files[PHONE_SERVICE_ICON_ARCHIVE])
        self.assertNotEqual(files[ICON_ARCHIVE], files[LEGACY_ICON_ARCHIVE])
        self.assertEqual(files[ICON_CHECKSUMS],
                         ''.join(f'{hashlib.sha256(files[path]).hexdigest()}  {Path(path).name}\n'
                                 for path in (ICON_ARCHIVE, CRAFT_ICON_ARCHIVE, ART_DIRECTION_ICON_ARCHIVE, IDENTITY_ICON_ARCHIVE, ROUTE_ICON_ARCHIVE, COMMUNICATION_ICON_ARCHIVE, MESSAGING_ICON_ARCHIVE, CONTACT_SPACED_ICON_ARCHIVE, CONTAINED_ICON_ARCHIVE, SPACED_ICON_ARCHIVE, POLISHED_ICON_ARCHIVE, VIDEO_EDITING_ICON_ARCHIVE, GBOARD_ICON_ARCHIVE, REFINED_ICON_ARCHIVE, PHONE_SERVICE_ICON_ARCHIVE, READING_ICON_ARCHIVE, LEARNING_ICON_ARCHIVE, RUNNING_TRAINING_ICON_ARCHIVE, WEATHER_ICON_ARCHIVE, FINANCE_ICON_ARCHIVE, TRAVEL_ICON_ARCHIVE, FOOD_ORDER_ICON_ARCHIVE, EVERYDAY_ICON_ARCHIVE, BROAD_ICON_ARCHIVE, COMPANION_ICON_ARCHIVE, MONOCHROME_ICON_ARCHIVE, THIRD_APP_ICON_ARCHIVE, SECOND_APP_ICON_ARCHIVE, FIRST_APP_ICON_ARCHIVE,
                                              PREVIOUS_ICON_ARCHIVE, LEGACY_ICON_ARCHIVE)).encode())
        repeated = preview_files(ROOT, self.artifacts)
        for path in (ICON_ARCHIVE, CRAFT_ICON_ARCHIVE, ART_DIRECTION_ICON_ARCHIVE, IDENTITY_ICON_ARCHIVE, ROUTE_ICON_ARCHIVE, COMMUNICATION_ICON_ARCHIVE, MESSAGING_ICON_ARCHIVE, CONTACT_SPACED_ICON_ARCHIVE, CONTAINED_ICON_ARCHIVE, SPACED_ICON_ARCHIVE, POLISHED_ICON_ARCHIVE, VIDEO_EDITING_ICON_ARCHIVE, GBOARD_ICON_ARCHIVE, REFINED_ICON_ARCHIVE, PHONE_SERVICE_ICON_ARCHIVE, READING_ICON_ARCHIVE, LEARNING_ICON_ARCHIVE, RUNNING_TRAINING_ICON_ARCHIVE, WEATHER_ICON_ARCHIVE, FINANCE_ICON_ARCHIVE, TRAVEL_ICON_ARCHIVE, FOOD_ORDER_ICON_ARCHIVE, EVERYDAY_ICON_ARCHIVE, BROAD_ICON_ARCHIVE, COMPANION_ICON_ARCHIVE, MONOCHROME_ICON_ARCHIVE, THIRD_APP_ICON_ARCHIVE, SECOND_APP_ICON_ARCHIVE, FIRST_APP_ICON_ARCHIVE,
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
                    self.assertEqual(card['attrs']['data-icon-version'], '0.31.0')
                    package = app_packages.get(function, '')
                    self.assertEqual(card['package'], package)
                    manual = function in MANUAL_MAPPING_IDS
                    self.assertEqual(card['attrs']['data-icon-mapping'], 'manual' if manual else 'included')
                    self.assertEqual(card['links'], ([] if not package else [{
                        'href': (f'https://galaxystore.samsung.com/detail/{package}' if function in
                                 {'gaming-hub', 'theme-park', 'samsung-pass', 'tips'} else
                                 f'https://play.google.com/store/apps/details?id={package}'),
                        'rel': 'noreferrer',
                    }]) + [{'href': '#icon-manual-instructions' if manual else '#icon-pack-instructions'}])
                    self.assertNotIn('hidden', card['attrs'])
                    self.assertEqual(len(card['images']), 2)
                    self.assertEqual(len(card['buttons']), 2)
                    for appearance, button in zip(('Clair', 'Obscur'), card['buttons']):
                        self.assertEqual(button['type'], 'button')
                        self.assertIn('data-icon-png', button)
                        self.assertEqual(button['data-icon-appearance'], appearance)
                        self.assertEqual(button['data-icon-filename'],
                                         f'Clair-Obscur-0.31.0-{appearance}-{function}-512.png')
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
                    self.assertIn((f'https://galaxystore.samsung.com/detail/{package}' if identifier in
                                   {'gaming-hub', 'theme-park', 'samsung-pass', 'tips'} else
                                   f'https://play.google.com/store/apps/details?id={package}'), page)
                    self.assertIn(f'<code translate="no">{package}</code>', page)
                for path in (ICON_ARCHIVE, CRAFT_ICON_ARCHIVE, ART_DIRECTION_ICON_ARCHIVE, IDENTITY_ICON_ARCHIVE, ROUTE_ICON_ARCHIVE, COMMUNICATION_ICON_ARCHIVE, MESSAGING_ICON_ARCHIVE, CONTACT_SPACED_ICON_ARCHIVE, CONTAINED_ICON_ARCHIVE, SPACED_ICON_ARCHIVE, POLISHED_ICON_ARCHIVE, VIDEO_EDITING_ICON_ARCHIVE, GBOARD_ICON_ARCHIVE, REFINED_ICON_ARCHIVE, PHONE_SERVICE_ICON_ARCHIVE, READING_ICON_ARCHIVE, LEARNING_ICON_ARCHIVE, RUNNING_TRAINING_ICON_ARCHIVE, WEATHER_ICON_ARCHIVE, FINANCE_ICON_ARCHIVE, TRAVEL_ICON_ARCHIVE, FOOD_ORDER_ICON_ARCHIVE, EVERYDAY_ICON_ARCHIVE, BROAD_ICON_ARCHIVE, COMPANION_ICON_ARCHIVE, MONOCHROME_ICON_ARCHIVE, THIRD_APP_ICON_ARCHIVE, SECOND_APP_ICON_ARCHIVE, FIRST_APP_ICON_ARCHIVE,
                             PREVIOUS_ICON_ARCHIVE, LEGACY_ICON_ARCHIVE, ICON_CHECKSUMS):
                    links = [link for link in markup.links if link.get('href') == path]
                    self.assertEqual(len(links), 1)
                    self.assertIn('download', links[0])
                    self.assertEqual(delivery[path], files[path])
                history = {link['id']: link['href'] for link in markup.links if 'id' in link}
                self.assertEqual(history['icon-artwork-download'], ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-art-direction-download'], ART_DIRECTION_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-identity-download'], IDENTITY_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-route-download'], ROUTE_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-communication-download'], COMMUNICATION_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-messaging-download'], MESSAGING_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-contact-spaced-download'], CONTACT_SPACED_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-contained-download'], CONTAINED_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-spaced-download'], SPACED_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-polished-download'], POLISHED_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-video-editing-download'], VIDEO_EDITING_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-phone-service-download'], PHONE_SERVICE_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-reading-download'], READING_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-study-learning-download'], LEARNING_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-travel-download'], TRAVEL_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-weather-download'], WEATHER_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-running-training-download'], RUNNING_TRAINING_ICON_ARCHIVE)
                self.assertEqual(history['icon-artwork-finance-download'], FINANCE_ICON_ARCHIVE)
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
                    'icon-artwork-download', 'icon-artwork-checksums', 'icon-artwork-craft-download', 'icon-artwork-art-direction-download', 'icon-artwork-identity-download', 'icon-artwork-route-download', 'icon-artwork-communication-download', 'icon-artwork-messaging-download', 'icon-artwork-contact-spaced-download', 'icon-artwork-contained-download', 'icon-artwork-spaced-download', 'icon-artwork-polished-download', 'icon-artwork-video-editing-download', 'icon-artwork-gboard-download', 'icon-artwork-refined-download', 'icon-artwork-phone-service-download', 'icon-artwork-reading-download', 'icon-artwork-study-learning-download', 'icon-artwork-running-training-download', 'icon-artwork-weather-download', 'icon-artwork-finance-download', 'icon-artwork-travel-download', 'icon-artwork-food-order-download', 'icon-artwork-everyday-download', 'icon-artwork-broad-download',
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
        for changed_version in ('0.1.0', '0.2.0', '0.3.0', '0.4.0', '0.5.0', '0.6.0', '0.7.0', '0.8.0', '0.9.0', '0.10.0', '0.11.0', '0.12.0', '0.13.0', '0.14.0', '0.15.0', '0.16.0', '0.17.0', '0.18.0', '0.19.0', '0.20.0', '0.21.0', '0.22.0', '0.23.0', '0.24.0', '0.25.0', '0.26.0', '0.27.0', '0.28.0', '0.29.0', '0.30.0', '0.31.0'):
            with self.subTest(version=changed_version):
                def changed_grant(document, *, version='0.31.0'):
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
                ('fly-delta', 'missing-app'), ('hopper', 'missing-label'),
                ('bank-of-america', 'missing-app'), ('robinhood', 'missing-label'),
                ('accuweather', 'missing-app'), ('rainviewer', 'missing-label'),
                ('nike-run-club', 'missing-app'), ('relive', 'missing-label'),
                ('google-classroom', 'missing-app'), ('brainly', 'missing-label'),
                ('google-play-books', 'missing-app'), ('moon-reader', 'missing-label'),
                ('gboard', 'missing-app'), ('gboard', 'missing-label'),
                *[(row[0], mutation) for row in VIDEO_EDITING_APPS + MESSAGING_APPS
                  for mutation in ('missing-app', 'missing-label')]):
            def changed_catalog(document, *, version='0.31.0'):
                files = render_icons(document, version=version)
                if version == '0.31.0':
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
        def changed_label(document, *, version='0.31.0'):
            files = render_icons(document, version=version)
            if version == '0.31.0':
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
