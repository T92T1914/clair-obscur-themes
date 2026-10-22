"""Original vector geometry, palette consumption and output-preservation checks."""

import copy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from themeforge import icons


ROOT = Path(__file__).resolve().parents[1]
BASE_NAMES = (
    "phone messages contacts camera gallery settings calendar clock files notes mail "
    "browser maps music video store wallet calculator weather health fitness "
    "voice-recorder home search"
).split()
APP_NAMES = (
    "google-chrome youtube google-maps gmail google-photos google-messages google-calendar google-drive "
    "samsung-browser samsung-notes samsung-health garmin-connect whatsapp messenger instagram facebook "
    "snapchat tiktok discord reddit pinterest telegram spotify netflix amazon-shopping walmart temu uber "
    "doordash paypal outlook chatgpt firefox"
).split()
PREVIOUS_APP_NAMES = APP_NAMES[:]
PREVIOUS_NAMES = BASE_NAMES + PREVIOUS_APP_NAMES
NEW_APP_NAMES = (
    "x threads signal twitch capcut disney-plus prime-video microsoft-teams zoom google-meet "
    "google-docs google-sheets onedrive google-translate google-keep google-wallet cash-app venmo "
    "ebay mcdonalds starbucks duolingo waze canva"
).split()
APP_NAMES += NEW_APP_NAMES
SECOND_NAMES = BASE_NAMES + APP_NAMES
THIRD_APP_NAMES = (
    "linkedin github notion microsoft-edge brave microsoft-authenticator "
    "google-authenticator samsung-smartthings"
).split()
APP_NAMES += THIRD_APP_NAMES
THIRD_NAMES = BASE_NAMES + APP_NAMES
FOURTH_APP_NAMES = "good-lock connect-iq-store steam reuters home-depot patreon".split()
APP_NAMES += FOURTH_APP_NAMES
FOURTH_NAMES = BASE_NAMES + APP_NAMES
FIFTH_APP_NAMES = (
    'youtube-music audible amazon-kindle pocket-casts vlc shazam soundcloud hulu target costco best-buy etsy aliexpress shein instacart airbnb booking expedia lyft uber-eats google-earth google-news galaxy-wearable files-by-google adobe-acrobat microsoft-word microsoft-excel microsoft-powerpoint google-slides google-lens roblox minecraft'
).split()
APP_NAMES += FIFTH_APP_NAMES
FIFTH_NAMES = BASE_NAMES + APP_NAMES
SIXTH_APP_NAMES = (
    "slack trello todoist ticktick evernote obsidian dropbox proton-mail "
    "yahoo-mail google-tasks google-one microsoft-copilot google-gemini claude perplexity bitwarden "
    "apple-music apple-tv hbo-max peacock paramount-plus plex tubi pluto-tv "
    "crunchyroll pandora iheartradio siriusxm adobe-lightroom photoshop-express snapseed picsart "
    "strava fitbit google-fit myfitnesspal alltrails komoot amazon-alexa ring "
    "blink google-home zillow chase capital-one chime ups fedex"
).split()
APP_NAMES += SIXTH_APP_NAMES
SIXTH_NAMES = BASE_NAMES + APP_NAMES
SEVENTH_APP_NAMES = (
    "chipotle taco-bell wendys burger-king dunkin chick-fil-a dominos pizza-hut "
    "subway panera-bread kfc-us grubhub"
).split()
APP_NAMES += SEVENTH_APP_NAMES
SEVENTH_NAMES = BASE_NAMES + APP_NAMES
EIGHTH_APP_NAMES = (
    "fly-delta united-airlines american-airlines southwest-airlines amtrak "
    "transit moovit citymapper tripit hopper"
).split()
APP_NAMES += EIGHTH_APP_NAMES
EIGHTH_NAMES = BASE_NAMES + APP_NAMES
NINTH_APP_NAMES = "bank-of-america wells-fargo us-bank pnc discover amex fidelity-investments schwab sofi robinhood".split()
APP_NAMES += NINTH_APP_NAMES
NINTH_NAMES = BASE_NAMES + APP_NAMES
TENTH_APP_NAMES = (
    "accuweather weather-channel weather-underground windy-com myradar "
    "weatherbug one-weather clime windfinder rainviewer"
).split()
APP_NAMES += TENTH_APP_NAMES
TENTH_NAMES = BASE_NAMES + APP_NAMES
ELEVENTH_APP_NAMES = (
    "nike-run-club adidas-running asics-runkeeper map-my-run runna "
    "trainingpeaks zwift-companion relive"
).split()
APP_NAMES += ELEVENTH_APP_NAMES
ELEVENTH_NAMES = BASE_NAMES + APP_NAMES
TWELFTH_APP_NAMES = "google-classroom khan-academy coursera udemy edx quizlet photomath brainly".split()
APP_NAMES += TWELFTH_APP_NAMES
TWELFTH_NAMES = BASE_NAMES + APP_NAMES
THIRTEENTH_APP_NAMES = "google-play-books libby kobo-books goodreads wattpad webtoon readera moon-reader".split()
APP_NAMES += THIRTEENTH_APP_NAMES
THIRTEENTH_NAMES = BASE_NAMES + APP_NAMES
FOURTEENTH_APP_NAMES = "ace-hardware ai-dungeon gaming-hub kroger affirm usaa proton-authenticator wikipedia xbox shop fandom shonen-jump smart-switch steam-chat sonic samsung-global-goals theme-park zillow-rentals samsung-find dollar-general sound-connect samsung-pass va battle-net coinbase credit-one samsung-members proton-vpn t-life my-spectrum g2a samsung-tv-plus ap-news link-to-windows tips proton-pass shop-samsung wallpaper-engine asus-router mochi-health".split()
APP_NAMES += FOURTEENTH_APP_NAMES
NAMES = BASE_NAMES + APP_NAMES
EXPECTED_APPS = {
    "google-chrome": ("Google Chrome", "com.android.chrome"),
    "youtube": ("YouTube", "com.google.android.youtube"),
    "google-maps": ("Google Maps", "com.google.android.apps.maps"),
    "gmail": ("Gmail", "com.google.android.gm"),
    "google-photos": ("Google Photos", "com.google.android.apps.photos"),
    "google-messages": ("Google Messages", "com.google.android.apps.messaging"),
    "google-calendar": ("Google Calendar", "com.google.android.calendar"),
    "google-drive": ("Google Drive", "com.google.android.apps.docs"),
    "samsung-browser": ("Samsung Browser", "com.sec.android.app.sbrowser"),
    "samsung-notes": ("Samsung Notes", "com.samsung.android.app.notes"),
    "samsung-health": ("Samsung Health", "com.sec.android.app.shealth"),
    "garmin-connect": ("Garmin Connect", "com.garmin.android.apps.connectmobile"),
    "whatsapp": ("WhatsApp", "com.whatsapp"),
    "messenger": ("Messenger", "com.facebook.orca"),
    "instagram": ("Instagram", "com.instagram.android"),
    "facebook": ("Facebook", "com.facebook.katana"),
    "snapchat": ("Snapchat", "com.snapchat.android"),
    "tiktok": ("TikTok", "com.zhiliaoapp.musically"),
    "discord": ("Discord", "com.discord"),
    "reddit": ("Reddit", "com.reddit.frontpage"),
    "pinterest": ("Pinterest", "com.pinterest"),
    "telegram": ("Telegram", "org.telegram.messenger"),
    "spotify": ("Spotify", "com.spotify.music"),
    "netflix": ("Netflix", "com.netflix.mediaclient"),
    "amazon-shopping": ("Amazon Shopping", "com.amazon.mShop.android.shopping"),
    "walmart": ("Walmart", "com.walmart.android"),
    "temu": ("Temu", "com.einnovation.temu"),
    "uber": ("Uber", "com.ubercab"),
    "doordash": ("DoorDash", "com.dd.doordash"),
    "paypal": ("PayPal", "com.paypal.android.p2pmobile"),
    "outlook": ("Microsoft Outlook", "com.microsoft.office.outlook"),
    "chatgpt": ("ChatGPT", "com.openai.chatgpt"),
    "firefox": ("Firefox", "org.mozilla.firefox"),
    "x": ("X", "com.twitter.android"),
    "threads": ("Threads", "com.instagram.barcelona"),
    "signal": ("Signal", "org.thoughtcrime.securesms"),
    "twitch": ("Twitch", "tv.twitch.android.app"),
    "capcut": ("CapCut", "com.lemon.lvoverseas"),
    "disney-plus": ("Disney+", "com.disney.disneyplus"),
    "prime-video": ("Prime Video", "com.amazon.avod.thirdpartyclient"),
    "microsoft-teams": ("Teams", "com.microsoft.teams"),
    "zoom": ("Zoom", "us.zoom.videomeetings"),
    "google-meet": ("Google Meet", "com.google.android.apps.tachyon"),
    "google-docs": ("Google Docs", "com.google.android.apps.docs.editors.docs"),
    "google-sheets": ("Google Sheets", "com.google.android.apps.docs.editors.sheets"),
    "onedrive": ("OneDrive", "com.microsoft.skydrive"),
    "google-translate": ("Google Translate", "com.google.android.apps.translate"),
    "google-keep": ("Google Keep", "com.google.android.keep"),
    "google-wallet": ("Google Wallet", "com.google.android.apps.walletnfcrel"),
    "cash-app": ("Cash App", "com.squareup.cash"),
    "venmo": ("Venmo", "com.venmo"),
    "ebay": ("eBay", "com.ebay.mobile"),
    "mcdonalds": ("McDonald's", "com.mcdonalds.app"),
    "starbucks": ("Starbucks", "com.starbucks.mobilecard"),
    "duolingo": ("Duolingo", "com.duolingo"),
    "waze": ("Waze", "com.waze"),
    "canva": ("Canva", "com.canva.editor"),
    "linkedin": ("LinkedIn", "com.linkedin.android"),
    "github": ("GitHub", "com.github.android"),
    "notion": ("Notion", "notion.id"),
    "microsoft-edge": ("Microsoft Edge", "com.microsoft.emmx"),
    "brave": ("Brave", "com.brave.browser"),
    "microsoft-authenticator": ("Microsoft Authenticator", "com.azure.authenticator"),
    "google-authenticator": ("Google Authenticator", "com.google.android.apps.authenticator2"),
    "samsung-smartthings": ("SmartThings", "com.samsung.android.oneconnect"),
    "good-lock": ("Good Lock", "com.samsung.android.goodlock"),
    "connect-iq-store": ("Connect IQ Store", "com.garmin.connectiq"),
    "steam": ("Steam", "com.valvesoftware.android.steam.community"),
    "reuters": ("Reuters", "com.thomsonreuters.reuters"),
    "home-depot": ("Home Depot", "com.thehomedepot"),
    "patreon": ("Patreon", "com.patreon.android"),
    'youtube-music': ('YouTube Music', 'com.google.android.apps.youtube.music'),
    'audible': ('Audible', 'com.audible.application'),
    'amazon-kindle': ('Amazon Kindle', 'com.amazon.kindle'),
    'pocket-casts': ('Pocket Casts', 'au.com.shiftyjelly.pocketcasts'),
    'vlc': ('VLC', 'org.videolan.vlc'),
    'shazam': ('Shazam', 'com.shazam.android'),
    'soundcloud': ('SoundCloud', 'com.soundcloud.android'),
    'hulu': ('Hulu', 'com.hulu.plus'),
    'target': ('Target', 'com.target.ui'),
    'costco': ('Costco', 'com.costco.app.android'),
    'best-buy': ('Best Buy', 'com.bestbuy.android'),
    'etsy': ('Etsy', 'com.etsy.android'),
    'aliexpress': ('AliExpress', 'com.alibaba.aliexpresshd'),
    'shein': ('SHEIN', 'com.zzkko'),
    'instacart': ('Instacart', 'com.instacart.client'),
    'airbnb': ('Airbnb', 'com.airbnb.android'),
    'booking': ('Booking.com', 'com.booking'),
    'expedia': ('Expedia', 'com.expedia.bookings'),
    'lyft': ('Lyft', 'me.lyft.android'),
    'uber-eats': ('Uber Eats', 'com.ubercab.eats'),
    'google-earth': ('Google Earth', 'com.google.earth'),
    'google-news': ('Google News', 'com.google.android.apps.magazines'),
    'galaxy-wearable': ('Galaxy Wearable', 'com.samsung.android.app.watchmanager'),
    'files-by-google': ('Files by Google', 'com.google.android.apps.nbu.files'),
    'adobe-acrobat': ('Adobe Acrobat', 'com.adobe.reader'),
    'microsoft-word': ('Microsoft Word', 'com.microsoft.office.word'),
    'microsoft-excel': ('Microsoft Excel', 'com.microsoft.office.excel'),
    'microsoft-powerpoint': ('PowerPoint', 'com.microsoft.office.powerpoint'),
    'google-slides': ('Google Slides', 'com.google.android.apps.docs.editors.slides'),
    'google-lens': ('Google Lens', 'com.google.ar.lens'),
    'roblox': ('Roblox', 'com.roblox.client'),
    'minecraft': ('Minecraft', 'com.mojang.minecraftpe'),
}
# Independent literals from the inspected 48-row intake, SHA256 9711de129883dca9e806dcc60e821a3d1de84366f0d2c16306fa39efcccbee5d.
SIXTH_EXPECTED_APPS = (
    {
        "id": "slack",
        "label": "Slack",
        "store_title": "Slack",
        "kind": "app",
        "category": "workplace",
        "android_package": "com.Slack",
        "store_url": "https://play.google.com/store/apps/details?id=com.Slack",
        "selection_basis": "Missing named workplace messaging assignment alongside retained Teams and Discord."
    },
    {
        "id": "trello",
        "label": "Trello",
        "store_title": "Trello: Personal Planner App",
        "kind": "app",
        "category": "productivity",
        "android_package": "com.trello",
        "store_url": "https://play.google.com/store/apps/details?id=com.trello",
        "selection_basis": "Missing named board and personal-planning assignment."
    },
    {
        "id": "todoist",
        "label": "Todoist",
        "store_title": "Todoist: To Do List & Calendar",
        "kind": "app",
        "category": "productivity",
        "android_package": "com.todoist",
        "store_url": "https://play.google.com/store/apps/details?id=com.todoist",
        "selection_basis": "Missing named to-do and calendar-planning assignment."
    },
    {
        "id": "ticktick",
        "label": "TickTick",
        "store_title": "TickTick:To Do List & Calendar",
        "kind": "app",
        "category": "productivity",
        "android_package": "com.ticktick.task",
        "store_url": "https://play.google.com/store/apps/details?id=com.ticktick.task",
        "selection_basis": "Missing second named task-list and calendar-planning assignment."
    },
    {
        "id": "evernote",
        "label": "Evernote",
        "store_title": "Evernote - Note Organizer",
        "kind": "app",
        "category": "notes",
        "android_package": "com.evernote",
        "store_url": "https://play.google.com/store/apps/details?id=com.evernote",
        "selection_basis": "Missing named note-organizing assignment alongside retained Samsung Notes and Google Keep."
    },
    {
        "id": "obsidian",
        "label": "Obsidian",
        "store_title": "Obsidian",
        "kind": "app",
        "category": "notes",
        "android_package": "md.obsidian",
        "store_url": "https://play.google.com/store/apps/details?id=md.obsidian",
        "selection_basis": "Missing named local-knowledge and note-taking assignment."
    },
    {
        "id": "dropbox",
        "label": "Dropbox",
        "store_title": "Dropbox: Secure Cloud Storage",
        "kind": "app",
        "category": "cloud-storage",
        "android_package": "com.dropbox.android",
        "store_url": "https://play.google.com/store/apps/details?id=com.dropbox.android",
        "selection_basis": "Missing named file-storage and sharing assignment alongside retained Google Drive and OneDrive."
    },
    {
        "id": "proton-mail",
        "label": "Proton Mail",
        "store_title": "Proton Mail: Encrypted Email",
        "kind": "app",
        "category": "email",
        "android_package": "ch.protonmail.android",
        "store_url": "https://play.google.com/store/apps/details?id=ch.protonmail.android",
        "selection_basis": "Missing named mail-service assignment alongside retained Gmail and Outlook."
    },
    {
        "id": "yahoo-mail",
        "label": "Yahoo Mail",
        "store_title": "Yahoo Mail: Email & Planner",
        "kind": "app",
        "category": "email",
        "android_package": "com.yahoo.mobile.client.android.mail",
        "store_url": "https://play.google.com/store/apps/details?id=com.yahoo.mobile.client.android.mail",
        "selection_basis": "Missing named mail-service and inbox-organizing assignment."
    },
    {
        "id": "google-tasks",
        "label": "Google Tasks",
        "store_title": "Google Tasks",
        "kind": "app",
        "category": "productivity",
        "android_package": "com.google.android.apps.tasks",
        "store_url": "https://play.google.com/store/apps/details?id=com.google.android.apps.tasks",
        "selection_basis": "Missing named Google task-list assignment, separate from the retained Calendar app."
    },
    {
        "id": "google-one",
        "label": "Google One",
        "store_title": "Google One",
        "kind": "app",
        "category": "cloud-storage",
        "android_package": "com.google.android.apps.subscriptions.red",
        "store_url": "https://play.google.com/store/apps/details?id=com.google.android.apps.subscriptions.red",
        "selection_basis": "Missing named Google storage-management and phone-backup assignment, separate from Drive."
    },
    {
        "id": "microsoft-copilot",
        "label": "Microsoft Copilot",
        "store_title": "Microsoft Copilot",
        "kind": "app",
        "category": "productivity",
        "android_package": "com.microsoft.office.officehubrow",
        "store_url": "https://play.google.com/store/apps/details?id=com.microsoft.office.officehubrow",
        "selection_basis": "Missing inspected work-connected Microsoft Copilot phone-app assignment; package is com.microsoft.office.officehubrow. The older standalone com.microsoft.copilot identity was not verified and is not treated as equivalent."
    },
    {
        "id": "google-gemini",
        "label": "Google Gemini",
        "store_title": "Google Gemini",
        "kind": "app",
        "category": "assistant",
        "android_package": "com.google.android.apps.bard",
        "store_url": "https://play.google.com/store/apps/details?id=com.google.android.apps.bard",
        "selection_basis": "Missing named Google assistant-app assignment."
    },
    {
        "id": "claude",
        "label": "Claude",
        "store_title": "Claude by Anthropic",
        "kind": "app",
        "category": "assistant",
        "android_package": "com.anthropic.claude",
        "store_url": "https://play.google.com/store/apps/details?id=com.anthropic.claude",
        "selection_basis": "Missing named Anthropic assistant-app assignment."
    },
    {
        "id": "perplexity",
        "label": "Perplexity",
        "store_title": "Perplexity - Ask Anything",
        "kind": "app",
        "category": "search",
        "android_package": "ai.perplexity.app.android",
        "store_url": "https://play.google.com/store/apps/details?id=ai.perplexity.app.android",
        "selection_basis": "Missing named question-answering and search-app assignment."
    },
    {
        "id": "bitwarden",
        "label": "Bitwarden",
        "store_title": "Bitwarden Password Manager",
        "kind": "app",
        "category": "password-management",
        "android_package": "com.x8bit.bitwarden",
        "store_url": "https://play.google.com/store/apps/details?id=com.x8bit.bitwarden",
        "selection_basis": "Missing named password-manager assignment; no security endorsement is implied by inclusion."
    },
    {
        "id": "apple-music",
        "label": "Apple Music",
        "store_title": "Apple Music",
        "kind": "app",
        "category": "music",
        "android_package": "com.apple.android.music",
        "store_url": "https://play.google.com/store/apps/details?id=com.apple.android.music",
        "selection_basis": "Missing named music-service assignment alongside retained Spotify and YouTube Music."
    },
    {
        "id": "apple-tv",
        "label": "Apple TV",
        "store_title": "Apple TV: Shows, Movies & More",
        "kind": "app",
        "category": "streaming",
        "android_package": "com.apple.atve.androidtv.appletv",
        "store_url": "https://play.google.com/store/apps/details?id=com.apple.atve.androidtv.appletv",
        "selection_basis": "Missing named video-service assignment; Apple's official Android announcement explicitly includes phones, tablets and foldables."
    },
    {
        "id": "hbo-max",
        "label": "HBO Max",
        "store_title": "HBO Max: Stream TV & Movies",
        "kind": "app",
        "category": "streaming",
        "android_package": "com.wbd.stream",
        "store_url": "https://play.google.com/store/apps/details?id=com.wbd.stream",
        "selection_basis": "Missing current HBO Max streaming assignment using its inspected com.wbd.stream listing."
    },
    {
        "id": "peacock",
        "label": "Peacock",
        "store_title": "Peacock TV: Stream TV & Movies",
        "kind": "app",
        "category": "streaming",
        "android_package": "com.peacocktv.peacockandroid",
        "store_url": "https://play.google.com/store/apps/details?id=com.peacocktv.peacockandroid",
        "selection_basis": "Missing named video-streaming assignment."
    },
    {
        "id": "paramount-plus",
        "label": "Paramount+",
        "store_title": "Paramount+",
        "kind": "app",
        "category": "streaming",
        "android_package": "com.cbs.app",
        "store_url": "https://play.google.com/store/apps/details?id=com.cbs.app",
        "selection_basis": "Missing named video-streaming assignment."
    },
    {
        "id": "plex",
        "label": "Plex",
        "store_title": "Plex: Find Movies & TV Shows",
        "kind": "app",
        "category": "streaming",
        "android_package": "com.plexapp.android",
        "store_url": "https://play.google.com/store/apps/details?id=com.plexapp.android",
        "selection_basis": "Missing named media-library and streaming assignment."
    },
    {
        "id": "tubi",
        "label": "Tubi",
        "store_title": "Tubi: Free Movies & Live TV",
        "kind": "app",
        "category": "streaming",
        "android_package": "com.tubitv",
        "store_url": "https://play.google.com/store/apps/details?id=com.tubitv",
        "selection_basis": "Missing named video-streaming and live-TV assignment."
    },
    {
        "id": "pluto-tv",
        "label": "Pluto TV",
        "store_title": "Pluto TV: Watch Free Movies/TV",
        "kind": "app",
        "category": "streaming",
        "android_package": "tv.pluto.android",
        "store_url": "https://play.google.com/store/apps/details?id=tv.pluto.android",
        "selection_basis": "Missing named live-TV and streaming assignment."
    },
    {
        "id": "crunchyroll",
        "label": "Crunchyroll",
        "store_title": "Crunchyroll: Anime Streaming",
        "kind": "app",
        "category": "streaming",
        "android_package": "com.crunchyroll.crunchyroid",
        "store_url": "https://play.google.com/store/apps/details?id=com.crunchyroll.crunchyroid",
        "selection_basis": "Missing named anime-streaming assignment."
    },
    {
        "id": "pandora",
        "label": "Pandora",
        "store_title": "Pandora - Music & Podcasts",
        "kind": "app",
        "category": "music",
        "android_package": "com.pandora.android",
        "store_url": "https://play.google.com/store/apps/details?id=com.pandora.android",
        "selection_basis": "Missing named music and podcast-service assignment."
    },
    {
        "id": "iheartradio",
        "label": "iHeart",
        "store_title": "iHeart: Music, Radio, Podcasts",
        "kind": "app",
        "category": "radio",
        "android_package": "com.clearchannel.iheartradio.controller",
        "store_url": "https://play.google.com/store/apps/details?id=com.clearchannel.iheartradio.controller",
        "selection_basis": "Missing named iHeart music, radio and podcast assignment; requested stable id iheartradio retained."
    },
    {
        "id": "siriusxm",
        "label": "SiriusXM",
        "store_title": "SiriusXM: Music, Sports & Talk",
        "kind": "app",
        "category": "radio",
        "android_package": "com.sirius",
        "store_url": "https://play.google.com/store/apps/details?id=com.sirius",
        "selection_basis": "Missing named music, sports and talk-radio assignment."
    },
    {
        "id": "adobe-lightroom",
        "label": "Adobe Lightroom",
        "store_title": "Lightroom Photo & Video Editor",
        "kind": "app",
        "category": "photo-editing",
        "android_package": "com.adobe.lrmobile",
        "store_url": "https://play.google.com/store/apps/details?id=com.adobe.lrmobile",
        "selection_basis": "Missing named Adobe photo-editing assignment."
    },
    {
        "id": "photoshop-express",
        "label": "Photoshop Express",
        "store_title": "Photoshop Express Photo Editor",
        "kind": "app",
        "category": "photo-editing",
        "android_package": "com.adobe.psmobile",
        "store_url": "https://play.google.com/store/apps/details?id=com.adobe.psmobile",
        "selection_basis": "Missing named Adobe quick photo-editing assignment, separate from Lightroom."
    },
    {
        "id": "snapseed",
        "label": "Snapseed",
        "store_title": "Snapseed",
        "kind": "app",
        "category": "photo-editing",
        "android_package": "com.niksoftware.snapseed",
        "store_url": "https://play.google.com/store/apps/details?id=com.niksoftware.snapseed",
        "selection_basis": "Missing named photo-editing assignment."
    },
    {
        "id": "picsart",
        "label": "Picsart",
        "store_title": "Picsart AI Photo Editor, Video",
        "kind": "app",
        "category": "photo-editing",
        "android_package": "com.picsart.studio",
        "store_url": "https://play.google.com/store/apps/details?id=com.picsart.studio",
        "selection_basis": "Missing named photo and video-editing assignment."
    },
    {
        "id": "strava",
        "label": "Strava",
        "store_title": "Strava: Run, Bike, Walk",
        "kind": "app",
        "category": "fitness",
        "android_package": "com.strava",
        "store_url": "https://play.google.com/store/apps/details?id=com.strava",
        "selection_basis": "Missing named activity-tracking and fitness-community assignment."
    },
    {
        "id": "fitbit",
        "label": "Google Health (Fitbit)",
        "store_title": "Google Health (Fitbit)",
        "kind": "app",
        "category": "fitness",
        "android_package": "com.fitbit.FitbitMobile",
        "store_url": "https://play.google.com/store/apps/details?id=com.fitbit.FitbitMobile",
        "selection_basis": "Missing current Google Health (Fitbit) assignment; current title and existing Fitbit package were directly inspected."
    },
    {
        "id": "google-fit",
        "label": "Google Fit",
        "store_title": "Google Fit: Activity Tracking",
        "kind": "app",
        "category": "fitness",
        "android_package": "com.google.android.apps.fitness",
        "store_url": "https://play.google.com/store/apps/details?id=com.google.android.apps.fitness",
        "selection_basis": "Still-listed Google Fit activity-tracking assignment with a distinct package; Google has announced migration into Google Health, without establishing its completion here."
    },
    {
        "id": "myfitnesspal",
        "label": "MyFitnessPal",
        "store_title": "MyFitnessPal: Calorie Counter",
        "kind": "app",
        "category": "nutrition",
        "android_package": "com.myfitnesspal.android",
        "store_url": "https://play.google.com/store/apps/details?id=com.myfitnesspal.android",
        "selection_basis": "Missing named food-log and nutrition-tracking assignment."
    },
    {
        "id": "alltrails",
        "label": "AllTrails",
        "store_title": "AllTrails: Hike, Bike & Run",
        "kind": "app",
        "category": "outdoors",
        "android_package": "com.alltrails.alltrails",
        "store_url": "https://play.google.com/store/apps/details?id=com.alltrails.alltrails",
        "selection_basis": "Missing named trail and outdoor-route assignment."
    },
    {
        "id": "komoot",
        "label": "Komoot",
        "store_title": "komoot - hike, bike & run",
        "kind": "app",
        "category": "outdoors",
        "android_package": "de.komoot.android",
        "store_url": "https://play.google.com/store/apps/details?id=de.komoot.android",
        "selection_basis": "Missing second named hiking, cycling and route-planning assignment."
    },
    {
        "id": "amazon-alexa",
        "label": "Amazon Alexa",
        "store_title": "Amazon Alexa",
        "kind": "app",
        "category": "smart-home",
        "android_package": "com.amazon.dee.app",
        "store_url": "https://play.google.com/store/apps/details?id=com.amazon.dee.app",
        "selection_basis": "Missing named home and voice-assistant companion assignment."
    },
    {
        "id": "ring",
        "label": "Ring",
        "store_title": "Ring - Always Home",
        "kind": "app",
        "category": "smart-home",
        "android_package": "com.ringapp",
        "store_url": "https://play.google.com/store/apps/details?id=com.ringapp",
        "selection_basis": "Missing named Ring home-device companion assignment."
    },
    {
        "id": "blink",
        "label": "Blink",
        "store_title": "Blink Home Monitor",
        "kind": "app",
        "category": "smart-home",
        "android_package": "com.immediasemi.android.blink",
        "store_url": "https://play.google.com/store/apps/details?id=com.immediasemi.android.blink",
        "selection_basis": "Missing named Blink home-camera companion assignment."
    },
    {
        "id": "google-home",
        "label": "Google Home",
        "store_title": "Google Home",
        "kind": "app",
        "category": "smart-home",
        "android_package": "com.google.android.apps.chromecast.app",
        "store_url": "https://play.google.com/store/apps/details?id=com.google.android.apps.chromecast.app",
        "selection_basis": "Missing named Google home-device companion assignment alongside retained SmartThings."
    },
    {
        "id": "zillow",
        "label": "Zillow",
        "store_title": "Zillow: Homes for Sale & Rent",
        "kind": "app",
        "category": "property",
        "android_package": "com.zillow.android.zillowmap",
        "store_url": "https://play.google.com/store/apps/details?id=com.zillow.android.zillowmap",
        "selection_basis": "Missing named property-search assignment."
    },
    {
        "id": "chase",
        "label": "Chase",
        "store_title": "Chase Mobile",
        "kind": "app",
        "category": "banking",
        "android_package": "com.chase.sig.android",
        "store_url": "https://play.google.com/store/apps/details?id=com.chase.sig.android",
        "selection_basis": "Missing named Chase phone-banking assignment; inclusion does not imply personal account ownership."
    },
    {
        "id": "capital-one",
        "label": "Capital One",
        "store_title": "Capital One Mobile",
        "kind": "app",
        "category": "banking",
        "android_package": "com.konylabs.capitalone",
        "store_url": "https://play.google.com/store/apps/details?id=com.konylabs.capitalone",
        "selection_basis": "Missing named Capital One phone-banking assignment; inclusion does not imply personal account ownership."
    },
    {
        "id": "chime",
        "label": "Chime",
        "store_title": "Chime® – Fee-Free Banking",
        "kind": "app",
        "category": "banking",
        "android_package": "com.onedebit.chime",
        "store_url": "https://play.google.com/store/apps/details?id=com.onedebit.chime",
        "selection_basis": "Missing named Chime phone-banking assignment; inclusion does not imply personal account ownership."
    },
    {
        "id": "ups",
        "label": "UPS",
        "store_title": "UPS",
        "kind": "app",
        "category": "shipping",
        "android_package": "com.ups.mobile.android",
        "store_url": "https://play.google.com/store/apps/details?id=com.ups.mobile.android",
        "selection_basis": "Missing named parcel-tracking and shipping-service assignment."
    },
    {
        "id": "fedex",
        "label": "FedEx",
        "store_title": "FedEx Mobile",
        "kind": "app",
        "category": "shipping",
        "android_package": "com.fedex.ida.android",
        "store_url": "https://play.google.com/store/apps/details?id=com.fedex.ida.android",
        "selection_basis": "Missing second named parcel-tracking and shipping-service assignment."
    },
)
EXPECTED_APPS.update({row["id"]: (row["label"], row["android_package"])
                      for row in SIXTH_EXPECTED_APPS})
EXPECTED_APPS.update({'chipotle': ('Chipotle', 'com.chipotle.ordering'),
 'taco-bell': ('Taco Bell', 'com.tacobell.ordering'),
 'wendys': ("Wendy's", 'com.wendys.nutritiontool'),
 'burger-king': ('Burger King', 'com.emn8.mobilem8.nativeapp.bk'),
 'dunkin': ("Dunkin'", 'com.dunkinbrands.otgo'),
 'chick-fil-a': ('Chick-fil-A', 'com.chickfila.cfaflagship'),
 'dominos': ("Domino's", 'com.dominospizza'),
 'pizza-hut': ('Pizza Hut', 'com.yum.pizzahut'),
 'subway': ('Subway', 'com.subway.mobile.subwayapp03'),
 'panera-bread': ('Panera Bread', 'com.panera.bread'),
 'kfc-us': ('KFC US', 'com.kfc.us.mobile'),
 'grubhub': ('Grubhub', 'com.grubhub.android')})
EIGHTH_EXPECTED_APPS = (
    ("fly-delta", "Fly Delta", "com.delta.mobile.android"),
    ("united-airlines", "United Airlines", "com.united.mobile.android"),
    ("american-airlines", "American Airlines", "com.aa.android"),
    ("southwest-airlines", "Southwest Airlines", "com.southwestairlines.mobile"),
    ("amtrak", "Amtrak", "com.amtrak.rider"),
    ("transit", "Transit", "com.thetransitapp.droid"),
    ("moovit", "Moovit", "com.tranzmate"),
    ("citymapper", "Citymapper", "com.citymapper.app.release"),
    ("tripit", "TripIt", "com.tripit"),
    ("hopper", "Hopper", "com.hopper.mountainview.play"),
)
EXPECTED_APPS.update({identifier: (label, package)
                      for identifier, label, package in EIGHTH_EXPECTED_APPS})

NINTH_EXPECTED_APPS = (
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
EXPECTED_APPS.update({identifier: (label, package)
                      for identifier, label, package in NINTH_EXPECTED_APPS})

# Independent literals from the inspected official weather package identities.
TENTH_EXPECTED_APPS = (
    ("accuweather", "AccuWeather", "com.accuweather.android"),
    ("weather-channel", "The Weather Channel", "com.weather.Weather"),
    ("weather-underground", "Weather Underground", "com.wunderground.android.weather"),
    ("windy-com", "Windy.com", "com.windyty.android"),
    ("myradar", "MyRadar", "com.acmeaom.android.myradar"),
    ("weatherbug", "WeatherBug", "com.aws.android"),
    ("one-weather", "1Weather", "com.handmark.expressweather"),
    ("clime", "Clime", "com.apalon.weatherradar.free"),
    ("windfinder", "Windfinder", "com.studioeleven.windfinder"),
    ("rainviewer", "RainViewer", "com.lucky_apps.RainViewer"),
)
EXPECTED_APPS.update({identifier: (label, package)
                      for identifier, label, package in TENTH_EXPECTED_APPS})

# Independent literal assignment identities from the inspected official listings.
ELEVENTH_EXPECTED_APPS = (
    ("nike-run-club", "Nike Run Club", "com.nike.plusgps"),
    ("adidas-running", "adidas Running", "com.runtastic.android"),
    ("asics-runkeeper", "ASICS Runkeeper", "com.fitnesskeeper.runkeeper.pro"),
    ("map-my-run", "Map My Run", "com.mapmyrun.android2"),
    ("runna", "Runna", "com.runbuddy.prod"),
    ("trainingpeaks", "TrainingPeaks", "com.peaksware.trainingpeaks"),
    ("zwift-companion", "Zwift Companion", "com.zwift.android.prod"),
    ("relive", "Relive", "cc.relive.reliveapp"),
)
EXPECTED_APPS.update({identifier: (label, package)
                      for identifier, label, package in ELEVENTH_EXPECTED_APPS})

# Independent learning assignment literals from the inspected official listings.
TWELFTH_EXPECTED_APPS = (
    ("google-classroom", "Google Classroom", "com.google.android.apps.classroom"),
    ("khan-academy", "Khan Academy", "org.khanacademy.android"),
    ("coursera", "Coursera", "org.coursera.android"),
    ("udemy", "Udemy", "com.udemy.android"),
    ("edx", "edX", "org.edx.mobile"),
    ("quizlet", "Quizlet", "com.quizlet.quizletandroid"),
    ("photomath", "Photomath", "com.microblink.photomath"),
    ("brainly", "Brainly", "co.brainly"),
)
EXPECTED_APPS.update({identifier: (label, package)
                      for identifier, label, package in TWELFTH_EXPECTED_APPS})

# Independent reading assignment literals from the inspected official listings.
THIRTEENTH_EXPECTED_APPS = (
    ('google-play-books', 'Google Play Books', 'com.google.android.apps.books'),
    ('libby', 'Libby', 'com.overdrive.mobile.android.libby'),
    ('kobo-books', 'Kobo Books', 'com.kobobooks.android'),
    ('goodreads', 'Goodreads', 'com.goodreads'),
    ('wattpad', 'Wattpad', 'wp.wattpad'),
    ('webtoon', 'WEBTOON', 'com.naver.linewebtoon'),
    ('readera', 'ReadEra', 'org.readera'),
    ('moon-reader', 'Moon+ Reader', 'com.flyersoft.moonreader'),
)
EXPECTED_APPS.update({identifier: (label, package)
                      for identifier, label, package in THIRTEENTH_EXPECTED_APPS})

FOURTEENTH_EXPECTED_APPS = (
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
EXPECTED_APPS.update({identifier: (label, package)
                      for identifier, label, package in FOURTEENTH_EXPECTED_APPS})

NS = "{http://www.w3.org/2000/svg}"


def tree_snapshot(root):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*") if path.is_file()}


def geometry(svg):
    root = ET.fromstring(svg)
    root.attrib.pop("aria-label", None)
    for element in root.iter():
        for role in ("fill", "stroke"):
            if re.fullmatch(r"#[0-9a-fA-F]{6}", element.get(role, "")):
                element.attrib.pop(role)
    return ET.tostring(root)


def path_hull(data):
    """Conservatively bound absolute line/Bezier paths by endpoints and controls."""
    tokens = re.findall(r"[A-Za-z]|-?\d+(?:\.\d+)?", data)
    points = []
    x = y = 0
    index = 0
    while index < len(tokens):
        command = tokens[index]
        index += 1
        if command == "Z":
            continue
        counts = {"M": 2, "L": 2, "H": 1, "V": 1, "Q": 4, "C": 6}
        if command not in counts:
            raise AssertionError(f"Unqualified SVG path command {command}")
        count = counts[command]
        values = [float(value) for value in tokens[index:index + count]]
        if len(values) != count:
            raise AssertionError("Incomplete SVG path")
        index += count
        if command == "H":
            x = values[0]
            points.append((x, y))
        elif command == "V":
            y = values[0]
            points.append((x, y))
        else:
            points.extend(zip(values[::2], values[1::2]))
            x, y = values[-2:]
    return points


class FunctionalIconTests(unittest.TestCase):
    def setUp(self):
        self.legacy_document = json.loads((ROOT / "tokens.json").read_text(encoding="utf-8"))
        self.document = json.loads((ROOT / "tokens-monochrome.json").read_text(encoding="utf-8"))

    def test_exact_function_inventory_and_each_manifest_digest(self):
        files = icons.render_icons(self.document)
        expected = {f"{theme}/{name}.svg" for theme in ("Clair", "Obscur") for name in NAMES}
        self.assertEqual(set(files), expected | {"manifest.json"})
        manifest = json.loads(files["manifest.json"])
        self.assertEqual(manifest["functions"], NAMES)
        self.assertEqual(manifest["version"], "0.18.0")
        self.assertEqual(manifest["token_schema"], 1)
        self.assertEqual(manifest["token_version"], "1.0.0")
        self.assertEqual(manifest["palette_variant"], "monochrome")
        self.assertEqual(len(manifest["files"]), 562)
        for record in manifest["files"]:
            self.assertEqual(record["path"], f'{record["appearance"]}/{record["function"]}.svg')
            payload = files[record["path"]]
            self.assertEqual(record["bytes"], len(payload))
            self.assertEqual(record["sha256"], hashlib.sha256(payload).hexdigest())
        # Relabeling the same drawing must not count as new geometry.
        relabeled = files["Clair/phone.svg"].replace(b'aria-label="phone"', b'aria-label="messages"')
        self.assertEqual(geometry(relabeled), geometry(files["Clair/phone.svg"]))
        # Named choices must have different drawings, rather than relabeled aliases.
        self.assertEqual(len({geometry(files[f"Clair/{name}.svg"]) for name in NAMES}), 281)

    def test_palette_roles_and_geometry_are_shared_without_hardcoded_colors(self):
        files = icons.render_icons(self.document)
        for name in NAMES:
            self.assertEqual(geometry(files[f"Clair/{name}.svg"]), geometry(files[f"Obscur/{name}.svg"]))
            for theme in ("Clair", "Obscur"):
                root = ET.fromstring(files[f"{theme}/{name}.svg"])
                palette = self.document["themes"][theme]
                self.assertEqual(root.find(NS + "rect").get("fill"), palette["panel"])
                self.assertEqual(root.find(NS + "g").get("stroke"), palette["text"])
                colors = {value for element in root.iter() for key, value in element.attrib.items()
                          if key in ("stroke", "fill") and value != "none"}
                self.assertEqual(colors, {palette["panel"], palette["text"], palette["accent"]})
        # The explicit-document library API remains useful for controlled palette
        # experiments; the CLI and exporter admit the version's shared document.
        files = icons.render_icons(self.legacy_document, version="0.5.0")
        changed = copy.deepcopy(self.legacy_document)
        changed["themes"]["Clair"].update(panel="#fcfbf7", text="#252525", accent="#355e77")
        changed["version"] = "2.3.4"
        updated = icons.render_icons(changed, version="0.5.0")
        for name in THIRD_NAMES:
            self.assertNotEqual(updated[f"Clair/{name}.svg"], files[f"Clair/{name}.svg"])
            self.assertEqual(updated[f"Obscur/{name}.svg"], files[f"Obscur/{name}.svg"])
            self.assertEqual(geometry(updated[f"Clair/{name}.svg"]), geometry(files[f"Clair/{name}.svg"]))
        self.assertEqual(json.loads(updated["manifest.json"])["token_version"], "2.3.4")

    def test_output_is_deterministic_and_does_not_mutate_tokens(self):
        before = copy.deepcopy(self.document)
        reordered = dict(reversed(list(self.document.items())))
        reordered["themes"] = {name: dict(reversed(list(values.items())))
                               for name, values in reversed(list(self.document["themes"].items()))}
        self.assertEqual(icons.render_icons(reordered), icons.render_icons(self.document))
        self.assertEqual(self.document, before)

    def test_current_monochrome_palette_rejects_color_and_impure_endpoints_before_output(self):
        for appearance, background, foreground in (("Clair", "#ffffff", "#000000"),
                                                    ("Obscur", "#000000", "#ffffff")):
            palette = self.document["themes"][appearance]
            self.assertEqual({palette[role].lower() for role in ("canvas", "panel")}, {background})
            self.assertEqual({palette[role].lower() for role in ("text", "accent")}, {foreground})
            self.assertTrue(all(len({color[index:index + 2].lower() for index in (1, 3, 5)}) == 1
                                for color in palette.values()))
        invalid = [self.legacy_document]
        for role, value in (("muted", "#555554"), ("panel", "#fefefe"), ("accent", "#111111")):
            document = copy.deepcopy(self.document)
            document["themes"]["Clair"][role] = value
            invalid.append(document)
        for document in invalid:
            with self.subTest(document=document), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "never-created"
                with self.assertRaisesRegex(ValueError, "Monochrome"):
                    icons.build_icons(document, output)
                self.assertFalse(output.exists())

    def test_cli_selects_versioned_tokens_and_accepts_only_an_explicit_matching_copy(self):
        self.assertEqual(icons.token_path(), ROOT / "tokens-monochrome.json")
        for version in ("0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0"):
            self.assertEqual(icons.token_path(version), ROOT / "tokens.json")
        for version in ("0.6.0", "0.7.0", "0.8.0", "0.9.0", "0.10.0", "0.11.0", "0.12.0", "0.13.0", "0.14.0", "0.15.0", "0.16.0", "0.17.0"):
            self.assertEqual(icons.token_path(version), ROOT / "tokens-monochrome.json")
        for version, document in (("0.5.0", self.legacy_document), ("0.6.0", self.document),
                                  ("0.7.0", self.document), ("0.8.0", self.document),
                                  ("0.9.0", self.document), ("0.10.0", self.document),
                                  ("0.11.0", self.document), ("0.12.0", self.document),
                                  ("0.13.0", self.document), ("0.14.0", self.document),
                                  ("0.15.0", self.document), ("0.16.0", self.document), ("0.17.0", self.document)):
            with self.subTest(version=version), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                explicit = base / "explicit.json"
                explicit.write_text(json.dumps(document, sort_keys=True), encoding="utf-8")
                output = base / "icons"
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(icons.main(["--version", version, "--tokens", str(explicit),
                                                "--output", str(output)]), 0)
                self.assertEqual(tree_snapshot(output), icons.render_icons(document, version=version))
                wrong = self.document if version == "0.5.0" else self.legacy_document
                explicit.write_text(json.dumps(wrong), encoding="utf-8")
                unchanged = tree_snapshot(output)
                refused = base / "never-created"
                with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                    icons.main(["--version", version, "--tokens", str(explicit), "--output", str(refused)])
                self.assertEqual(error.exception.code, 1)
                self.assertFalse(refused.exists())
                self.assertEqual(tree_snapshot(output), unchanged)

    def test_svg_has_only_local_geometric_primitives_and_embedded_project_license(self):
        license_body = (ROOT / "LICENSE").read_text(encoding="utf-8").replace("\r\n", "\n").rstrip() + "\n"
        allowed = {"svg", "rect", "g", "path", "line", "circle", "ellipse"}
        for path, payload in icons.render_icons(self.document).items():
            if not path.endswith(".svg"):
                continue
            self.assertIn(license_body, payload.decode())
            root = ET.fromstring(payload)
            labels = {entry["id"]: entry["label"] for entry in icons.icon_catalog()}
            name = Path(path).stem
            self.assertEqual(root.get("aria-label"), labels[name] if name in APP_NAMES else name)
            for element in root.iter():
                self.assertIn(element.tag.removeprefix(NS), allowed)
                for key, value in element.attrib.items():
                    self.assertNotIn("href", key.lower())
                    self.assertFalse(key.lower().startswith("on"))
                    self.assertNotIn("url(", value.lower())
                    self.assertNotIn("font", key.lower())
                self.assertFalse((element.text or "").strip())

    def test_glyph_control_hulls_and_strokes_stay_inside_safe_tile_inset(self):
        for name in NAMES:
            root = ET.fromstring(icons.render_icons(self.document)[f"Clair/{name}.svg"])
            self.assertEqual((root.get("width"), root.get("height"), root.get("viewBox")),
                             ("512", "512", "0 0 512 512"))
            tile = root.find(NS + "rect")
            self.assertEqual({key: tile.get(key) for key in ("x", "y", "width", "height", "rx")},
                             {"x": "32", "y": "32", "width": "448", "height": "448", "rx": "104"})
            group = root.find(NS + "g")
            self.assertEqual(group.get("stroke-width"), "16")
            self.assertEqual(group.get("stroke-linecap"), "round")
            self.assertEqual(group.get("stroke-linejoin"), "round")
            for element in group:
                tag = element.tag.removeprefix(NS)
                values = element.attrib
                if tag == "path":
                    points = path_hull(values["d"])
                elif tag == "line":
                    points = [(float(values["x1"]), float(values["y1"])),
                              (float(values["x2"]), float(values["y2"]))]
                elif tag == "rect":
                    x, y, width, height = (float(values[key]) for key in ("x", "y", "width", "height"))
                    points = [(x, y), (x + width, y + height)]
                elif tag in ("circle", "ellipse"):
                    x, y = float(values["cx"]), float(values["cy"])
                    rx, ry = ((float(values["r"]),) * 2 if tag == "circle"
                              else (float(values["rx"]), float(values["ry"])))
                    points = [(x - rx, y - ry), (x + rx, y + ry)]
                else:
                    self.fail(f"Unqualified geometric primitive {tag}")
                self.assertTrue(points)
                for x, y in points:
                    self.assertGreaterEqual(min(x, y), 112, (name, tag, x, y))
                    self.assertLessEqual(max(x, y), 400, (name, tag, x, y))
                    self.assertGreaterEqual(min(x - 8, y - 8), 104)
                    self.assertLessEqual(max(x + 8, y + 8), 408)

    def test_original_version_rebuilds_exact_accepted_archive_and_stays_separate(self):
        from themeforge.build import _zip_bytes
        from themeforge.legal import license_text
        legacy = icons.render_icons(self.legacy_document, version="0.1.0")
        current = icons.render_icons(self.document, version="0.17.0")
        refined = icons.render_icons(self.legacy_document, version="0.2.0")
        first_apps = icons.render_icons(self.legacy_document, version="0.3.0")
        second_apps = icons.render_icons(self.legacy_document, version="0.4.0")
        third_apps = icons.render_icons(self.legacy_document, version="0.5.0")
        first_monochrome = icons.render_icons(self.document, version="0.6.0")
        companion_apps = icons.render_icons(self.document, version="0.7.0")
        broad_apps = icons.render_icons(self.document, version="0.8.0")
        archived = {**legacy, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(archived)).hexdigest(),
                         "040d7f472ca12d6cf115daaf2631b83477183dee42f0b91c6133e62322014e34")
        self.assertEqual(json.loads(legacy["manifest.json"])["stroke_width"], 12)
        refined_archive = {**refined, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(refined_archive)).hexdigest(),
                         "6ae67a5aab7f4e0a50537bb6dcf3b383c5fc6e9e001d68db12a7413aaa376312")
        first_archive = {**first_apps, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(first_archive)).hexdigest(),
                         "d217cab68c1c118511078c189ec672b80cbcb29be285bf5cc58123516791e756")
        second_archive = {**second_apps, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(second_archive)).hexdigest(),
                         "fc2540a7bf9a6d580a3238904b6e7e4f6b77ca5df5797cc7ce3a6de782cda0cf")
        third_archive = {**third_apps, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(third_archive)).hexdigest(),
                         "2310c0151c0c3215e99d24a7aa92616a55dc726b2e38466427890223d778307a")
        monochrome_archive = {**first_monochrome, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(monochrome_archive)).hexdigest(),
                         "241efb1fe6584df4f66c84571bfe671059404e83be8d67876f415af6564a56bb")
        self.assertEqual(hashlib.sha256(first_monochrome["manifest.json"]).hexdigest(),
                         "57537e0ad06dee704400160d30ae47f4cce8beba557c347ef5236ac8da32ee92")
        companion_archive = {**companion_apps, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(companion_archive)).hexdigest(),
                         "aa18db922e824cd2bfa1ada2fbc08125af2605d9c5acb2ad8bfdb439985f4f05")
        self.assertEqual(hashlib.sha256(companion_apps["manifest.json"]).hexdigest(),
                         "a58049892930f817b1376c03510ab408c84d5336d908d885e4ab52e078d238ca")
        broad_archive = {**broad_apps, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(broad_archive)).hexdigest(),
                         "fcdaec582be7508b3e62bd9168695ea1650e33c8e53c3de46f3614ae53d833cf")
        self.assertEqual(hashlib.sha256(broad_apps["manifest.json"]).hexdigest(),
                         "7a8a35d6ba1186a718e970e26c5c6b7b19bf4949010c7bc89af3cb6063b95252")
        first_manifest = json.loads(first_apps["manifest.json"])
        current_manifest = json.loads(current["manifest.json"])
        self.assertEqual(first_manifest["functions"], PREVIOUS_NAMES)
        self.assertEqual(first_manifest["catalog_date"], "2026-10-18")
        self.assertEqual(first_manifest["catalog"], current_manifest["catalog"][:57])
        self.assertEqual(len(first_manifest["files"]), 114)
        for appearance in ("Clair", "Obscur"):
            for name in PREVIOUS_NAMES:
                path = f"{appearance}/{name}.svg"
                self.assertEqual(third_apps[path], first_apps[path])
        second_manifest = json.loads(second_apps["manifest.json"])
        self.assertEqual(second_manifest["functions"], SECOND_NAMES)
        self.assertEqual(second_manifest["catalog_date"], "2026-10-19")
        self.assertEqual(second_manifest["catalog"], current_manifest["catalog"][:81])
        self.assertEqual(len(second_manifest["files"]), 162)
        for appearance in ("Clair", "Obscur"):
            for name in SECOND_NAMES:
                path = f"{appearance}/{name}.svg"
                self.assertEqual(third_apps[path], second_apps[path])
        self.assertEqual(json.loads(third_apps["manifest.json"])["catalog"], current_manifest["catalog"][:89])
        monochrome_manifest = json.loads(first_monochrome["manifest.json"])
        self.assertEqual(monochrome_manifest["functions"], THIRD_NAMES)
        self.assertEqual(monochrome_manifest["catalog"], current_manifest["catalog"][:89])
        self.assertEqual(monochrome_manifest["token_version"], "1.0.0")
        self.assertEqual(monochrome_manifest["palette_variant"], "monochrome")
        self.assertEqual(len(monochrome_manifest["files"]), 178)
        for path, payload in first_monochrome.items():
            if path.endswith(".svg"):
                self.assertEqual(current[path], payload, path)
        companion_manifest = json.loads(companion_apps["manifest.json"])
        self.assertEqual(companion_manifest["functions"], FOURTH_NAMES)
        self.assertEqual(companion_manifest["catalog"], current_manifest["catalog"][:95])
        self.assertEqual(companion_manifest["palette_variant"], "monochrome")
        self.assertEqual(companion_manifest["token_version"], "1.0.0")
        self.assertEqual(len(companion_manifest["files"]), 190)
        for path, payload in companion_apps.items():
            if path.endswith(".svg"):
                self.assertEqual(current[path], payload, path)
        broad_manifest = json.loads(broad_apps["manifest.json"])
        self.assertEqual(broad_manifest["functions"], FIFTH_NAMES)
        self.assertEqual(broad_manifest["catalog"], current_manifest["catalog"][:127])
        self.assertEqual(len(broad_manifest["files"]), 254)
        for path, payload in broad_apps.items():
            if path.endswith(".svg"):
                self.assertEqual(current[path], payload, path)
        self.assertNotIn("palette_variant", json.loads(third_apps["manifest.json"]))
        for path in third_apps:
            if path.endswith(".svg"):
                self.assertNotEqual(current[path], third_apps[path])
                self.assertEqual(geometry(current[path]), geometry(third_apps[path]), path)
        self.assertNotIn("catalog", json.loads(refined["manifest.json"]))
        self.assertNotIn("catalog", json.loads(legacy["manifest.json"]))
        self.assertEqual(json.loads(refined["manifest.json"])["functions"], BASE_NAMES)
        for name in BASE_NAMES:
            self.assertNotEqual(current[f"Clair/{name}.svg"], legacy[f"Clair/{name}.svg"])
            for appearance in ("Clair", "Obscur"):
                self.assertEqual(third_apps[f"{appearance}/{name}.svg"], refined[f"{appearance}/{name}.svg"])
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "legacy"
            icons.build_icons(self.legacy_document, output, version="0.1.0")
            before = tree_snapshot(output)
            icons.build_icons(self.legacy_document, output, version="0.1.0", check=True)
            with self.assertRaisesRegex(ValueError, "differs"):
                icons.build_icons(self.document, output, check=True)
            self.assertEqual(tree_snapshot(output), before)
        for unsupported in ("0.0.0", "0.19.0", None, [], {}):
            with self.subTest(version=unsupported), self.assertRaisesRegex(ValueError, "Unsupported"):
                icons.render_icons(self.document, version=unsupported)

    def test_named_catalog_has_explicit_unique_assignments_and_accessible_labels(self):
        files = icons.render_icons(self.document)
        manifest = json.loads(files["manifest.json"])
        catalog = manifest["catalog"]
        self.assertEqual([row["id"] for row in catalog], NAMES)
        self.assertEqual([row["kind"] for row in catalog], ["function"] * 24 + ["app"] * 257)
        apps = catalog[24:]
        self.assertEqual(len({row["android_package"] for row in apps}), 257)
        self.assertEqual({row["id"]: (row["label"], row["android_package"]) for row in apps}, EXPECTED_APPS)
        for row in apps:
            prefix = ("https://galaxystore.samsung.com/detail/" if row["id"] in
                      {"gaming-hub", "theme-park", "samsung-pass", "tips"} else
                      "https://play.google.com/store/apps/details?id=")
            self.assertEqual(row["store_url"], prefix + row["android_package"])
            for appearance in ("Clair", "Obscur"):
                svg = ET.fromstring(files[f'{appearance}/{row["id"]}.svg'])
                self.assertEqual(svg.get("aria-label"), row["label"])
        self.assertIn("no popularity", manifest["catalog_scope"].lower())
        self.assertEqual(manifest["catalog_date"], "2026-10-21")

    def test_bad_named_catalog_fails_before_output_without_changing_existing_state(self):
        changes = (
            {"id": "../unsafe"}, {"id": "phone"}, {"label": " "},
            {"android_package": "not-a-package"},
            {"android_package": "com.google.android.youtube"},
            {"store_url": "https://example.com/store/apps/details?id=com.android.chrome"},
            {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"},
        )
        for change in changes:
            catalog = copy.deepcopy(icons.APP_CATALOG)
            catalog[0].update(change)
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "never-created"
                with patch.object(icons, "APP_CATALOG", catalog), self.assertRaises(ValueError):
                    icons.build_icons(self.document, output)
                self.assertFalse(output.exists())
                self.assertEqual(list(Path(temporary).iterdir()), [])

    def test_new_catalog_refusals_do_not_change_the_accepted_first_collection(self):
        previous = icons.render_icons(self.legacy_document, version="0.3.0")
        for change in ({"id": "youtube"}, {"android_package": "com.android.chrome"},
                       {"label": " "}, {"store_title": ""},
                       {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"}):
            invalid = copy.deepcopy(icons.NEW_APP_CATALOG)
            invalid[0].update(change)
            with self.subTest(change=change), patch.object(icons, "NEW_APP_CATALOG", invalid):
                self.assertEqual(icons.render_icons(self.legacy_document, version="0.3.0"), previous)
                with tempfile.TemporaryDirectory() as temporary:
                    output = Path(temporary) / "never-created"
                    with self.assertRaises(ValueError):
                        icons.build_icons(self.document, output)
                    self.assertFalse(output.exists())

    def test_third_catalog_refusals_preserve_both_accepted_named_collections(self):
        previous = {version: icons.render_icons(self.legacy_document, version=version)
                    for version in ("0.3.0", "0.4.0")}
        changes = ({"id": "x"}, {"android_package": "com.android.chrome"},
                   {"label": " "}, {"store_title": ""}, {"category": ""},
                   {"selection_basis": ""},
                   {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"})
        for change in changes:
            invalid = copy.deepcopy(icons.THIRD_APP_CATALOG)
            invalid[0].update(change)
            with self.subTest(change=change), patch.object(icons, "THIRD_APP_CATALOG", invalid):
                for version, files in previous.items():
                    self.assertEqual(icons.render_icons(self.legacy_document, version=version), files)
                with tempfile.TemporaryDirectory() as temporary:
                    output = Path(temporary) / "never-created"
                    with self.assertRaises(ValueError):
                        icons.build_icons(self.document, output)
                    self.assertFalse(output.exists())
        for fault in ("missing", "accepted-ID"):
            drawings = dict(icons.THIRD_APP_GLYPHS)
            if fault == "missing":
                drawings.pop("linkedin")
            else:
                drawings["x"] = drawings["linkedin"]
            with self.subTest(drawings=fault), patch.object(icons, "THIRD_APP_GLYPHS", drawings):
                self.assertEqual(icons.render_icons(self.legacy_document, version="0.4.0"), previous["0.4.0"])
                with tempfile.TemporaryDirectory() as temporary:
                    output = Path(temporary) / "never-created"
                    with self.assertRaises(ValueError):
                        icons.build_icons(self.document, output)
                    self.assertFalse(output.exists())

    def test_fourth_catalog_and_glyph_refusals_preserve_all_prior_named_collections(self):
        previous = {version: icons.render_icons(icons.load_icon_tokens(version), version=version)
                    for version in ("0.3.0", "0.4.0", "0.5.0", "0.6.0")}
        changes = ({"id": "linkedin"}, {"id": "phone"},
                   {"android_package": "com.garmin.android.apps.connectmobile"},
                   {"label": " "}, {"store_title": ""}, {"category": ""},
                   {"selection_basis": ""},
                   {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"})
        def refuse_without_rewriting_history():
            for version, files in previous.items():
                self.assertEqual(icons.render_icons(icons.load_icon_tokens(version), version=version), files)
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "never-created"
                with self.assertRaises(ValueError):
                    icons.build_icons(self.document, output)
                self.assertFalse(output.exists())
        for change in changes:
            invalid = copy.deepcopy(icons.FOURTH_APP_CATALOG)
            invalid[0].update(change)
            with self.subTest(change=change), patch.object(icons, "FOURTH_APP_CATALOG", invalid):
                refuse_without_rewriting_history()
        for fault in ("missing", "accepted-ID"):
            drawings = dict(icons.FOURTH_APP_GLYPHS)
            if fault == "missing":
                drawings.pop("good-lock")
            else:
                drawings["linkedin"] = drawings["good-lock"]
            with self.subTest(drawings=fault), patch.object(icons, "FOURTH_APP_GLYPHS", drawings):
                refuse_without_rewriting_history()

    def test_companion_store_titles_remain_distinct_from_short_assignment_labels(self):
        rows = {row["id"]: row for row in icons.icon_catalog()}
        expected = {"good-lock": "Good Lock", "connect-iq-store": "Connect IQ\u2122 Store",
                    "steam": "Steam", "reuters": "Reuters - Breaking World News",
                    "home-depot": "The Home Depot", "patreon": "Patreon"}
        self.assertEqual({name: rows[name]["store_title"] for name in FOURTH_APP_NAMES}, expected)

    def test_fifth_catalog_and_glyph_refusals_preserve_all_prior_named_collections(self):
        previous = {version: icons.render_icons(icons.load_icon_tokens(version), version=version)
                    for version in ("0.3.0", "0.4.0", "0.5.0", "0.6.0", "0.7.0")}
        changes = ({"id": "good-lock"}, {"id": "phone"}, {"id": "../unsafe"},
                   {"android_package": "com.garmin.connectiq"}, {"android_package": "bad-package"},
                   {"label": " "}, {"store_title": ""}, {"category": ""}, {"kind": "function"},
                   {"selection_basis": ""},
                   {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"})
        def refuse_without_rewriting_history():
            for version, files in previous.items():
                self.assertEqual(icons.render_icons(icons.load_icon_tokens(version), version=version), files)
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "never-created"
                with self.assertRaises(ValueError):
                    icons.build_icons(self.document, output)
                self.assertFalse(output.exists())
        for change in changes:
            invalid = copy.deepcopy(icons.FIFTH_APP_CATALOG)
            invalid[0].update(change)
            with self.subTest(change=change), patch.object(icons, "FIFTH_APP_CATALOG", invalid):
                refuse_without_rewriting_history()
        for fault in ("missing", "accepted-ID"):
            drawings = dict(icons.FIFTH_APP_GLYPHS)
            if fault == "missing":
                drawings.pop("youtube-music")
            else:
                drawings["good-lock"] = drawings["youtube-music"]
            with self.subTest(drawings=fault), patch.object(icons, "FIFTH_APP_GLYPHS", drawings):
                refuse_without_rewriting_history()

    def test_broad_app_titles_match_inspected_listings_without_relabeling_localized_titles(self):
        rows = {row["id"]: row for row in icons.icon_catalog()}
        expected = {'youtube-music': 'YouTube Music',
         'audible': 'Audible: Audiobooks & Podcasts',
         'amazon-kindle': 'Amazon Kindle: Reading App',
         'pocket-casts': 'Pocket Casts - Podcast App',
         'vlc': 'VLC for Android',
         'shazam': 'Shazam: Find Music & Concerts',
         'soundcloud': 'SoundCloud: Discover Music',
         'hulu': 'Hulu: Stream TV shows & movies',
         'target': 'Target: Shop. Style. Save.',
         'costco': 'Costco Wholesale',
         'best-buy': 'Best Buy: Shop tech deals',
         'etsy': 'Etsy: Shop from Real People',
         'aliexpress': 'AliExpress : shopping en ligne',
         'shein': 'SHEIN-Shopping Online',
         'instacart': 'Instacart: Get Food Delivery',
         'airbnb': 'Airbnb',
         'booking': 'Booking.com: Hotels & Travel',
         'expedia': 'Expedia: Hotels, Flights, Cars',
         'lyft': 'Lyft',
         'uber-eats': 'Uber Eats: Food and Grocery',
         'google-earth': 'Google Earth',
         'google-news': 'Google News - Daily Headlines',
         'galaxy-wearable': 'Galaxy Wearable',
         'files-by-google': 'Files by Google',
         'adobe-acrobat': 'Adobe Acrobat Reader: Edit PDF',
         'microsoft-word': 'Microsoft Word: Edit Documents',
         'microsoft-excel': 'Microsoft Excel: Spreadsheets',
         'microsoft-powerpoint': 'Microsoft PowerPoint',
         'google-slides': 'Google Slides',
         'google-lens': 'Google Lens',
         'roblox': 'Roblox',
         'minecraft': 'Minecraft: Dream it, Build it!'}
        self.assertEqual({name: rows[name]["store_title"] for name in FIFTH_APP_NAMES}, expected)
        self.assertEqual(rows["aliexpress"]["label"], "AliExpress")
        self.assertEqual(rows["aliexpress"]["store_title"], "AliExpress : shopping en ligne")

    def test_sixth_catalog_and_glyph_refusals_preserve_all_eight_earlier_versions(self):
        versions = ("0.1.0", "0.2.0", "0.3.0", "0.4.0", "0.5.0", "0.6.0", "0.7.0", "0.8.0")
        previous = {version: icons.render_icons(icons.load_icon_tokens(version), version=version)
                    for version in versions}
        changes = ({"id": "youtube-music"}, {"id": "phone"}, {"id": "../unsafe"},
                   {"android_package": "com.google.android.apps.youtube.music"},
                   {"android_package": "bad-package"}, {"label": " "}, {"store_title": ""},
                   {"category": ""}, {"kind": "function"}, {"selection_basis": ""},
                   {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"})

        def refuse_without_rewriting_history():
            for version, files in previous.items():
                self.assertEqual(icons.render_icons(icons.load_icon_tokens(version), version=version), files)
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "never-created"
                with self.assertRaises(ValueError):
                    icons.build_icons(self.document, output)
                self.assertFalse(output.exists())
                self.assertEqual(list(Path(temporary).iterdir()), [])

        for change in changes:
            invalid = copy.deepcopy(icons.SIXTH_APP_CATALOG)
            invalid[0].update(change)
            with self.subTest(change=change), patch.object(icons, "SIXTH_APP_CATALOG", invalid):
                refuse_without_rewriting_history()
        for fault in ("missing", "accepted-ID"):
            drawings = dict(icons.SIXTH_APP_GLYPHS)
            if fault == "missing":
                drawings.pop("slack")
            else:
                drawings["youtube-music"] = drawings["slack"]
            with self.subTest(drawings=fault), patch.object(icons, "SIXTH_APP_GLYPHS", drawings):
                refuse_without_rewriting_history()

    def test_everyday_identity_rows_match_the_independently_inspected_literals(self):
        catalog = icons.icon_catalog()
        self.assertEqual([row["id"] for row in SIXTH_EXPECTED_APPS], SIXTH_APP_NAMES)
        self.assertEqual(catalog[127:175], list(SIXTH_EXPECTED_APPS))

    def test_food_collection_preserves_the_exact_accepted_0_9_archive_and_all_svg_bytes(self):
        from themeforge.build import _zip_bytes
        from themeforge.legal import license_text
        previous = icons.render_icons(self.document, version="0.9.0")
        archive = {**previous, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(archive)).hexdigest(),
                         "994ce1d819414b06062d5cd32a03eeb8891e9074b09491dfb2c774a55ae5a3b1")
        current = icons.render_icons(self.document, version="0.10.0")
        manifest = json.loads(current["manifest.json"])
        self.assertEqual(manifest["functions"][:175], SIXTH_NAMES)
        self.assertEqual([row["id"] for row in manifest["catalog"][-12:]], SEVENTH_APP_NAMES)
        self.assertEqual(manifest["catalog"][:175], json.loads(previous["manifest.json"])["catalog"])
        for name, payload in previous.items():
            if name.endswith(".svg"):
                self.assertEqual(current[name], payload, name)
        rows = {row["id"]: row for row in manifest["catalog"][-12:]}
        self.assertEqual(rows["kfc-us"]["store_title"], "KFC US: Ordering & Delivery")
        self.assertEqual(rows["kfc-us"]["store_url"],
                         "https://play.google.com/store/apps/details?id=com.kfc.us.mobile")
        self.assertNotIn("com.kfc.mobile", {row["android_package"] for row in rows.values()})

    def test_food_catalog_faults_refuse_output_and_preserve_the_accepted_0_9_tree(self):
        previous = icons.render_icons(self.document, version="0.9.0")
        for change in ({"id": "phone"}, {"android_package": "com.mcdonalds.app"},
                       {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"}):
            bad = copy.deepcopy(icons.SEVENTH_APP_CATALOG)
            bad[0].update(change)
            with self.subTest(change=change), patch.object(icons, "SEVENTH_APP_CATALOG", bad):
                self.assertEqual(icons.render_icons(self.document, version="0.9.0"), previous)
                with tempfile.TemporaryDirectory() as temporary:
                    output = Path(temporary) / "never-created"
                    with self.assertRaises(ValueError):
                        icons.build_icons(self.document, output, version="0.10.0")
                    self.assertFalse(output.exists())
        for fault in ("missing", "accepted-ID"):
            bad = dict(icons.SEVENTH_APP_GLYPHS)
            if fault == "missing":
                bad.pop("chipotle")
            else:
                bad["phone"] = bad["chipotle"]
            with self.subTest(drawings=fault), patch.object(icons, "SEVENTH_APP_GLYPHS", bad):
                self.assertEqual(icons.render_icons(self.document, version="0.9.0"), previous)
                with tempfile.TemporaryDirectory() as temporary:
                    output = Path(temporary) / "never-created"
                    with self.assertRaises(ValueError):
                        icons.build_icons(self.document, output, version="0.10.0")
                    self.assertFalse(output.exists())

    def test_travel_collection_preserves_the_exact_accepted_0_10_archive_and_all_svg_bytes(self):
        from themeforge.build import _zip_bytes
        from themeforge.legal import license_text
        previous = icons.render_icons(self.document, version="0.10.0")
        archive = {**previous, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(archive)).hexdigest(),
                         "a81ffb8c4fb3ef32f3c8391c53016e99246b755ce9079fdee84b5948790ab8e0")
        previous_manifest = json.loads(previous["manifest.json"])
        self.assertEqual(previous_manifest["version"], "0.10.0")
        self.assertEqual(previous_manifest["catalog_date"], "2026-10-19")
        self.assertEqual(previous_manifest["functions"], SEVENTH_NAMES)
        self.assertEqual(len(previous_manifest["files"]), 374)
        current = icons.render_icons(self.document, version="0.11.0")
        manifest = json.loads(current["manifest.json"])
        self.assertEqual(manifest["catalog"][:187], previous_manifest["catalog"])
        self.assertEqual(manifest["functions"][:187], SEVENTH_NAMES)
        self.assertEqual([row["id"] for row in manifest["catalog"][-10:]], EIGHTH_APP_NAMES)
        self.assertEqual([(row["id"], row["label"], row["android_package"])
                          for row in manifest["catalog"][-10:]], list(EIGHTH_EXPECTED_APPS))
        for name, payload in previous.items():
            if name.endswith(".svg"):
                self.assertEqual(current[name], payload, name)

    def test_travel_catalog_faults_refuse_output_and_preserve_the_accepted_0_10_tree(self):
        previous = icons.render_icons(self.document, version="0.10.0")

        def refuse_without_rewriting_history():
            self.assertEqual(icons.render_icons(self.document, version="0.10.0"), previous)
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "never-created"
                with self.assertRaises(ValueError):
                    icons.build_icons(self.document, output)
                self.assertFalse(output.exists())

        for change in ({"id": "phone"}, {"id": "united-airlines"},
                       {"android_package": "com.mcdonalds.app"},
                       {"android_package": "com.united.mobile.android"},
                       {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"}):
            bad = copy.deepcopy(icons.EIGHTH_APP_CATALOG)
            bad[0].update(change)
            with self.subTest(change=change), patch.object(icons, "EIGHTH_APP_CATALOG", bad):
                refuse_without_rewriting_history()
        for fault in ("missing", "accepted-ID"):
            bad = dict(icons.EIGHTH_APP_GLYPHS)
            if fault == "missing":
                bad.pop("fly-delta")
            else:
                bad["phone"] = bad["fly-delta"]
            with self.subTest(drawings=fault), patch.object(icons, "EIGHTH_APP_GLYPHS", bad):
                refuse_without_rewriting_history()

    def test_finance_collection_preserves_exact_accepted_0_11_archive_and_all_svg_bytes(self):
        from themeforge.build import _zip_bytes
        from themeforge.legal import license_text
        previous = icons.render_icons(self.document, version="0.11.0")
        self.assertEqual(hashlib.sha256(_zip_bytes({**previous, "LICENSE.txt": license_text().encode("utf-8")})).hexdigest(),
                         "04cce2b812ad4f6ed7bcfda172a9bfe5a6d63d058b6899570a1dbe94f162884d")
        previous_manifest = json.loads(previous["manifest.json"])
        self.assertEqual(previous_manifest["version"], "0.11.0")
        self.assertEqual(previous_manifest["catalog_date"], "2026-10-20")
        self.assertEqual(previous_manifest["functions"], EIGHTH_NAMES)
        self.assertEqual(len(previous_manifest["files"]), 394)
        current = icons.render_icons(self.document, version="0.12.0")
        manifest = json.loads(current["manifest.json"])
        self.assertEqual(manifest["catalog"][:197], previous_manifest["catalog"])
        self.assertEqual(manifest["functions"][:197], EIGHTH_NAMES)
        self.assertEqual([row["id"] for row in manifest["catalog"][-10:]], NINTH_APP_NAMES)
        self.assertEqual([(row["id"], row["label"], row["android_package"])
                          for row in manifest["catalog"][-10:]], list(NINTH_EXPECTED_APPS))
        for name, payload in previous.items():
            if name.endswith(".svg"):
                self.assertEqual(current[name], payload, name)
        assignments = {row["id"]: row["android_package"] for row in manifest["catalog"] if row["kind"] == "app"}
        self.assertEqual(assignments["discover"], "com.discoverfinancial.mobile")
        self.assertEqual(assignments["capital-one"], "com.konylabs.capitalone")
        self.assertNotEqual(assignments["discover"], assignments["capital-one"])

    def test_finance_catalog_faults_refuse_output_and_preserve_accepted_0_11_tree(self):
        previous = icons.render_icons(self.document, version="0.11.0")
        def refuse_without_rewriting_history():
            self.assertEqual(icons.render_icons(self.document, version="0.11.0"), previous)
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "never-created"
                with self.assertRaises(ValueError):
                    icons.build_icons(self.document, output, version="0.12.0")
                self.assertFalse(output.exists())
        for change in ({"id": "phone"}, {"id": "wells-fargo"},
                       {"android_package": "com.konylabs.capitalone"},
                       {"android_package": "com.wf.wellsfargomobile"},
                       {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"}):
            bad = copy.deepcopy(icons.NINTH_APP_CATALOG)
            bad[0].update(change)
            with self.subTest(change=change), patch.object(icons, "NINTH_APP_CATALOG", bad):
                refuse_without_rewriting_history()
        for fault in ("missing", "accepted-ID", "extra"):
            bad = dict(icons.NINTH_APP_GLYPHS)
            if fault == "missing":
                bad.pop("bank-of-america")
            else:
                bad["phone" if fault == "accepted-ID" else "unassigned-new-app"] = bad["bank-of-america"]
            with self.subTest(drawings=fault), patch.object(icons, "NINTH_APP_GLYPHS", bad):
                refuse_without_rewriting_history()

    def test_weather_collection_preserves_exact_accepted_0_12_archive_catalog_and_all_svg_bytes(self):
        from themeforge.build import _zip_bytes
        from themeforge.legal import license_text
        previous = icons.render_icons(self.document, version="0.12.0")
        archive = {**previous, "LICENSE.txt": license_text().encode("utf-8")}
        self.assertEqual(hashlib.sha256(_zip_bytes(archive)).hexdigest(),
                         "db8ed7e2c62d36786b2c2d510fdf68f83649fda512f6bb018f5043491cb8f0cf")
        previous_manifest = json.loads(previous["manifest.json"])
        self.assertEqual(previous_manifest["version"], "0.12.0")
        self.assertEqual(previous_manifest["functions"], NINTH_NAMES)
        self.assertEqual(len(previous_manifest["catalog"]), 207)
        self.assertEqual(len(previous_manifest["files"]), 414)
        self.assertEqual(sum(name.endswith(".svg") for name in previous), 414)

        current = icons.render_icons(self.document, version="0.13.0")
        manifest = json.loads(current["manifest.json"])
        self.assertEqual(manifest["version"], "0.13.0")
        self.assertEqual(len(manifest["catalog"]), 217)
        self.assertEqual(len(manifest["files"]), 434)
        self.assertEqual(manifest["catalog"][:207], previous_manifest["catalog"])
        self.assertEqual(manifest["functions"][:207], NINTH_NAMES)
        self.assertEqual([row["id"] for row in manifest["catalog"][-10:]], TENTH_APP_NAMES)
        self.assertEqual([(row["id"], row["label"], row["android_package"])
                          for row in manifest["catalog"][-10:]], list(TENTH_EXPECTED_APPS))
        for name, payload in previous.items():
            if name.endswith(".svg"):
                self.assertEqual(current[name], payload, name)
        rows = {row["id"]: row for row in manifest["catalog"][-10:]}
        self.assertEqual(rows["weather-underground"]["store_title"], "Weather data & microclimate :")
        self.assertEqual(rows["rainviewer"]["store_url"],
                         "https://play.google.com/store/apps/details?id=com.lucky_apps.RainViewer")
        self.assertTrue(all(row["category"] == "weather" for row in rows.values()))

    def test_weather_catalog_faults_refuse_output_and_preserve_accepted_0_12_tree(self):
        previous = icons.render_icons(self.document, version="0.12.0")

        def refuse_without_rewriting_history():
            self.assertEqual(icons.render_icons(self.document, version="0.12.0"), previous)
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "never-created"
                with self.assertRaises(ValueError):
                    icons.build_icons(self.document, output, version="0.13.0")
                self.assertFalse(output.exists())
                self.assertEqual(list(Path(temporary).iterdir()), [])

        for change in ({"id": "phone"}, {"id": "weather-channel"},
                       {"android_package": "com.discoverfinancial.mobile"},
                       {"android_package": "com.weather.Weather"},
                       {"label": " "}, {"store_title": ""},
                       {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"}):
            bad = copy.deepcopy(icons.TENTH_APP_CATALOG)
            bad[0].update(change)
            with self.subTest(change=change), patch.object(icons, "TENTH_APP_CATALOG", bad):
                refuse_without_rewriting_history()
        for fault in ("missing", "accepted-ID", "extra"):
            bad = dict(icons.TENTH_APP_GLYPHS)
            if fault == "missing":
                bad.pop("accuweather")
            else:
                bad["phone" if fault == "accepted-ID" else "unassigned-new-app"] = bad["accuweather"]
            with self.subTest(drawings=fault), patch.object(icons, "TENTH_APP_GLYPHS", bad):
                refuse_without_rewriting_history()

    def test_running_training_preserves_exact_weather_archive_catalog_and_all_434_svg_bytes(self):
        from themeforge.build import _zip_bytes
        from themeforge.legal import license_text
        previous = icons.render_icons(self.document, version="0.13.0")
        previous_manifest = json.loads(previous["manifest.json"])
        self.assertEqual(hashlib.sha256(_zip_bytes({**previous, "LICENSE.txt": license_text().encode("utf-8")})).hexdigest(),
                         "e6f7c532d0c625666a0f3403ee27842ac8612e6368d49f64fb3e84b667a42ca1")
        self.assertEqual(hashlib.sha256(previous["manifest.json"]).hexdigest(),
                         "cc573fb8f3996d05eff6d8e724c179f17001ffcfaff26bbfade76e52591ce723")
        self.assertEqual(previous_manifest["functions"], TENTH_NAMES)
        self.assertEqual(len(previous_manifest["files"]), 434)
        current = icons.render_icons(self.document, version="0.14.0")
        manifest = json.loads(current["manifest.json"])
        self.assertEqual(manifest["version"], "0.14.0")
        self.assertEqual(len(manifest["catalog"]), 225)
        self.assertEqual(len(manifest["files"]), 450)
        self.assertEqual(manifest["catalog"][:217], previous_manifest["catalog"])
        self.assertEqual(manifest["functions"][:217], TENTH_NAMES)
        self.assertEqual([(row["id"], row["label"], row["android_package"])
                          for row in manifest["catalog"][-8:]], list(ELEVENTH_EXPECTED_APPS))
        for name, payload in previous.items():
            if name.endswith(".svg"):
                self.assertEqual(current[name], payload, name)
        rows = {row["id"]: row for row in manifest["catalog"][-8:]}
        self.assertEqual({identifier: row["store_title"] for identifier, row in rows.items()}, {
            "nike-run-club": "Nike Run Club - Running Coach",
            "adidas-running": "adidas Running: Run tracker",
            "asics-runkeeper": "ASICS Runkeeper: Fitness App",
            "map-my-run": "Map My Run GPS Running Tracker",
            "runna": "Runna: Running Plans & Coach",
            "trainingpeaks": "TrainingPeaks: Plan Train Lift",
            "zwift-companion": "Zwift Companion",
            "relive": "Relive: Run, Ride, Hike & more",
        })
        self.assertTrue(all(row["category"] == "fitness" for row in rows.values()))
        self.assertEqual(rows["asics-runkeeper"]["android_package"], "com.fitnesskeeper.runkeeper.pro")
        self.assertEqual(rows["zwift-companion"]["store_url"],
                         "https://play.google.com/store/apps/details?id=com.zwift.android.prod")
        self.assertNotEqual(rows["runna"]["android_package"],
                            next(row for row in manifest["catalog"] if row["id"] == "strava")["android_package"])

    def test_running_training_faults_refuse_output_and_preserve_accepted_weather_tree(self):
        previous = icons.render_icons(self.document, version="0.13.0")
        def refuse_without_rewriting_history():
            self.assertEqual(icons.render_icons(self.document, version="0.13.0"), previous)
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "never-created"
                with self.assertRaises(ValueError):
                    icons.build_icons(self.document, output, version="0.14.0")
                self.assertFalse(output.exists())
                self.assertEqual(list(Path(temporary).iterdir()), [])
        for change in ({"id": "phone"}, {"id": "adidas-running"},
                       {"android_package": "com.strava"}, {"android_package": "com.runbuddy.prod"},
                       {"label": " "}, {"store_title": ""},
                       {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"}):
            bad = copy.deepcopy(icons.ELEVENTH_APP_CATALOG)
            bad[0].update(change)
            with self.subTest(change=change), patch.object(icons, "ELEVENTH_APP_CATALOG", bad):
                refuse_without_rewriting_history()
        for fault in ("missing", "accepted-ID", "extra"):
            bad = dict(icons.ELEVENTH_APP_GLYPHS)
            if fault == "missing":
                bad.pop("nike-run-club")
            else:
                bad["phone" if fault == "accepted-ID" else "unassigned-new-app"] = bad["nike-run-club"]
            with self.subTest(drawings=fault), patch.object(icons, "ELEVENTH_APP_GLYPHS", bad):
                refuse_without_rewriting_history()

    def test_learning_preserves_exact_running_archive_catalog_and_all_450_svg_bytes(self):
        from themeforge.build import _zip_bytes
        from themeforge.legal import license_text
        previous = icons.render_icons(self.document, version="0.14.0")
        previous_manifest = json.loads(previous["manifest.json"])
        self.assertEqual(hashlib.sha256(_zip_bytes({**previous, "LICENSE.txt": license_text().encode("utf-8")})).hexdigest(),
                         "4b3324d30b0b6e94a52e0d51a206e499e6e2b6be82052752963da9446c44e6c1")
        self.assertEqual(hashlib.sha256(previous["manifest.json"]).hexdigest(),
                         "4ac31c55d2723a0e27ee4892eb29d59dbdcb179443f496fced7b69337c0699df")
        self.assertEqual(previous_manifest["functions"], ELEVENTH_NAMES)
        self.assertEqual(len(previous_manifest["files"]), 450)
        current = icons.render_icons(self.document, version="0.15.0")
        manifest = json.loads(current["manifest.json"])
        self.assertEqual(manifest["version"], "0.15.0")
        self.assertEqual(len(manifest["catalog"]), 233)
        self.assertEqual(len(manifest["files"]), 466)
        self.assertEqual(manifest["catalog"][:225], previous_manifest["catalog"])
        self.assertEqual(manifest["functions"][:225], ELEVENTH_NAMES)
        self.assertEqual([(row["id"], row["label"], row["android_package"])
                          for row in manifest["catalog"][-8:]], list(TWELFTH_EXPECTED_APPS))
        for name, payload in previous.items():
            if name.endswith(".svg"):
                self.assertEqual(current[name], payload, name)
        rows = {row["id"]: row for row in manifest["catalog"][-8:]}
        self.assertEqual({identifier: row["store_title"] for identifier, row in rows.items()}, {
            "google-classroom": "Google Classroom", "khan-academy": "Khan Academy",
            "coursera": "Coursera: Grow your career", "udemy": "Udemy - Online Courses",
            "edx": "edX online learning", "quizlet": "Quizlet: More than Flashcards",
            "photomath": "Photomath", "brainly": "Brainly: AI Homework Helper",
        })
        self.assertEqual(manifest["catalog_date"], "2026-10-21")
        self.assertTrue(all(row["category"] == "education" for row in rows.values()))

    def test_learning_faults_refuse_output_and_preserve_accepted_running_tree(self):
        previous = icons.render_icons(self.document, version="0.14.0")
        def refuse_without_rewriting_history():
            self.assertEqual(icons.render_icons(self.document, version="0.14.0"), previous)
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "never-created"
                with self.assertRaises(ValueError):
                    icons.build_icons(self.document, output)
                self.assertFalse(output.exists())
                self.assertEqual(list(Path(temporary).iterdir()), [])
        for change in ({"id": "phone"}, {"id": "khan-academy"},
                       {"android_package": "com.strava"}, {"android_package": "co.brainly"},
                       {"label": " "}, {"store_title": ""},
                       {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"}):
            bad = copy.deepcopy(icons.TWELFTH_APP_CATALOG)
            bad[0].update(change)
            with self.subTest(change=change), patch.object(icons, "TWELFTH_APP_CATALOG", bad):
                refuse_without_rewriting_history()
        for fault in ("missing", "accepted-ID", "extra"):
            bad = dict(icons.TWELFTH_APP_GLYPHS)
            if fault == "missing":
                bad.pop("google-classroom")
            else:
                bad["phone" if fault == "accepted-ID" else "unassigned-new-app"] = bad["google-classroom"]
            with self.subTest(drawings=fault), patch.object(icons, "TWELFTH_APP_GLYPHS", bad):
                refuse_without_rewriting_history()

    def test_reading_preserves_exact_learning_archive_catalog_and_all_466_svg_bytes(self):
        from themeforge.build import _zip_bytes
        from themeforge.legal import license_text
        previous = icons.render_icons(self.document, version="0.15.0")
        previous_manifest = json.loads(previous["manifest.json"])
        self.assertEqual(hashlib.sha256(_zip_bytes({**previous, "LICENSE.txt": license_text().encode("utf-8")})).hexdigest(),
                         "df05503c0f1825d09e5b5fb96fcb87401490fef601518ca4e526a6e6d564197c")
        self.assertEqual(hashlib.sha256(previous["manifest.json"]).hexdigest(),
                         "3979cc7eaf90a5cf8aab82bd711fc8d2ff92388856cbb41b9321442693b88b2b")
        self.assertEqual(previous_manifest["functions"], TWELFTH_NAMES)
        self.assertEqual(len(previous_manifest["files"]), 466)
        current = icons.render_icons(self.document, version="0.16.0")
        manifest = json.loads(current["manifest.json"])
        self.assertEqual(manifest["version"], "0.16.0")
        self.assertEqual(len(manifest["catalog"]), 241)
        self.assertEqual(len(manifest["files"]), 482)
        self.assertEqual(manifest["catalog"][:233], previous_manifest["catalog"])
        self.assertEqual(manifest["functions"][:233], TWELFTH_NAMES)
        self.assertEqual([(row["id"], row["label"], row["android_package"])
                          for row in manifest["catalog"][-8:]], list(THIRTEENTH_EXPECTED_APPS))
        for name, payload in previous.items():
            if name.endswith(".svg"):
                self.assertEqual(current[name], payload, name)
        rows = {row["id"]: row for row in manifest["catalog"][-8:]}
        self.assertEqual({identifier: row["store_title"] for identifier, row in rows.items()}, {'google-play-books': 'Google Play Books & Audiobooks', 'libby': 'Libby: Read Library Books', 'kobo-books': 'Kobo | eBooks & Audiobooks', 'goodreads': 'Goodreads: Book Tracker & More', 'wattpad': 'Wattpad - Read & Write Stories', 'webtoon': 'WEBTOON: Manga, Comics, Manhwa', 'readera': 'ReadEra – book reader pdf epub', 'moon-reader': 'Moon+ Reader'})
        self.assertEqual(manifest["catalog_date"], "2026-10-21")
        self.assertTrue(all(row["category"] == "reading" for row in rows.values()))

    def test_reading_faults_refuse_output_and_preserve_accepted_learning_tree(self):
        previous = icons.render_icons(self.document, version="0.15.0")
        def refuse_without_rewriting_history():
            self.assertEqual(icons.render_icons(self.document, version="0.15.0"), previous)
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "never-created"
                with self.assertRaises(ValueError):
                    icons.build_icons(self.document, output)
                self.assertFalse(output.exists())
                self.assertEqual(list(Path(temporary).iterdir()), [])
        for change in ({"id": "phone"}, {"id": "libby"},
                       {"android_package": "com.amazon.kindle"}, {"android_package": "wp.wattpad"},
                       {"label": " "}, {"store_title": ""},
                       {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"}):
            bad = copy.deepcopy(icons.THIRTEENTH_APP_CATALOG)
            bad[0].update(change)
            with self.subTest(change=change), patch.object(icons, "THIRTEENTH_APP_CATALOG", bad):
                refuse_without_rewriting_history()
        for fault in ("missing", "accepted-ID", "extra"):
            bad = dict(icons.THIRTEENTH_APP_GLYPHS)
            if fault == "missing":
                bad.pop("google-play-books")
            else:
                bad["phone" if fault == "accepted-ID" else "unassigned-new-app"] = bad["google-play-books"]
            with self.subTest(drawings=fault), patch.object(icons, "THIRTEENTH_APP_GLYPHS", bad):
                refuse_without_rewriting_history()


    def test_phone_services_preserve_reading_archive_catalog_and_all_482_svg_bytes(self):
        from themeforge.build import _zip_bytes
        previous = icons.render_icons(self.document, version="0.16.0")
        previous_manifest = json.loads(previous["manifest.json"])
        self.assertEqual(hashlib.sha256(_zip_bytes({
            **previous, "LICENSE.txt": icons.license_text().encode("utf-8")
        })).hexdigest(), "3fbf8b53e12ddae6ea354d6ed20a1464c4874192a24f5dee7f231baed0e7f3a0")
        self.assertEqual(hashlib.sha256(previous["manifest.json"]).hexdigest(),
                         "edf610a33c55adeecca9c43bde0b0786a4f7d0b81c018880a504068218670b19")
        current = icons.render_icons(self.document, version="0.17.0")
        manifest = json.loads(current["manifest.json"])
        self.assertEqual(manifest["version"], "0.17.0")
        self.assertEqual(len(manifest["catalog"]), 281)
        self.assertEqual(len(manifest["files"]), 562)
        self.assertEqual(manifest["catalog"][:241], previous_manifest["catalog"])
        self.assertEqual(manifest["functions"][:241], THIRTEENTH_NAMES)
        self.assertEqual([(row["id"], row["label"], row["android_package"])
                          for row in manifest["catalog"][241:]], list(FOURTEENTH_EXPECTED_APPS))
        for name, payload in previous.items():
            if name.endswith(".svg"):
                self.assertEqual(current[name], payload, name)
        rows = {row["id"]: row for row in manifest["catalog"]}
        self.assertNotEqual(rows["steam-chat"]["android_package"], rows["steam"]["android_package"])
        self.assertNotEqual(rows["zillow-rentals"]["android_package"], rows["zillow"]["android_package"])
        self.assertNotEqual(rows["credit-one"]["android_package"], rows["capital-one"]["android_package"])
        self.assertNotEqual(rows["usaa"]["android_package"], rows["us-bank"]["android_package"])
        self.assertEqual(rows["ap-news"]["android_package"], "mnn.Android")
        self.assertEqual(rows["fandom"]["android_package"], "com.fandom.app")
        self.assertEqual(rows["shop"]["android_package"], "com.shopify.arrive")
        self.assertTrue({"interpreter", "learning", "visual-voicemail"}.isdisjoint(rows))

    def test_phone_service_faults_refuse_output_and_preserve_reading_tree(self):
        previous = icons.render_icons(self.document, version="0.16.0")
        def refuse_without_rewriting_history():
            self.assertEqual(icons.render_icons(self.document, version="0.16.0"), previous)
            with tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "never-created"
                with self.assertRaises(ValueError):
                    icons.build_icons(self.document, output)
                self.assertFalse(output.exists())
                self.assertEqual(list(Path(temporary).iterdir()), [])
        for change in ({"id": "phone"}, {"id": "libby"}, {"id": "../unsafe"},
                       {"android_package": "wp.wattpad"}, {"android_package": "not-a-package"},
                       {"label": " "}, {"store_title": ""}, {"selection_basis": ""},
                       {"store_url": "https://play.google.com/store/apps/details?id=com.wrong.app"}):
            bad = copy.deepcopy(icons.FOURTEENTH_APP_CATALOG)
            bad[0].update(change)
            with self.subTest(change=change), patch.object(icons, "FOURTEENTH_APP_CATALOG", bad):
                refuse_without_rewriting_history()
        for fault in ("missing", "accepted-ID", "extra"):
            bad = dict(icons.FOURTEENTH_APP_GLYPHS)
            if fault == "missing":
                bad.pop("ace-hardware")
            else:
                bad["phone" if fault == "accepted-ID" else "unassigned-new-app"] = bad["ace-hardware"]
            with self.subTest(drawings=fault), patch.object(icons, "FOURTEENTH_APP_GLYPHS", bad):
                refuse_without_rewriting_history()

    def test_galaxy_store_admission_is_exact_and_current_only(self):
        packages = {
            "gaming-hub": "com.samsung.android.game.gamehome",
            "theme-park": "com.samsung.android.themedesigner",
            "samsung-pass": "com.samsung.android.samsungpass",
            "tips": "com.samsung.android.app.tips",
        }
        catalog = {row["id"]: row for row in icons.icon_catalog()}
        for identifier, package in packages.items():
            url = "https://galaxystore.samsung.com/detail/" + package
            self.assertEqual(catalog[identifier]["store_url"], url)
            faults = (
                url.replace("https:", "http:"), url.replace("galaxystore.samsung.com", "example.com"),
                url.replace("galaxystore.samsung.com", "galaxystore.samsung.com.example.com"),
                url.replace("galaxystore.samsung.com", "galaxystore.samsung.com:443"),
                url.replace("galaxystore.samsung.com", "user@galaxystore.samsung.com"),
                url.replace("/detail/", "/weardetail/"), url + "/", url + "?langCd=en",
                url + "?id=" + package, url + "#details", url.replace(package, "com.wrong.app"),
                url.replace(package, package.replace(".", "%2E")),
            )
            for bad_url in faults:
                bad = copy.deepcopy(icons.FOURTEENTH_APP_CATALOG)
                next(row for row in bad if row["id"] == identifier)["store_url"] = bad_url
                with self.subTest(identifier=identifier, url=bad_url):
                    with patch.object(icons, "FOURTEENTH_APP_CATALOG", bad):
                        with self.assertRaises(ValueError):
                            icons.icon_catalog()
        bad = copy.deepcopy(icons.FOURTEENTH_APP_CATALOG)
        bad[0]["store_url"] = "https://galaxystore.samsung.com/detail/" + bad[0]["android_package"]
        with patch.object(icons, "FOURTEENTH_APP_CATALOG", bad), self.assertRaises(ValueError):
            icons.icon_catalog()
        # A new-store identity cannot be smuggled into any historical catalog.
        old = copy.deepcopy(icons.THIRTEENTH_APP_CATALOG)
        old[0].update(android_package=packages["theme-park"],
                      store_url="https://galaxystore.samsung.com/detail/" + packages["theme-park"])
        with patch.object(icons, "THIRTEENTH_APP_CATALOG", old), self.assertRaises(ValueError):
            icons.icon_catalog("0.16.0")


    def test_current_bubble_has_one_continuous_outline_and_calculator_has_open_equals(self):
        files = icons.render_icons(self.document)
        bubble = ET.fromstring(files["Obscur/messages.svg"]).find(NS + "g")
        self.assertEqual(len(bubble.findall(NS + "rect")), 0)
        outline = bubble.findall(NS + "path")[0].get("d")
        self.assertEqual(outline.count("M"), 1)
        self.assertTrue(outline.endswith("Z"))
        # The tail is part of the perimeter rather than a line over a closed rectangle.
        calculator = ET.fromstring(files["Clair/calculator.svg"]).find(NS + "g")
        operators = calculator.findall(NS + "path")[0].get("d")
        horizontal = re.findall(r"M(\d+) (\d+) H(\d+)", operators)
        # The final two horizontal marks form '='. Measure their real clear gap
        # so merely increasing stroke weight cannot close it again.
        first, second = horizontal[-2:]
        self.assertEqual((first[0], first[2]), (second[0], second[2]))
        width = float(calculator.get("stroke-width"))
        clear_gap = abs(float(second[1]) - float(first[1])) - width
        self.assertGreaterEqual(clear_gap, width)

    def test_fresh_build_and_check_preserve_bytes_and_refuse_rebuild(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "icons"
            result = icons.build_icons(self.document, output)
            self.assertEqual(len(result["files"]), 562)
            before = tree_snapshot(output)
            self.assertEqual(before, icons.render_icons(self.document))
            icons.build_icons(self.document, output, check=True)
            self.assertEqual(tree_snapshot(output), before)
            with self.assertRaisesRegex(ValueError, "new output"):
                icons.build_icons(self.document, output)
            self.assertEqual(tree_snapshot(output), before)

    def test_foreign_existing_file_folder_and_empty_folder_are_preserved(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            for name in ("foreign", "empty"):
                output = base / name
                output.mkdir()
                if name == "foreign":
                    (output / "personal.txt").write_bytes(b"keep this exact file")
                before = tree_snapshot(output)
                for check in (False, True):
                    with self.assertRaises(ValueError):
                        icons.build_icons(self.document, output, check=check)
                    self.assertEqual(tree_snapshot(output), before)
            existing = base / "existing-file"
            existing.write_bytes(b"unchanged")
            with self.assertRaises(ValueError):
                icons.build_icons(self.document, existing)
            self.assertEqual(existing.read_bytes(), b"unchanged")

    def test_check_refuses_changed_missing_extra_file_and_extra_directory_without_repair(self):
        for mutation in ("changed", "missing", "extra-file", "extra-dir", "manifest"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "icons"
                icons.build_icons(self.document, output)
                item = output / "Clair/phone.svg"
                if mutation == "changed":
                    item.write_bytes(item.read_bytes() + b" ")
                elif mutation == "missing":
                    item.unlink()
                elif mutation == "extra-file":
                    (output / "extra.txt").write_bytes(b"preserve")
                elif mutation == "extra-dir":
                    (output / "extra").mkdir()
                else:
                    (output / "manifest.json").write_bytes(b"{}\n")
                before = tree_snapshot(output)
                with self.assertRaisesRegex(ValueError, "differs"):
                    icons.build_icons(self.document, output, check=True)
                self.assertEqual(tree_snapshot(output), before)
                if mutation == "extra-dir":
                    self.assertTrue((output / "extra").is_dir())

    def test_invalid_tokens_are_rejected_before_output_creation(self):
        invalid = [None, [], {**self.document, "schema_version": True},
                   {**self.document, "version": None}, {**self.document, "themes": None}]
        injection = copy.deepcopy(self.document)
        injection["themes"]["Clair"]["accent"] = '#355e77" onload="bad'
        invalid.append(injection)
        contrast = copy.deepcopy(self.document)
        contrast["themes"]["Obscur"]["text"] = contrast["themes"]["Obscur"]["panel"]
        invalid.append(contrast)
        missing = copy.deepcopy(self.document)
        del missing["themes"]["Clair"]["focus"]
        invalid.append(missing)
        for document in invalid:
            with self.subTest(document=document), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "icons"
                with self.assertRaises(ValueError):
                    icons.build_icons(document, output)
                self.assertFalse(output.exists())

    def test_managed_dist_and_filesystem_root_are_not_output_targets(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(icons, "ROOT", Path(temporary)):
            for output in (Path(temporary) / "dist", Path(temporary) / "dist/icons", Path(Path(temporary).anchor)):
                with self.subTest(output=output), self.assertRaises(ValueError):
                    icons.build_icons(self.document, output)
            self.assertFalse((Path(temporary) / "dist").exists())

    def test_linked_output_ancestor_is_rejected_without_touching_target(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            target = base / "target"
            target.mkdir()
            (target / "keep.txt").write_bytes(b"unchanged")
            link = base / "link"
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"Symlink fixture unavailable: {error}")
            with self.assertRaisesRegex(ValueError, "links or reparse"):
                icons.build_icons(self.document, link / "icons")
            self.assertEqual(tree_snapshot(target), {"keep.txt": b"unchanged"})

    def test_cli_requires_output_and_check_does_not_create_missing_tree(self):
        with self.assertRaises(SystemExit) as error:
            icons.main([])
        self.assertEqual(error.exception.code, 2)
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "icons"
            self.assertEqual(icons.main(["--output", str(output)]), 0)
            self.assertEqual(icons.main(["--output", str(output), "--check"]), 0)
            before = tree_snapshot(output)
            with self.assertRaises(SystemExit) as existing:
                icons.main(["--output", str(output)])
            self.assertEqual(existing.exception.code, 1)
            self.assertEqual(tree_snapshot(output), before)
            missing = Path(temporary) / "missing"
            with self.assertRaises(SystemExit) as check:
                icons.main(["--output", str(missing), "--check"])
            self.assertEqual(check.exception.code, 1)
            self.assertFalse(missing.exists())


if __name__ == "__main__":
    unittest.main()
