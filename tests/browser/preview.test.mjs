import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { chromium, webkit } from 'playwright';
import { spawnSync } from 'node:child_process';
import { mkdtemp, readFile, writeFile, mkdir, rename, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import http from 'node:http';
import crypto from 'node:crypto';
import { inflateSync } from 'node:zlib';
import { assertRenderedFace } from './font-evidence.mjs';

const root = fileURLToPath(new URL('../../', import.meta.url));
let temp, site, server, browser, origin;
const results = { environment: {}, scenarios: [], fonts: {}, metrics: {} };
const failures = [];
const evidence = process.env.THEME_EVIDENCE_DIR;
const python = process.platform === 'win32' ? ['py', '-3.11', '-X', 'utf8'] : ['python3'];
const generalIconFunctions = [
  'phone', 'messages', 'contacts', 'camera', 'gallery', 'settings', 'calendar', 'clock',
  'files', 'notes', 'mail', 'browser', 'maps', 'music', 'video', 'store', 'wallet',
  'calculator', 'weather', 'health', 'fitness', 'voice-recorder', 'home', 'search',
];
const namedIconApps = [
  ['google-chrome', 'Google Chrome', 'com.android.chrome'], ['youtube', 'YouTube', 'com.google.android.youtube'],
  ['google-maps', 'Google Maps', 'com.google.android.apps.maps'], ['gmail', 'Gmail', 'com.google.android.gm'],
  ['google-photos', 'Google Photos', 'com.google.android.apps.photos'], ['google-messages', 'Google Messages', 'com.google.android.apps.messaging'],
  ['google-calendar', 'Google Calendar', 'com.google.android.calendar'], ['google-drive', 'Google Drive', 'com.google.android.apps.docs'],
  ['samsung-browser', 'Samsung Browser', 'com.sec.android.app.sbrowser'], ['samsung-notes', 'Samsung Notes', 'com.samsung.android.app.notes'],
  ['samsung-health', 'Samsung Health', 'com.sec.android.app.shealth'], ['garmin-connect', 'Garmin Connect', 'com.garmin.android.apps.connectmobile'],
  ['whatsapp', 'WhatsApp', 'com.whatsapp'], ['messenger', 'Messenger', 'com.facebook.orca'],
  ['instagram', 'Instagram', 'com.instagram.android'], ['facebook', 'Facebook', 'com.facebook.katana'],
  ['snapchat', 'Snapchat', 'com.snapchat.android'], ['tiktok', 'TikTok', 'com.zhiliaoapp.musically'],
  ['discord', 'Discord', 'com.discord'], ['reddit', 'Reddit', 'com.reddit.frontpage'],
  ['pinterest', 'Pinterest', 'com.pinterest'], ['telegram', 'Telegram', 'org.telegram.messenger'],
  ['spotify', 'Spotify', 'com.spotify.music'], ['netflix', 'Netflix', 'com.netflix.mediaclient'],
  ['amazon-shopping', 'Amazon Shopping', 'com.amazon.mShop.android.shopping'], ['walmart', 'Walmart', 'com.walmart.android'],
  ['temu', 'Temu', 'com.einnovation.temu'], ['uber', 'Uber', 'com.ubercab'], ['doordash', 'DoorDash', 'com.dd.doordash'],
  ['paypal', 'PayPal', 'com.paypal.android.p2pmobile'], ['outlook', 'Microsoft Outlook', 'com.microsoft.office.outlook'],
  ['chatgpt', 'ChatGPT', 'com.openai.chatgpt'], ['firefox', 'Firefox', 'org.mozilla.firefox'],
];
const additionalIconApps = [
  [
    "x",
    "X",
    "com.twitter.android"
  ],
  [
    "threads",
    "Threads",
    "com.instagram.barcelona"
  ],
  [
    "signal",
    "Signal",
    "org.thoughtcrime.securesms"
  ],
  [
    "twitch",
    "Twitch",
    "tv.twitch.android.app"
  ],
  [
    "capcut",
    "CapCut",
    "com.lemon.lvoverseas"
  ],
  [
    "disney-plus",
    "Disney+",
    "com.disney.disneyplus"
  ],
  [
    "prime-video",
    "Prime Video",
    "com.amazon.avod.thirdpartyclient"
  ],
  [
    "microsoft-teams",
    "Teams",
    "com.microsoft.teams"
  ],
  [
    "zoom",
    "Zoom",
    "us.zoom.videomeetings"
  ],
  [
    "google-meet",
    "Google Meet",
    "com.google.android.apps.tachyon"
  ],
  [
    "google-docs",
    "Google Docs",
    "com.google.android.apps.docs.editors.docs"
  ],
  [
    "google-sheets",
    "Google Sheets",
    "com.google.android.apps.docs.editors.sheets"
  ],
  [
    "onedrive",
    "OneDrive",
    "com.microsoft.skydrive"
  ],
  [
    "google-translate",
    "Google Translate",
    "com.google.android.apps.translate"
  ],
  [
    "google-keep",
    "Google Keep",
    "com.google.android.keep"
  ],
  [
    "google-wallet",
    "Google Wallet",
    "com.google.android.apps.walletnfcrel"
  ],
  [
    "cash-app",
    "Cash App",
    "com.squareup.cash"
  ],
  [
    "venmo",
    "Venmo",
    "com.venmo"
  ],
  [
    "ebay",
    "eBay",
    "com.ebay.mobile"
  ],
  [
    "mcdonalds",
    "McDonald's",
    "com.mcdonalds.app"
  ],
  [
    "starbucks",
    "Starbucks",
    "com.starbucks.mobilecard"
  ],
  [
    "duolingo",
    "Duolingo",
    "com.duolingo"
  ],
  [
    "waze",
    "Waze",
    "com.waze"
  ],
  [
    "canva",
    "Canva",
    "com.canva.editor"
  ]
];
const firstNamedIconApps = namedIconApps.slice();
namedIconApps.push(...additionalIconApps);
const secondNamedIconApps = namedIconApps.slice();
const thirdIconApps = [
  [
    "linkedin",
    "LinkedIn",
    "com.linkedin.android"
  ],
  [
    "github",
    "GitHub",
    "com.github.android"
  ],
  [
    "notion",
    "Notion",
    "notion.id"
  ],
  [
    "microsoft-edge",
    "Microsoft Edge",
    "com.microsoft.emmx"
  ],
  [
    "brave",
    "Brave",
    "com.brave.browser"
  ],
  [
    "microsoft-authenticator",
    "Microsoft Authenticator",
    "com.azure.authenticator"
  ],
  [
    "google-authenticator",
    "Google Authenticator",
    "com.google.android.apps.authenticator2"
  ],
  [
    "samsung-smartthings",
    "SmartThings",
    "com.samsung.android.oneconnect"
  ]
];
namedIconApps.push(...thirdIconApps);
const monochromeNamedIconApps = namedIconApps.slice();
const companionIconApps = [
  ['good-lock', 'Good Lock', 'com.samsung.android.goodlock'],
  ['connect-iq-store', 'Connect IQ Store', 'com.garmin.connectiq'],
  ['steam', 'Steam', 'com.valvesoftware.android.steam.community'],
  ['reuters', 'Reuters', 'com.thomsonreuters.reuters'],
  ['home-depot', 'Home Depot', 'com.thehomedepot'],
  ['patreon', 'Patreon', 'com.patreon.android'],
];
namedIconApps.push(...companionIconApps);
const companionNamedIconApps = namedIconApps.slice();
const broadIconApps = [
  ['youtube-music', 'YouTube Music', 'com.google.android.apps.youtube.music'],
  ['audible', 'Audible', 'com.audible.application'],
  ['amazon-kindle', 'Amazon Kindle', 'com.amazon.kindle'],
  ['pocket-casts', 'Pocket Casts', 'au.com.shiftyjelly.pocketcasts'],
  ['vlc', 'VLC', 'org.videolan.vlc'],
  ['shazam', 'Shazam', 'com.shazam.android'],
  ['soundcloud', 'SoundCloud', 'com.soundcloud.android'],
  ['hulu', 'Hulu', 'com.hulu.plus'],
  ['target', 'Target', 'com.target.ui'],
  ['costco', 'Costco', 'com.costco.app.android'],
  ['best-buy', 'Best Buy', 'com.bestbuy.android'],
  ['etsy', 'Etsy', 'com.etsy.android'],
  ['aliexpress', 'AliExpress', 'com.alibaba.aliexpresshd'],
  ['shein', 'SHEIN', 'com.zzkko'],
  ['instacart', 'Instacart', 'com.instacart.client'],
  ['airbnb', 'Airbnb', 'com.airbnb.android'],
  ['booking', 'Booking.com', 'com.booking'],
  ['expedia', 'Expedia', 'com.expedia.bookings'],
  ['lyft', 'Lyft', 'me.lyft.android'],
  ['uber-eats', 'Uber Eats', 'com.ubercab.eats'],
  ['google-earth', 'Google Earth', 'com.google.earth'],
  ['google-news', 'Google News', 'com.google.android.apps.magazines'],
  ['galaxy-wearable', 'Galaxy Wearable', 'com.samsung.android.app.watchmanager'],
  ['files-by-google', 'Files by Google', 'com.google.android.apps.nbu.files'],
  ['adobe-acrobat', 'Adobe Acrobat', 'com.adobe.reader'],
  ['microsoft-word', 'Microsoft Word', 'com.microsoft.office.word'],
  ['microsoft-excel', 'Microsoft Excel', 'com.microsoft.office.excel'],
  ['microsoft-powerpoint', 'PowerPoint', 'com.microsoft.office.powerpoint'],
  ['google-slides', 'Google Slides', 'com.google.android.apps.docs.editors.slides'],
  ['google-lens', 'Google Lens', 'com.google.ar.lens'],
  ['roblox', 'Roblox', 'com.roblox.client'],
  ['minecraft', 'Minecraft', 'com.mojang.minecraftpe'],
];
namedIconApps.push(...broadIconApps);
const broadNamedIconApps = namedIconApps.slice();
const everydayIconApps = [
  ["slack", "Slack", "com.Slack"],
  ["trello", "Trello", "com.trello"],
  ["todoist", "Todoist", "com.todoist"],
  ["ticktick", "TickTick", "com.ticktick.task"],
  ["evernote", "Evernote", "com.evernote"],
  ["obsidian", "Obsidian", "md.obsidian"],
  ["dropbox", "Dropbox", "com.dropbox.android"],
  ["proton-mail", "Proton Mail", "ch.protonmail.android"],
  ["yahoo-mail", "Yahoo Mail", "com.yahoo.mobile.client.android.mail"],
  ["google-tasks", "Google Tasks", "com.google.android.apps.tasks"],
  ["google-one", "Google One", "com.google.android.apps.subscriptions.red"],
  ["microsoft-copilot", "Microsoft Copilot", "com.microsoft.office.officehubrow"],
  ["google-gemini", "Google Gemini", "com.google.android.apps.bard"],
  ["claude", "Claude", "com.anthropic.claude"],
  ["perplexity", "Perplexity", "ai.perplexity.app.android"],
  ["bitwarden", "Bitwarden", "com.x8bit.bitwarden"],
  ["apple-music", "Apple Music", "com.apple.android.music"],
  ["apple-tv", "Apple TV", "com.apple.atve.androidtv.appletv"],
  ["hbo-max", "HBO Max", "com.wbd.stream"],
  ["peacock", "Peacock", "com.peacocktv.peacockandroid"],
  ["paramount-plus", "Paramount+", "com.cbs.app"],
  ["plex", "Plex", "com.plexapp.android"],
  ["tubi", "Tubi", "com.tubitv"],
  ["pluto-tv", "Pluto TV", "tv.pluto.android"],
  ["crunchyroll", "Crunchyroll", "com.crunchyroll.crunchyroid"],
  ["pandora", "Pandora", "com.pandora.android"],
  ["iheartradio", "iHeart", "com.clearchannel.iheartradio.controller"],
  ["siriusxm", "SiriusXM", "com.sirius"],
  ["adobe-lightroom", "Adobe Lightroom", "com.adobe.lrmobile"],
  ["photoshop-express", "Photoshop Express", "com.adobe.psmobile"],
  ["snapseed", "Snapseed", "com.niksoftware.snapseed"],
  ["picsart", "Picsart", "com.picsart.studio"],
  ["strava", "Strava", "com.strava"],
  ["fitbit", "Google Health (Fitbit)", "com.fitbit.FitbitMobile"],
  ["google-fit", "Google Fit", "com.google.android.apps.fitness"],
  ["myfitnesspal", "MyFitnessPal", "com.myfitnesspal.android"],
  ["alltrails", "AllTrails", "com.alltrails.alltrails"],
  ["komoot", "Komoot", "de.komoot.android"],
  ["amazon-alexa", "Amazon Alexa", "com.amazon.dee.app"],
  ["ring", "Ring", "com.ringapp"],
  ["blink", "Blink", "com.immediasemi.android.blink"],
  ["google-home", "Google Home", "com.google.android.apps.chromecast.app"],
  ["zillow", "Zillow", "com.zillow.android.zillowmap"],
  ["chase", "Chase", "com.chase.sig.android"],
  ["capital-one", "Capital One", "com.konylabs.capitalone"],
  ["chime", "Chime", "com.onedebit.chime"],
  ["ups", "UPS", "com.ups.mobile.android"],
  ["fedex", "FedEx", "com.fedex.ida.android"],
];
namedIconApps.push(...everydayIconApps);
const everydayNamedIconApps = [...namedIconApps];
const foodOrderIconApps = [
  ["chipotle", "Chipotle", "com.chipotle.ordering"],
  ["taco-bell", "Taco Bell", "com.tacobell.ordering"],
  ["wendys", "Wendy's", "com.wendys.nutritiontool"],
  ["burger-king", "Burger King", "com.emn8.mobilem8.nativeapp.bk"],
  ["dunkin", "Dunkin'", "com.dunkinbrands.otgo"],
  ["chick-fil-a", "Chick-fil-A", "com.chickfila.cfaflagship"],
  ["dominos", "Domino's", "com.dominospizza"],
  ["pizza-hut", "Pizza Hut", "com.yum.pizzahut"],
  ["subway", "Subway", "com.subway.mobile.subwayapp03"],
  ["panera-bread", "Panera Bread", "com.panera.bread"],
  ["kfc-us", "KFC US", "com.kfc.us.mobile"],
  ["grubhub", "Grubhub", "com.grubhub.android"],
];
namedIconApps.push(...foodOrderIconApps);
const foodOrderNamedIconApps = [...namedIconApps];
const travelIconApps = [
  ['fly-delta', 'Fly Delta', 'com.delta.mobile.android'],
  ['united-airlines', 'United Airlines', 'com.united.mobile.android'],
  ['american-airlines', 'American Airlines', 'com.aa.android'],
  ['southwest-airlines', 'Southwest Airlines', 'com.southwestairlines.mobile'],
  ['amtrak', 'Amtrak', 'com.amtrak.rider'],
  ['transit', 'Transit', 'com.thetransitapp.droid'],
  ['moovit', 'Moovit', 'com.tranzmate'],
  ['citymapper', 'Citymapper', 'com.citymapper.app.release'],
  ['tripit', 'TripIt', 'com.tripit'],
  ['hopper', 'Hopper', 'com.hopper.mountainview.play'],
];
namedIconApps.push(...travelIconApps);
const travelNamedIconApps = [...namedIconApps];
const financeIconApps = [
  ['bank-of-america', 'Bank of America', 'com.infonow.bofa'],
  ['wells-fargo', 'Wells Fargo', 'com.wf.wellsfargomobile'],
  ['us-bank', 'U.S. Bank', 'com.usbank.mobilebanking'],
  ['pnc', 'PNC', 'com.pnc.ecommerce.mobile'],
  ['discover', 'Discover', 'com.discoverfinancial.mobile'],
  ['amex', 'Amex', 'com.americanexpress.android.acctsvcs.us'],
  ['fidelity-investments', 'Fidelity Investments', 'com.fidelity.android'],
  ['schwab', 'Schwab', 'com.schwab.mobile'],
  ['sofi', 'SoFi', 'com.sofi.mobile'],
  ['robinhood', 'Robinhood', 'com.robinhood.android'],
];
namedIconApps.push(...financeIconApps);
const financeNamedIconApps = [...namedIconApps];
const weatherIconApps = [
  ['accuweather', 'AccuWeather', 'com.accuweather.android'],
  ['weather-channel', 'The Weather Channel', 'com.weather.Weather'],
  ['weather-underground', 'Weather Underground', 'com.wunderground.android.weather'],
  ['windy-com', 'Windy.com', 'com.windyty.android'],
  ['myradar', 'MyRadar', 'com.acmeaom.android.myradar'],
  ['weatherbug', 'WeatherBug', 'com.aws.android'],
  ['one-weather', '1Weather', 'com.handmark.expressweather'],
  ['clime', 'Clime', 'com.apalon.weatherradar.free'],
  ['windfinder', 'Windfinder', 'com.studioeleven.windfinder'],
  ['rainviewer', 'RainViewer', 'com.lucky_apps.RainViewer'],
];
namedIconApps.push(...weatherIconApps);
const weatherNamedIconApps = [...namedIconApps];
const runningTrainingIconApps = [
  ['nike-run-club', 'Nike Run Club', 'com.nike.plusgps'],
  ['adidas-running', 'adidas Running', 'com.runtastic.android'],
  ['asics-runkeeper', 'ASICS Runkeeper', 'com.fitnesskeeper.runkeeper.pro'],
  ['map-my-run', 'Map My Run', 'com.mapmyrun.android2'],
  ['runna', 'Runna', 'com.runbuddy.prod'],
  ['trainingpeaks', 'TrainingPeaks', 'com.peaksware.trainingpeaks'],
  ['zwift-companion', 'Zwift Companion', 'com.zwift.android.prod'],
  ['relive', 'Relive', 'cc.relive.reliveapp'],
];
namedIconApps.push(...runningTrainingIconApps);
const learningIconApps = [
  ['google-classroom', 'Google Classroom', 'com.google.android.apps.classroom'],
  ['khan-academy', 'Khan Academy', 'org.khanacademy.android'],
  ['coursera', 'Coursera', 'org.coursera.android'],
  ['udemy', 'Udemy', 'com.udemy.android'],
  ['edx', 'edX', 'org.edx.mobile'],
  ['quizlet', 'Quizlet', 'com.quizlet.quizletandroid'],
  ['photomath', 'Photomath', 'com.microblink.photomath'],
  ['brainly', 'Brainly', 'co.brainly'],
];
namedIconApps.push(...learningIconApps);
const learningNamedIconApps = [...namedIconApps];
const readingIconApps = [
  ["google-play-books", "Google Play Books", "com.google.android.apps.books"],
  ["libby", "Libby", "com.overdrive.mobile.android.libby"],
  ["kobo-books", "Kobo Books", "com.kobobooks.android"],
  ["goodreads", "Goodreads", "com.goodreads"],
  ["wattpad", "Wattpad", "wp.wattpad"],
  ["webtoon", "WEBTOON", "com.naver.linewebtoon"],
  ["readera", "ReadEra", "org.readera"],
  ["moon-reader", "Moon+ Reader", "com.flyersoft.moonreader"],
];
namedIconApps.push(...readingIconApps);
const readingNamedIconApps = [...namedIconApps];
const phoneServiceApps = [
  [
    "ace-hardware",
    "Ace Hardware",
    "com.acehardware.rewards"
  ],
  [
    "ai-dungeon",
    "AI Dungeon",
    "com.aidungeon"
  ],
  [
    "gaming-hub",
    "Gaming Hub",
    "com.samsung.android.game.gamehome"
  ],
  [
    "kroger",
    "Kroger",
    "com.kroger.mobile"
  ],
  [
    "affirm",
    "Affirm",
    "com.affirm.central"
  ],
  [
    "usaa",
    "USAA",
    "com.usaa.mobile.android.usaa"
  ],
  [
    "proton-authenticator",
    "Proton Authenticator",
    "proton.android.authenticator"
  ],
  [
    "wikipedia",
    "Wikipedia",
    "org.wikipedia"
  ],
  [
    "xbox",
    "Xbox",
    "com.microsoft.xboxone.smartglass"
  ],
  [
    "shop",
    "Shop",
    "com.shopify.arrive"
  ],
  [
    "fandom",
    "Fandom",
    "com.fandom.app"
  ],
  [
    "shonen-jump",
    "Shonen Jump",
    "com.viz.wsj.android"
  ],
  [
    "smart-switch",
    "Smart Switch",
    "com.sec.android.easyMover"
  ],
  [
    "steam-chat",
    "Steam Chat",
    "com.valvesoftware.android.steam.friendsui"
  ],
  [
    "sonic",
    "Sonic",
    "com.sonic.sonicdrivein"
  ],
  [
    "samsung-global-goals",
    "Samsung Global Goals",
    "com.samsung.sree"
  ],
  [
    "theme-park",
    "Theme Park",
    "com.samsung.android.themedesigner"
  ],
  [
    "zillow-rentals",
    "Zillow Rentals",
    "com.zillow.android.rentals"
  ],
  [
    "samsung-find",
    "Samsung Find",
    "com.samsung.android.app.find"
  ],
  [
    "dollar-general",
    "Dollar General",
    "com.dollargeneral.android"
  ],
  [
    "sound-connect",
    "Sound Connect",
    "com.sony.songpal.mdr"
  ],
  [
    "samsung-pass",
    "Samsung Pass",
    "com.samsung.android.samsungpass"
  ],
  [
    "va",
    "VA",
    "gov.va.mobileapp"
  ],
  [
    "battle-net",
    "Battle.net",
    "com.blizzard.messenger"
  ],
  [
    "coinbase",
    "Coinbase",
    "com.coinbase.android"
  ],
  [
    "credit-one",
    "Credit One",
    "com.creditonebank.mobile"
  ],
  [
    "samsung-members",
    "Samsung Members",
    "com.samsung.android.voc"
  ],
  [
    "proton-vpn",
    "Proton VPN",
    "ch.protonvpn.android"
  ],
  [
    "t-life",
    "T-Life",
    "com.tmobile.tuesdays"
  ],
  [
    "my-spectrum",
    "My Spectrum",
    "com.brighthouse.mybhn"
  ],
  [
    "g2a",
    "G2A",
    "com.g2a.marketplace"
  ],
  [
    "samsung-tv-plus",
    "Samsung TV Plus",
    "com.samsung.android.tvplus"
  ],
  [
    "ap-news",
    "AP News",
    "mnn.Android"
  ],
  [
    "link-to-windows",
    "Link to Windows",
    "com.microsoft.appmanager"
  ],
  [
    "tips",
    "Tips",
    "com.samsung.android.app.tips"
  ],
  [
    "proton-pass",
    "Proton Pass",
    "proton.android.pass"
  ],
  [
    "shop-samsung",
    "Shop Samsung",
    "com.samsung.ecomm"
  ],
  [
    "wallpaper-engine",
    "Wallpaper Engine",
    "io.wallpaperengine.weclient"
  ],
  [
    "asus-router",
    "ASUS Router",
    "com.asus.aihome"
  ],
  [
    "mochi-health",
    "Mochi Health",
    "com.mochihealth.mochihealth"
  ]
];

namedIconApps.push(...phoneServiceApps);

const iconFunctions = [...namedIconApps.map(row => row[0]), ...generalIconFunctions];
const iconManifestFunctions = [...generalIconFunctions, ...namedIconApps.map(row => row[0])];
const iconLabels = new Map([...generalIconFunctions.map(name => [name, name.replaceAll('-', ' ').replace(/\b[a-z]/g, letter => letter.toUpperCase())]),
  ...namedIconApps.map(([id, label]) => [id, label])]);
const iconArchive = 'icons/Clair-Obscur-SVG-Icons-0.17.0.zip';
const readingIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.16.0.zip';
const readingIconDigest = '3fbf8b53e12ddae6ea354d6ed20a1464c4874192a24f5dee7f231baed0e7f3a0';
const galaxyIconIds = new Set(['gaming-hub', 'theme-park', 'samsung-pass', 'tips']);
const appStoreUrl = (id, packageId) => galaxyIconIds.has(id) ?
  `https://galaxystore.samsung.com/detail/${packageId}` : `https://play.google.com/store/apps/details?id=${packageId}`;
const learningIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.15.0.zip';
const learningIconDigest = 'df05503c0f1825d09e5b5fb96fcb87401490fef601518ca4e526a6e6d564197c';
const runningTrainingIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.14.0.zip';
const runningTrainingIconDigest = '4b3324d30b0b6e94a52e0d51a206e499e6e2b6be82052752963da9446c44e6c1';
const weatherIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.13.0.zip';
const weatherIconDigest = 'e6f7c532d0c625666a0f3403ee27842ac8612e6368d49f64fb3e84b667a42ca1';
const financeIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.12.0.zip';
const financeIconDigest = 'db8ed7e2c62d36786b2c2d510fdf68f83649fda512f6bb018f5043491cb8f0cf';
const travelIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.11.0.zip';
const travelIconDigest = '04cce2b812ad4f6ed7bcfda172a9bfe5a6d63d058b6899570a1dbe94f162884d';
const foodOrderIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.10.0.zip';
const foodOrderIconDigest = 'a81ffb8c4fb3ef32f3c8391c53016e99246b755ce9079fdee84b5948790ab8e0';
const everydayIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.9.0.zip';
const everydayIconDigest = '994ce1d819414b06062d5cd32a03eeb8891e9074b09491dfb2c774a55ae5a3b1';
const broadIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.8.0.zip';
const broadIconDigest = 'fcdaec582be7508b3e62bd9168695ea1650e33c8e53c3de46f3614ae53d833cf';
const companionIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.7.0.zip';
const companionIconDigest = 'aa18db922e824cd2bfa1ada2fbc08125af2605d9c5acb2ad8bfdb439985f4f05';
const monochromeIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.6.0.zip';
const monochromeIconDigest = '241efb1fe6584df4f66c84571bfe671059404e83be8d67876f415af6564a56bb';
const thirdAppIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.5.0.zip';
const thirdAppIconDigest = '2310c0151c0c3215e99d24a7aa92616a55dc726b2e38466427890223d778307a';
const secondAppIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.4.0.zip';
const secondAppIconDigest = 'fc2540a7bf9a6d580a3238904b6e7e4f6b77ca5df5797cc7ce3a6de782cda0cf';
const firstAppIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.3.0.zip';
const firstAppIconDigest = 'd217cab68c1c118511078c189ec672b80cbcb29be285bf5cc58123516791e756';
const previousIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.2.0.zip';
const previousIconDigest = '6ae67a5aab7f4e0a50537bb6dcf3b383c5fc6e9e001d68db12a7413aaa376312';
const legacyIconArchive = 'icons/Clair-Obscur-SVG-Icons-0.1.0.zip';
const legacyIconDigest = '040d7f472ca12d6cf115daaf2631b83477183dee42f0b91c6133e62322014e34';
const iconChecksums = digest => `${digest}  ${path.basename(iconArchive)}\n${readingIconDigest}  ${path.basename(readingIconArchive)}\n${learningIconDigest}  ${path.basename(learningIconArchive)}\n${runningTrainingIconDigest}  ${path.basename(runningTrainingIconArchive)}\n${weatherIconDigest}  ${path.basename(weatherIconArchive)}\n${financeIconDigest}  ${path.basename(financeIconArchive)}\n${travelIconDigest}  ${path.basename(travelIconArchive)}\n${foodOrderIconDigest}  ${path.basename(foodOrderIconArchive)}\n${everydayIconDigest}  ${path.basename(everydayIconArchive)}\n${broadIconDigest}  ${path.basename(broadIconArchive)}\n${companionIconDigest}  ${path.basename(companionIconArchive)}\n${monochromeIconDigest}  ${path.basename(monochromeIconArchive)}\n${thirdAppIconDigest}  ${path.basename(thirdAppIconArchive)}\n${secondAppIconDigest}  ${path.basename(secondAppIconArchive)}\n${firstAppIconDigest}  ${path.basename(firstAppIconArchive)}\n${previousIconDigest}  ${path.basename(previousIconArchive)}\n${legacyIconDigest}  ${path.basename(legacyIconArchive)}\n`;
const iconPaths = iconFunctions.flatMap(functionName => ['Clair', 'Obscur'].map(appearance => `icons/${appearance}/${functionName}.svg`));
const terminalFragment = 'Clair-Obscur-Windows-Terminal-0.1.0.json';
const terminalArchive = 'Clair-Obscur-Windows-Terminal-0.1.0.zip';
const terminalAnsi = [
  ['black', 'Black'], ['red', 'Red'], ['green', 'Green'], ['yellow', 'Yellow'],
  ['blue', 'Blue'], ['purple', 'Purple'], ['cyan', 'Cyan'], ['white', 'White'],
  ['brightBlack', 'Bright black'], ['brightRed', 'Bright red'], ['brightGreen', 'Bright green'], ['brightYellow', 'Bright yellow'],
  ['brightBlue', 'Bright blue'], ['brightPurple', 'Bright purple'], ['brightCyan', 'Bright cyan'], ['brightWhite', 'Bright white'],
];

function run(args) {
  const result = spawnSync(python[0], [...python.slice(1), ...args], {
    cwd: root, encoding: 'utf8', windowsHide: true, timeout: 30000, maxBuffer: 4 * 1024 * 1024,
  });
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stdout + result.stderr);
}

before(async () => {
  temp = await mkdtemp(path.join(tmpdir(), 'clair-obscur-browser-'));
  const artifacts = path.join(temp, 'artifacts');
  const generated = path.join(temp, 'generated', 'site');
  site = path.join(temp, 'relocated', 'preview');
  run(['build.py', '--output', artifacts]);
  run(['preview.py', '--artifacts', artifacts, '--output', generated]);
  await mkdir(path.dirname(site));
  await rename(generated, site);
  server = http.createServer(async (request, response) => {
    const pathname = decodeURIComponent(new URL(request.url, 'http://localhost').pathname);
    const target = path.resolve(site, '.' + (pathname === '/' ? '/index.html' : pathname));
    if (!target.startsWith(site + path.sep)) { response.writeHead(403).end(); return; }
    try {
      const body = await readFile(target);
      const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml', '.zip': 'application/zip', '.xpi': 'application/x-xpinstall' };
      response.writeHead(200, { 'Content-Type': types[path.extname(target)] || 'text/plain', 'Cache-Control': 'no-store' });
      response.end(body);
    } catch { response.writeHead(404).end(); }
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  origin = `http://127.0.0.1:${server.address().port}`;
  // Uses a disposable profile and never falls back to a visible browser.
  // WebKit can run the portable layout and download checks by test name.
  // The exact glyph-face checks continue to require Chromium's CDP interface.
  const engine = process.env.THEME_BROWSER_ENGINE || 'chromium';
  assert.ok(['chromium', 'webkit'].includes(engine), 'Unknown specimen browser engine');
  const launchOptions = engine === 'webkit' ? { headless: true } : {
    channel: process.env.THEME_BROWSER_CHANNEL || 'chrome', headless: true,
    chromiumSandbox: true, args: ['--mute-audio', '--disable-gpu'],
  };
  browser = await (engine === 'webkit' ? webkit : chromium).launch(launchOptions);
  results.environment = { engine, browser: browser.version(), channel: launchOptions.channel, requestedLaunch: launchOptions, node: process.version, platform: process.platform, renderer: 'isolated headless page', relocatedPreview: true, nativeChromeFrameVerified: false, equibopVerified: false };
  let versionSession;
  try {
    versionSession = await browser.newBrowserCDPSession();
    const { product, revision, protocolVersion, jsVersion } = await versionSession.send('Browser.getVersion');
    results.environment.browserProcess = { status: 'observed', product, revision, protocolVersion, jsVersion };
  } catch (error) {
    results.environment.browserProcess = { status: 'unavailable', error: error.name };
  } finally { await versionSession?.detach(); }
  if (evidence) await mkdir(evidence, { recursive: true });
});

after(async () => {
  await browser?.close();
  if (server) await new Promise(resolve => server.close(resolve));
  if (evidence) await writeFile(path.join(evidence, 'browser-evidence.json'), JSON.stringify({ ...results, failures }, null, 2) + '\n');
  // This is the one newly created test directory, never a user profile.
  if (temp && path.basename(temp).startsWith('clair-obscur-browser-') && path.dirname(temp) === tmpdir()) await rm(temp, { recursive: true });
});

async function pageFor(options = {}) {
  const { missingFont = false, setup, ...contextOptions } = options;
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, ...contextOptions });
  const page = await context.newPage();
  const network = [], consoleErrors = [];
  page.on('pageerror', error => consoleErrors.push(String(error)));
  page.on('console', message => { if (message.type() === 'error') consoleErrors.push(message.text()); });
  await context.route('**/*', route => {
    network.push(route.request().url());
    if (!route.request().url().startsWith(origin + '/')) { failures.push('unexpected network origin'); return route.abort(); }
    return route.continue();
  });
  if (missingFont) {
    await page.route('**/tokens.css', async route => {
      const original = await readFile(path.join(site, 'tokens.css'), 'utf8');
      await route.fulfill({ contentType: 'text/css', body: original.replace(/src:local\([^;]+;/g, 'src:local("MissingClairObscurFixtureFont");') });
    });
    await page.route('**/preview.css', async route => {
      const original = await readFile(path.join(site, 'preview.css'), 'utf8');
      await route.fulfill({ contentType: 'text/css', body: original.replace('"Clair Obscur Inter", Inter,', '"Clair Obscur Inter",') });
    });
  }
  if (setup) await setup(context, page);
  await page.goto(origin);
  await page.evaluate(() => document.fonts.ready);
  return { context, page, network, consoleErrors };
}

test('both appearances work at desktop and phone widths without horizontal overflow', async () => {
  for (const width of [390, 1280, 2560]) {
    const { context, page, network, consoleErrors } = await pageFor({ viewport: { width, height: 900 } });
    try {
      for (const name of ['Obscur', 'Clair']) {
        await page.getByRole('button', { name, exact: true }).click();
        assert.equal(await page.locator('html').getAttribute('data-theme'), name);
        assert.equal(await page.getByRole('button', { name, exact: true }).getAttribute('aria-pressed'), 'true');
        const measurements = await page.evaluate(() => ({
          width: innerWidth, documentWidth: document.documentElement.scrollWidth,
          background: getComputedStyle(document.body).backgroundColor,
          color: getComputedStyle(document.body).color,
          font: getComputedStyle(document.body).fontFamily,
        }));
        assert.ok(measurements.documentWidth <= width + 1, JSON.stringify(measurements));
        assert.equal(measurements.background, name === 'Obscur' ? 'rgb(0, 0, 0)' : 'rgb(255, 255, 255)');
        results.scenarios.push({ name, viewport: width, measurements, status: 'passed' });
        if (evidence && width !== 2560) await page.screenshot({ path: path.join(evidence, `${name.toLowerCase()}-${width}-specimen.png`), fullPage: true });
      }
      assert.deepEqual([...new Set(network)].sort(), [origin + '/', ...['tokens.css', 'preview.css', 'preview.js', ...iconPaths].map(file => origin + '/' + file)].sort(),
        'The page requests only its four original local assets and the 562 declared local SVGs');
      assert.deepEqual(consoleErrors, []);
    } finally { await context.close(); }
  }
});

test('narrow enlarged headings wrap without reducing text or hiding content', async () => {
  for (const { width, height, enlarged } of [
    { width: 390, height: 844, enlarged: false },
    { width: 844, height: 320, enlarged: false },
    { width: 320, height: 640, enlarged: true },
  ]) {
    const { context, page, consoleErrors } = await pageFor({
      viewport: { width, height }, isMobile: true, hasTouch: true, reducedMotion: 'reduce',
    });
    try {
      if (enlarged) await page.addStyleTag({ content: 'html { font-size: 200%; }' });
      for (const appearance of ['Obscur', 'Clair']) {
        await page.getByRole('button', { name: appearance, exact: true }).tap();
        const layout = await page.evaluate(() => ({
          viewport: innerWidth, pageWidth: document.documentElement.scrollWidth,
          rootFontSize: getComputedStyle(document.documentElement).fontSize,
          headings: ['palettes-heading', 'downloads-heading'].map(id => {
            const node = document.getElementById(id), box = node.getBoundingClientRect();
            const style = getComputedStyle(node);
            return { id, text: node.textContent, fontSize: style.fontSize,
              width: box.width, height: box.height, left: box.left, right: box.right,
              clientWidth: node.clientWidth, scrollWidth: node.scrollWidth,
              overflowX: style.overflowX };
          }),
          controls: [...document.querySelectorAll('.switcher button,.download-card a.button')].map(node => {
            const box = node.getBoundingClientRect();
            return { label: node.textContent, left: box.left, right: box.right, height: box.height };
          }),
        }));
        results.scenarios.push({ name: 'narrow headings', appearance, width, height, enlarged, layout });
        assert.equal(layout.rootFontSize, enlarged ? '32px' : '16px');
        assert.ok(layout.pageWidth <= width + 1, JSON.stringify(layout));
        assert.deepEqual(layout.headings.map(h => h.text), [
          'One identity, two appearances.', 'Choose a platform candidate',
        ]);
        for (const heading of layout.headings) {
          assert.equal(heading.overflowX, 'visible', 'Do not hide the overflowing prose');
          assert.ok(heading.scrollWidth <= heading.clientWidth + 1, JSON.stringify(heading));
          if (enlarged) assert.ok(parseFloat(heading.fontSize) >= 48, 'Keep the enlarged heading size');
        }
        for (const control of layout.controls) {
          assert.ok(control.height >= 44, JSON.stringify(control));
          assert.ok(control.left >= -1 && control.right <= width + 1, JSON.stringify(control));
        }
        if (evidence && enlarged) {
          await page.locator('#palettes-heading').scrollIntoViewIfNeeded();
          await page.screenshot({ path: path.join(evidence, `${appearance.toLowerCase()}-320-enlarged-headings.png`) });
        }
      }
      assert.deepEqual(consoleErrors, []);
    } finally { await context.close(); }
  }
});

test('six genuine Inter glyph faces and native monospace are distinguishable', async t => {
  const { context, page } = await pageFor();
  try {
    const session = await context.newCDPSession(page);
    await session.send('DOM.enable'); await session.send('CSS.enable');
    const faceStates = await page.evaluate(async () => Promise.all(
      [...document.fonts].filter(face => face.family === 'Clair Obscur Inter').map(async face => {
        const record = { family: face.family, weight: face.weight, style: face.style, statusBeforeRequest: face.status };
        try { await face.load(); record.loadRequest = 'fulfilled'; }
        catch (error) { record.loadRequest = 'rejected'; record.error = error.name; }
        return { ...record, status: face.status };
      })));
    results.fonts.localFaces = { required: process.env.THEME_REQUIRE_INTER === '1', faces: faceStates };
    assert.deepEqual(faceStates.map(face => `${face.weight}:${face.style}`).sort(),
      ['400:normal', '400:italic', '600:normal', '600:italic', '700:normal', '700:italic'].sort(),
      'The fixture must declare each required face exactly once');
    const loadedFaces = faceStates.filter(face => face.status === 'loaded').length;
    if (loadedFaces !== 6 && process.env.THEME_REQUIRE_INTER !== '1') {
      t.skip('Six installed Inter faces are required for exact glyph-face verification');
      return;
    }
    assert.equal(loadedFaces, 6, JSON.stringify(results.fonts.localFaces));
    await page.evaluate(async () => {
      await document.fonts.ready;
      await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
    });
    const { root: document } = await session.send('DOM.getDocument');
    const expected = {
      regular: 'Inter-Regular', semibold: 'Inter-SemiBold', bold: 'Inter-Bold', italic: 'Inter-Italic',
      'semibold-italic': 'Inter-SemiBoldItalic', 'bold-italic': 'Inter-BoldItalic',
    };
    for (const [kind, face] of Object.entries(expected)) {
      const { nodeId } = await session.send('DOM.querySelector', { nodeId: document.nodeId, selector: '#face-' + kind });
      const { fonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId });
      results.fonts[kind] = fonts;
      assertRenderedFace(fonts, face);
    }
    const { nodeId } = await session.send('DOM.querySelector', { nodeId: document.nodeId, selector: '#face-code' });
    const { fonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId });
    results.fonts.code = fonts;
    assert.ok(fonts.some(font => font.glyphCount > 0));
    assert.ok(fonts.every(font => !font.postScriptName?.startsWith('Inter')));
    await session.detach();
  } finally { await context.close(); }
});

test('missing local Inter uses fallback without network font requests', async () => {
  const { context, page, network } = await pageFor({ missingFont: true });
  try {
    const session = await context.newCDPSession(page);
    await session.send('DOM.enable'); await session.send('CSS.enable');
    const { root: document } = await session.send('DOM.getDocument');
    const { nodeId } = await session.send('DOM.querySelector', { nodeId: document.nodeId, selector: '#face-regular' });
    const { fonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId });
    assert.ok(fonts.some(font => font.glyphCount > 0));
    const fallbackState = await page.evaluate(() => ({
      body: getComputedStyle(document.body).fontFamily,
      faces: [...document.fonts].map(face => ({ family: face.family, status: face.status })),
    }));
    assert.ok(fallbackState.faces.every(face => face.status === 'error'), JSON.stringify(fallbackState));
    // A user's system sans can itself resolve to Inter. Compare with the real
    // fallback stack, instead of pretending its PostScript name is universal.
    await page.evaluate(() => {
      const reference = document.createElement('p'); reference.id = 'fallback-reference';
      reference.textContent = document.querySelector('#face-regular').textContent;
      reference.style.fontFamily = 'system-ui, "Segoe UI", sans-serif';
      document.body.append(reference);
    });
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const { nodeId: referenceId } = await session.send('DOM.querySelector', { nodeId: document.nodeId, selector: '#fallback-reference' });
    const { fonts: referenceFonts } = await session.send('CSS.getPlatformFontsForNode', { nodeId: referenceId });
    const identities = list => list.map(({ familyName, postScriptName, isCustomFont }) => ({ familyName, postScriptName, isCustomFont }));
    assert.deepEqual(identities(fonts), identities(referenceFonts));
    results.fonts.missingLocalFallback = { fonts, aliasStates: fallbackState.faces, comparedWithSystemFallback: true };
    assert.ok(network.every(url => url.startsWith(origin + '/')));
  } finally { await context.close(); }
});

test('keyboard, enlarged text, reduced motion and forced colors retain usable controls', async () => {
  const { context, page } = await pageFor({ viewport: { width: 390, height: 844 }, reducedMotion: 'reduce' });
  try {
    await page.keyboard.press('Tab');
    assert.equal(await page.locator(':focus').textContent(), 'Skip to content');
    await page.getByRole('button', { name: 'Clair', exact: true }).focus();
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('html').getAttribute('data-theme'), 'Clair');
    await page.locator('#sample-button').focus();
    await page.keyboard.press('Enter');
    assert.match(await page.locator('#control-status').textContent(), /Control activated/);
    const focus = await page.locator('#sample-button').evaluate(node => getComputedStyle(node).outlineWidth);
    assert.equal(focus, '2px');
    await page.addStyleTag({ content: 'html { font-size: 200%; }' });
    const overflowing = await page.evaluate(() => [...document.querySelectorAll('body *')].filter(n => n.getBoundingClientRect().right > innerWidth + 1).map(n => [n.tagName, n.className, n.getBoundingClientRect().right]));
    assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), JSON.stringify(overflowing));
    await page.emulateMedia({ forcedColors: 'active' });
    for (const name of ['Obscur', 'Clair']) {
      await page.getByRole('button', { name, exact: true }).click();
      assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--panel').trim()), 'Canvas');
      for (const palette of await page.locator('[data-palette]').all()) {
        assert.equal(await palette.evaluate(node => getComputedStyle(node).getPropertyValue('--canvas').trim()), 'Canvas');
      }
      assert.equal(await page.locator('#sample-button').isEnabled(), true);
    }
    results.scenarios.push({ name: 'keyboard, 200% text, reduced motion, forced colors', status: 'passed' });
  } finally { await context.close(); }
});

test('download clicks save all platform choices without navigating away', async () => {
  // Separate palette chooser journeys keep the test about deliberate file
  // selection. One context per palette and one for the paired GX candidate
  // keep each journey below Chromium's ordinary ten-download burst threshold.
  // A single rapid seventeen-click burst measures Chromium's download
  // throttle instead. Browser limits and download permissions stay unchanged.
  for (const name of ['Clair', 'Obscur', 'Clair and Obscur']) {
    const { context, page, consoleErrors } = await pageFor({ viewport: { width: name === 'Clair and Obscur' ? 390 : 1280, height: 900 } });
    try {
    const manifest = await (await context.request.get(origin + '/downloads/artifact-manifest.json')).json();
    assert.equal(manifest.downloads.length, 17);
    const choices = manifest.downloads.filter(item => item.name === name);
    assert.equal(choices.length, name === 'Clair and Obscur' ? 1 : 8);
    for (const download of choices) {
      const group = page.locator(`#${download.platform}-downloads`);
      const link = group.locator(`a[download][href="downloads/${download.path}"]`);
      assert.equal(await link.count(), 1);
      let saved;
      try { [saved] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), link.click()]); }
      catch (error) {
        failures.push({ scenario:'download', platform:download.platform, path:download.path, pageUrl:page.url(), error:error.message });
        throw new Error(`${download.platform} ${download.name} download failed (${download.path}): ${error.message}`, { cause:error });
      }
      assert.equal(saved.suggestedFilename(), path.basename(download.path));
      assert.equal(await saved.failure(), null);
      const chunks = [];
      for await (const chunk of await saved.createReadStream()) chunks.push(chunk);
      const bytes = Buffer.concat(chunks);
      assert.equal(page.url(), origin + '/');
      const record = manifest.files.find(file => file.path === download.path);
      assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), record.sha256);
      results.scenarios.push({ name:`${download.name} ${download.platform} download`, status:'passed', path:download.path, sha256:record.sha256 });
      if (['equicord', 'vencord', 'betterdiscord'].includes(download.platform)) {
        const css = await page.evaluate(text => { const sheet = new CSSStyleSheet(); sheet.replaceSync(text); return { rules: sheet.cssRules.length, faces: [...sheet.cssRules].filter(rule => rule.type === CSSRule.FONT_FACE_RULE).length }; }, bytes.toString('utf8'));
        assert.ok(css.rules > 10);
        assert.equal(css.faces, 6);
      }
    }
    const navigation = await page.evaluate(() => {
      const n = performance.getEntriesByType('navigation')[0];
      return { domContentLoadedMs: n.domContentLoadedEventEnd, loadMs: n.loadEventEnd, requests: performance.getEntriesByType('resource').length };
    });
    results.metrics[`previewNavigation${name}`] = { ...navigation, scope: `one local headless ${choices.length}-choice journey, not application startup or comparative performance` };
    assert.deepEqual(consoleErrors, []);
    assert.deepEqual(failures, []);
    } finally { await context.close(); }
  }
});

test('released source stays separate from the current preview snapshot', async () => {
  const { context, page } = await pageFor();
  try {
    const manifest = await (await context.request.get(origin + '/site-manifest.json')).json();
    const releaseBase = `https://github.com/T92T1914/clair-obscur-themes/releases/download/v${manifest.release.version}`;
    assert.equal(await page.locator('#released-source').getAttribute('href'), releaseBase + '/source.zip');
    assert.equal(await page.locator('#released-checksums').getAttribute('href'), releaseBase + '/release-SHA256SUMS');
    assert.equal(await page.locator('#current-source').textContent(), 'Current source snapshot');
    const sourceText = await page.locator('#source-identity').textContent();
    if (manifest.source.revision) {
      assert.ok(sourceText.includes(manifest.source.revision));
      assert.equal(sourceText.includes('with local source changes'), manifest.source.state === 'modified');
    } else {
      assert.ok(sourceText.includes('Revision unavailable'));
      assert.equal(manifest.source.state, 'unavailable');
    }
    const [saved] = await Promise.all([page.waitForEvent('download'), page.locator('#current-source').click()]);
    assert.equal(saved.suggestedFilename(), 'source.zip');
    assert.equal(await saved.failure(), null);
    const chunks = [];
    for await (const chunk of await saved.createReadStream()) chunks.push(chunk);
    const digest = crypto.createHash('sha256').update(Buffer.concat(chunks)).digest('hex');
    assert.equal(digest, manifest.source.sha256);
    assert.equal(await (await context.request.get(origin + '/source-SHA256SUMS')).text(), `${digest}  source.zip\n`);
    results.scenarios.push({ name: 'separate release source links and revision-labeled current source download', status: 'passed', source: manifest.source });
  } finally { await context.close(); }
});

test('static delivery remains usable without JavaScript and internal links resolve', async () => {
  const { context, page, consoleErrors } = await pageFor({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  try {
    await assertIconPngFallback(page);
    assert.equal(await page.locator('#downloads .download-card a[download]').count(), 17);
    assert.ok(await page.locator('#local-package-checker').isHidden());
    assert.match(await page.locator('#downloads .status').textContent(), /preview builds/);
    assert.match(await page.locator('.hero .status').textContent(), /Full native acceptance remains open/);
    const acceptance = page.getByRole('link', { name: 'dated acceptance record', exact: true });
    assert.ok(await acceptance.isVisible());
    assert.equal(await acceptance.getAttribute('href'), 'https://github.com/T92T1914/clair-obscur-themes/blob/main/docs/acceptance.md');
    assert.doesNotMatch(await page.content(), /\{\{[A-Z_]+\}\}/);
    for (const [name, background] of [['Obscur', 'rgb(0, 0, 0)'], ['Clair', 'rgb(255, 255, 255)']]) {
      const card = page.locator(`.palette[data-palette="${name}"]`);
      assert.equal(await card.evaluate(node => getComputedStyle(node).backgroundColor), background);
    }
    const unresolved = await page.evaluate(() => [...document.querySelectorAll('a[href^="#"]')]
      .map(link => link.getAttribute('href').slice(1)).filter(id => !document.getElementById(id)));
    assert.deepEqual(unresolved, []);
    await page.getByRole('link', { name: 'Equibop with Equicord', exact: true }).click();
    assert.equal(new URL(page.url()).hash, '#equicord-downloads');
    assert.ok(await page.locator('#equicord-downloads').isVisible());
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'no-JavaScript palette comparison, grouped downloads and anchor navigation', status: 'passed' });
  } finally { await context.close(); }
});

async function checkIconGallery(page) {
  assert.equal(await page.locator('#icons').getAttribute('aria-labelledby'), 'icons-heading');
  assert.equal(await page.locator('#icons-heading').textContent(), 'Matching app icons');
  assert.equal(await page.locator('#icons-app-heading').textContent(), 'Named apps');
  assert.equal(await page.locator('#icons-function-heading').textContent(), 'General functions');
  assert.equal(await page.locator('#icons [data-icon-kind="app"]').count(), 257);
  assert.equal(await page.locator('#icons [data-icon-kind="function"]').count(), 24);
  assert.equal(await page.locator('#icon-artwork-download').getAttribute('href'), iconArchive);
  assert.equal(await page.locator('#icon-artwork-reading-download').getAttribute('href'), readingIconArchive);
  assert.equal(await page.locator('#icon-artwork-study-learning-download').getAttribute('href'), learningIconArchive);
  assert.equal(await page.locator('#icon-artwork-running-training-download').getAttribute('href'), runningTrainingIconArchive);
  assert.equal(await page.locator('#icon-artwork-weather-download').getAttribute('href'), weatherIconArchive);
  assert.equal(await page.locator('#icon-artwork-finance-download').getAttribute('href'), financeIconArchive);
  assert.equal(await page.locator('#icon-artwork-travel-download').getAttribute('href'), travelIconArchive);
  assert.equal(await page.locator('#icon-artwork-food-order-download').getAttribute('href'), foodOrderIconArchive);
  assert.equal(await page.locator('#icon-artwork-everyday-download').getAttribute('href'), everydayIconArchive);
  assert.equal(await page.locator('#icon-artwork-broad-download').getAttribute('href'), broadIconArchive);
  assert.equal(await page.locator('#icon-artwork-companion-download').getAttribute('href'), companionIconArchive);
  assert.equal(await page.locator('#icon-artwork-monochrome-download').getAttribute('href'), monochromeIconArchive);
  assert.equal(await page.locator('#icon-artwork-previous-download').getAttribute('href'), previousIconArchive);
  assert.equal(await page.locator('#icon-artwork-legacy-download').getAttribute('href'), legacyIconArchive);
  assert.equal(await page.locator('#icon-artwork-third-app-download').getAttribute('href'), thirdAppIconArchive);
  assert.equal(await page.locator('#icon-artwork-second-app-download').getAttribute('href'), secondAppIconArchive);
  assert.equal(await page.locator('#icon-artwork-first-app-download').getAttribute('href'), firstAppIconArchive);
  assert.match(await page.locator('#icon-artwork-first-app-download').textContent(), /preserved 0\.3\.0/);
  assert.match(await page.locator('#icon-artwork-download').textContent(), /0\.17\.0/);
  assert.match(await page.locator('#icon-artwork-running-training-download').textContent(), /preserved 0\.14\.0/);
  assert.match(await page.locator('#icon-artwork-weather-download').textContent(), /preserved 0\.13\.0/);
  assert.match(await page.locator('#icon-artwork-finance-download').textContent(), /preserved 0\.12\.0/);
  assert.match(await page.locator('#icon-artwork-travel-download').textContent(), /preserved 0\.11\.0/);
  assert.match(await page.locator('#icon-artwork-food-order-download').textContent(), /preserved 0\.10\.0/);
  assert.match(await page.locator('#icon-artwork-everyday-download').textContent(), /preserved 0\.9\.0/);
  assert.match(await page.locator('#icon-artwork-broad-download').textContent(), /preserved 0\.8\.0/);
  assert.match(await page.locator('#icon-artwork-companion-download').textContent(), /preserved 0\.7\.0/);
  assert.match(await page.locator('#icon-artwork-monochrome-download').textContent(), /preserved 0\.6\.0/);
  assert.match(await page.locator('#icon-artwork-previous-download').textContent(), /preserved 0\.2\.0/);
  assert.match(await page.locator('#icon-artwork-legacy-download').textContent(), /original 0\.1\.0/);
  assert.equal(await page.locator('#icon-artwork-checksums').getAttribute('href'), 'icons/SVG-SHA256SUMS');
  const cards = await page.locator('#icons article.icon-card').evaluateAll(nodes => Promise.all(nodes.map(async card => {
    const box = card.getBoundingClientRect(), textErrors = [];
    const textNodes = [...card.querySelectorAll('h4, figcaption, p a, p code')];
    for (const node of textNodes) {
      const range = document.createRange(); range.selectNodeContents(node);
      const rects = [...range.getClientRects()].filter(rect => rect.width > 0 && rect.height > 0);
      if (!node.textContent.trim() || !rects.length) textErrors.push('text unavailable: ' + node.tagName);
      for (const rect of rects) {
        if (rect.left < box.left - 1 || rect.right > box.right + 1 || rect.left < -1 || rect.right > innerWidth + 1)
          textErrors.push('text outside card or viewport: ' + node.textContent);
      }
      for (let ancestor = node; ancestor; ancestor = ancestor.parentElement) {
        const style = getComputedStyle(ancestor), bounds = ancestor.getBoundingClientRect();
        if (style.display === 'none' || style.visibility !== 'visible' || Number(style.opacity) === 0)
          textErrors.push('text unavailable: ' + node.textContent);
        for (const rect of rects) {
          if (['hidden', 'clip'].includes(style.overflowX) && (rect.left < bounds.left - 1 || rect.right > bounds.right + 1))
            textErrors.push('text clipped horizontally: ' + node.textContent);
          if (['hidden', 'clip'].includes(style.overflowY) && (rect.top < bounds.top - 1 || rect.bottom > bounds.bottom + 1))
            textErrors.push('text clipped vertically: ' + node.textContent);
        }
      }
    }
    return {
    functionName: card.dataset.iconFunction, label: card.querySelector('h4')?.textContent, kind: card.dataset.iconKind,
    mapping: card.querySelector('p a')?.getAttribute('href'), packageId: card.querySelector('p code')?.textContent,
    textErrors, textNodes: textNodes.length, box: { left: box.left, right: box.right, width: box.width, height: box.height, viewport: innerWidth },
    pairs: card.querySelectorAll('.icon-pair').length,
    figures: await Promise.all([...card.querySelectorAll('.icon-pair figure')].map(async figure => {
      const node = figure.querySelector('img');
      if (!node) return { missingImage: true };
      let decode = true;
      try { await node.decode(); } catch { decode = false; }
      const box = node.getBoundingClientRect(), style = getComputedStyle(node);
      return { path: node.getAttribute('src'), alt: node.getAttribute('alt'), caption: figure.querySelector('figcaption')?.textContent,
        declaredWidth: node.getAttribute('width'), declaredHeight: node.getAttribute('height'),
        decode, naturalWidth: node.naturalWidth, naturalHeight: node.naturalHeight,
        width: box.width, height: box.height, left: box.left, right: box.right, viewport: innerWidth,
        display: style.display, visibility: style.visibility };
    })),
  }; })));
  assert.deepEqual(cards.map(card => card.functionName), iconFunctions);
  const decoded = [];
  for (const card of cards) {
    const functionName = card.functionName;
    const words = iconLabels.get(functionName);
    assert.equal(card.label, words);
    assert.ok(card.box.width > 0 && card.box.height > 0 && card.box.left >= -1 && card.box.right <= card.box.viewport + 1,
      JSON.stringify({ functionName, box: card.box }));
    assert.deepEqual(card.textErrors, [], functionName);
    const app = namedIconApps.find(row => row[0] === functionName);
    assert.equal(card.kind, app ? 'app' : 'function');
    if (app) {
      assert.equal(card.textNodes, 5, 'Named cards expose a heading, two captions, mapping link and package ID');
      assert.equal(card.mapping, appStoreUrl(app[0], app[2]));
      assert.equal(card.packageId, app[2]);
    } else {
      assert.equal(card.textNodes, 3);
      assert.equal(card.mapping, undefined); assert.equal(card.packageId, undefined);
    }
    assert.equal(card.pairs, 1);
    assert.equal(card.figures.length, 2);
    for (const [index, appearance] of ['Clair', 'Obscur'].entries()) {
      const observation = card.figures[index];
      assert.equal(observation.caption, appearance);
      assert.equal(observation.path, `icons/${appearance}/${functionName}.svg`);
      assert.equal(observation.alt, `${appearance} ${words} icon`);
      assert.equal(observation.declaredWidth, '512');
      assert.equal(observation.declaredHeight, '512');
      assert.ok(observation.decode, `Icon not decoded: ${observation.path}`);
      assert.equal(observation.naturalWidth, 512); assert.equal(observation.naturalHeight, 512);
      assert.ok(observation.width > 0 && observation.height > 0, JSON.stringify(observation));
      assert.equal(observation.visibility, 'visible'); assert.notEqual(observation.display, 'none');
      assert.ok(observation.left >= -1 && observation.right <= observation.viewport + 1, JSON.stringify(observation));
      decoded.push(observation.path);
    }
  }
  assert.equal(await page.locator('#downloads .download-card').count(), 17);
  assert.equal(await page.locator('#downloads .guide-link').count(), 18);
  return decoded;
}

const iconHistoryArchives = [
  ['icon-artwork-reading-download', readingIconArchive, readingIconDigest],
  ['icon-artwork-study-learning-download', learningIconArchive, learningIconDigest],
  ['icon-artwork-running-training-download', runningTrainingIconArchive, runningTrainingIconDigest],
  ['icon-artwork-weather-download', weatherIconArchive, weatherIconDigest],
  ['icon-artwork-finance-download', financeIconArchive, financeIconDigest],
  ['icon-artwork-travel-download', travelIconArchive, travelIconDigest],
  ['icon-artwork-food-order-download', foodOrderIconArchive, foodOrderIconDigest],
  ['icon-artwork-everyday-download', everydayIconArchive, everydayIconDigest],
  ['icon-artwork-broad-download', broadIconArchive, broadIconDigest],
  ['icon-artwork-companion-download', companionIconArchive, companionIconDigest],
  ['icon-artwork-monochrome-download', monochromeIconArchive, monochromeIconDigest],
  ['icon-artwork-third-app-download', thirdAppIconArchive, thirdAppIconDigest],
  ['icon-artwork-second-app-download', secondAppIconArchive, secondAppIconDigest],
  ['icon-artwork-first-app-download', firstAppIconArchive, firstAppIconDigest],
  ['icon-artwork-previous-download', previousIconArchive, previousIconDigest],
  ['icon-artwork-legacy-download', legacyIconArchive, legacyIconDigest],
];

async function assertIconHistoryStructure(page, { open } = {}) {
  const structure = await page.evaluate(() => {
    const history = document.querySelector('#icon-history'), summary = document.querySelector('#icon-history-summary');
    const nodes = ['#icon-artwork-download', '#icon-artwork-checksums', '#icon-finder', '#icon-png-help',
      '#icon-png-status', '#icon-history', '#icons .icon-card'].map(selector => document.querySelector(selector));
    return { tag: history?.tagName, summaryTag: summary?.tagName, summaryText: summary?.textContent.trim(),
      summaryIsFirstChild: history?.firstElementChild === summary, open: history?.open,
      outsideCards: Boolean(history && !history.closest('.icon-card')),
      ordered: nodes.every(Boolean) && nodes.slice(1).every((node, index) =>
        Boolean(nodes[index].compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING)),
      links: [...(history?.querySelectorAll('a') || [])].map(node => ({ id: node.id,
        href: node.getAttribute('href'), download: node.hasAttribute('download') })) };
  });
  assert.equal(structure.tag, 'DETAILS'); assert.equal(structure.summaryTag, 'SUMMARY');
  assert.equal(structure.summaryText, 'Preserved SVG collections'); assert.equal(structure.summaryIsFirstChild, true);
  assert.equal(structure.outsideCards, true);
  assert.equal(structure.ordered, true, 'Current acquisition precedes preserved history and the static gallery');
  assert.deepEqual(structure.links, iconHistoryArchives.map(([id, href]) => ({ id, href, download: true })),
    'Preserved archive identities must remain exact');
  if (open !== undefined) assert.equal(structure.open, open, 'Expected native history disclosure state');
  return structure;
}

async function setIconHistoryOpen(page, open, key = 'Enter') {
  const history = page.locator('#icon-history'), summary = page.locator('#icon-history-summary');
  if (await history.evaluate(node => node.open) !== open) {
    await summary.focus(); await page.keyboard.press(key);
    assert.equal(await history.evaluate(node => node.open), open, 'History keyboard toggle must change the native open state');
    assert.equal(await summary.evaluate(node => node === document.activeElement), true, 'History toggle retains summary focus');
  }
}

async function focusBeforeIconCards(page) {
  await setIconHistoryOpen(page, false);
  await (await page.locator('#icon-finder').isVisible() ? page.locator('#icon-clear') : page.locator('#icon-artwork-checksums')).focus();
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-history-summary');
  assert.equal(await page.locator('#icon-history a:visible').count(), 0, 'Closed history must not add archive keyboard stops');
}

async function acquirePreservedIconArchive(page, [id, relative, digest]) {
  const link = page.locator('#' + id);
  assert.equal(await link.evaluate(node => document.activeElement === node), true);
  const beforeUrl = page.url();
  const [download] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), page.keyboard.press('Enter')]);
  assert.equal(await download.failure(), null);
  const chunks = []; for await (const chunk of await download.createReadStream()) chunks.push(chunk);
  const bytes = Buffer.concat(chunks); assert.ok(bytes.length > 0, 'Acquire actual archive bytes before identity checks');
  assert.equal(download.suggestedFilename(), path.basename(relative), 'Preserved archive filename identity');
  assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), digest, 'Preserved archive digest identity');
  assert.deepEqual(bytes, await readFile(path.join(site, relative))); assert.equal(page.url(), beforeUrl);
  return { id, path: relative, bytes: bytes.length, sha256: digest };
}

async function assertIconHistoryLayout(page, { spacing = false } = {}) {
  const metrics = await page.locator('#icon-history summary, #icon-history > p, #icon-history a').evaluateAll(nodes => nodes.map(node => {
    const box = node.getBoundingClientRect(), style = getComputedStyle(node), range = document.createRange();
    range.selectNodeContents(node);
    return { tag: node.tagName, text: node.textContent.trim(), left: box.left, right: box.right, width: box.width, height: box.height,
      viewport: innerWidth, visibility: style.visibility, opacity: style.opacity, fontSize: style.fontSize,
      lineHeight: style.lineHeight, letterSpacing: style.letterSpacing, wordSpacing: style.wordSpacing,
      marginBlockEnd: style.marginBlockEnd, rects: [...range.getClientRects()].map(rect => ({ left: rect.left, right: rect.right,
        top: rect.top, bottom: rect.bottom, width: rect.width, height: rect.height })) };
  }));
  assert.equal(metrics.length, 33, 'Admit the summary, all sixteen archive paragraphs and their actual links');
  for (const node of metrics) {
    assert.ok(node.text && node.width > 0 && node.height > 0 && node.visibility === 'visible' && Number(node.opacity) > 0,
      'History text unavailable: ' + JSON.stringify(node));
    assert.ok(node.left >= -1 && node.right <= node.viewport + 1, 'History outside viewport: ' + JSON.stringify(node));
    assert.ok(node.rects.length > 0 && node.rects.every(rect => rect.width > 0 && rect.height > 0 && rect.left >= -1 && rect.right <= node.viewport + 1),
      'History text clipped: ' + JSON.stringify(node));
    if (!spacing) continue;
    const size = parseFloat(node.fontSize);
    for (const [property, minimum] of [['lineHeight', 1.5], ['letterSpacing', .12], ['wordSpacing', .16]])
      assert.ok(parseFloat(node[property]) + .02 >= size * minimum, 'History spacing admission ' + property + ': ' + JSON.stringify(node));
    if (node.tag === 'P') assert.ok(parseFloat(node.marginBlockEnd) + .02 >= size * 2, 'History paragraph spacing: ' + JSON.stringify(node));
  }
  return { nodes: metrics.length, paragraphs: metrics.filter(node => node.tag === 'P').length, spacing };
}

test('current icon acquisition precedes preserved history with native keyboard disclosure', async () => {
  for (const width of [390, 1280]) {
    const { context, page, consoleErrors } = await pageFor({ viewport: { width, height: 900 } });
    try {
      await snapshotFinderCatalog(page);
      const acquisitions = [];
      for (const appearance of ['Obscur', 'Clair']) {
        await page.getByRole('button', { name: appearance, exact: true }).click();
        await assertIconHistoryStructure(page, { open: false });
        await page.locator('#icon-artwork-download').focus();
        for (const id of ['icon-artwork-checksums', 'icon-query', 'icon-kind', 'icon-clear', 'icon-history-summary']) {
          await page.keyboard.press('Tab');
          assert.equal(await page.evaluate(() => document.activeElement.id), id, 'Current task keyboard order before preserved links');
        }
        assert.equal(await page.locator('#icon-history a:visible').count(), 0);
        await page.locator('#icon-query').fill('weather-channel'); await assertFinderResults(page, ['weather-channel']);
        const surroundings = await iconPngSurroundings(page);
        await setIconHistoryOpen(page, true, 'Enter'); await assertIconHistoryLayout(page);
        for (const [index, item] of iconHistoryArchives.entries()) {
          await page.keyboard.press('Tab');
          assert.equal(await page.evaluate(() => document.activeElement.id), item[0]);
          assert.equal(await page.locator('#' + item[0]).isVisible(), true);
          if (index === 0 || index === iconHistoryArchives.length - 1) acquisitions.push(await acquirePreservedIconArchive(page, item));
        }
        await setIconHistoryOpen(page, false, 'Space');
        await tabToIconAction(page, 'weather-channel', 'Clair', 'com.weather.Weather');
        const png = await acquireIconPng(page, 'weather-channel', appearance);
        acquisitions.push(await assertDownloadedIconPng(page, png, 'weather-channel', appearance));
        assert.deepEqual(await iconPngSurroundings(page), surroundings);
        assert.equal(await page.locator('#icon-history').evaluate(node => node.open), false);
      }
      assert.deepEqual(consoleErrors, []);
      results.scenarios.push({ name: 'current-first icon acquisition and native history disclosure', width, appearances: ['Obscur', 'Clair'],
        historicalLinksReached: 30, acquisitions, status: 'passed', nativePhoneVerified: false });
    } finally { await context.close(); }
  }
});

test('current icon acquisition keeps opened history spacing-only and additional responsive stress distinct', async () => {
  for (const scenario of [{ width: 1280, scale: 100, missingFont: false, spacingOnly: true },
    { width: 390, scale: 100, missingFont: false, spacingOnly: false },
    { width: 320, scale: 200, missingFont: true, spacingOnly: false }]) {
    const { context, page, consoleErrors } = await pageFor({ viewport: { width: scenario.width, height: 844 }, missingFont: scenario.missingFont });
    try {
      if (scenario.scale === 200) await page.addStyleTag({ content: 'html { font-size: 200%; }' });
      await snapshotFinderCatalog(page);
      for (const appearance of ['Obscur', 'Clair']) {
        await page.getByRole('button', { name: appearance, exact: true }).click();
        await setIconHistoryOpen(page, true);
        const baseline = await spacingContentBaseline(page);
        assert.equal(baseline.rootFontSize, scenario.scale === 200 ? '32px' : '16px'); assert.equal(baseline.width, scenario.width);
        const style = await page.addStyleTag({ content: textSpacingOverride });
        const admission = await assertTextSpacing(page, baseline), history = await assertIconHistoryLayout(page, { spacing: true });
        await setIconHistoryOpen(page, false, 'Space'); await setIconHistoryOpen(page, true, 'Enter');
        await page.keyboard.press('Tab');
        const archive = await acquirePreservedIconArchive(page, iconHistoryArchives[0]);
        await page.locator('#icon-query').fill('weather-channel'); await assertFinderResults(page, ['weather-channel']);
        const before = await iconPngSurroundings(page);
        const bytes = await acquireIconPng(page, 'weather-channel', appearance);
        const png = await assertDownloadedIconPng(page, bytes, 'weather-channel', appearance);
        assert.equal(await page.locator('#icon-png-status').innerText(),
          `Prepared Clair-Obscur-0.17.0-${appearance}-weather-channel-512.png. Your browser handles the download.`);
        assert.deepEqual(await iconPngSurroundings(page), before); assert.equal(await page.locator('#icon-history').evaluate(node => node.open), true);
        await page.locator('#icon-clear').focus(); await page.keyboard.press('Enter'); await assertFinderResults(page, iconFunctions);
        await assertTextSpacing(page, baseline); await assertIconHistoryLayout(page, { spacing: true });
        await setIconHistoryOpen(page, false); await style.evaluate(node => node.remove());
        results.scenarios.push({ name: scenario.spacingOnly ? 'current acquisition opened-history spacing only' : 'current acquisition opened-history additional stress',
          ...scenario, appearance, admission, history, archive, png, status: 'passed',
          scope: 'Actual four computed overrides and keyboard operations. Narrow layout/enlarged fallback are separate stress, not native-device or broad WCAG acceptance.' });
      }
      assert.deepEqual(consoleErrors, []);
    } finally { await context.close(); }
  }
});

test('current icon acquisition qualification rejects earlier history, an inert disclosure and an altered archive link', async () => {
  for (const fault of ['history-first', 'inert-disclosure', 'altered-archive-link']) {
    const { context, page, consoleErrors } = await pageFor();
    try {
      await assertIconHistoryStructure(page, { open: false });
      if (fault === 'history-first') {
        await page.evaluate(() => document.querySelector('#icon-finder').before(document.querySelector('#icon-history')));
        assert.equal(await page.locator('#icon-history').evaluate(node => Boolean(node.compareDocumentPosition(document.querySelector('#icon-finder')) & Node.DOCUMENT_POSITION_FOLLOWING)), true);
        await assert.rejects(assertIconHistoryStructure(page), /Current acquisition precedes preserved history/);
      } else if (fault === 'inert-disclosure') {
        await page.locator('#icon-history-summary').evaluate(node => {
          window.preventedHistoryToggles = 0;
          node.addEventListener('click', event => { event.preventDefault(); window.preventedHistoryToggles++; });
        });
        for (const key of ['Enter', 'Space']) await assert.rejects(setIconHistoryOpen(page, true, key), /History keyboard toggle/);
        assert.equal(await page.evaluate(() => window.preventedHistoryToggles), 2);
        assert.equal(await page.locator('#icon-history').evaluate(node => node.open), false);
      } else {
        const firstHistoryLink = page.locator('#' + iconHistoryArchives[0][0]);
        await firstHistoryLink.evaluate(node => node.setAttribute('href', 'icons/Clair-Obscur-SVG-Icons-0.1.0.zip'));
        assert.equal(await firstHistoryLink.getAttribute('href'), legacyIconArchive);
        await assert.rejects(assertIconHistoryStructure(page), /Preserved archive identities/);
        await setIconHistoryOpen(page, true); await page.keyboard.press('Tab');
        await assert.rejects(acquirePreservedIconArchive(page, iconHistoryArchives[0]), /Preserved archive filename identity/);
      }
      assert.deepEqual(consoleErrors, []);
      results.scenarios.push({ name: 'current acquisition controlled qualification failure', fault, status: 'rejected as expected',
        scope: 'Deliberate fault in a disposable page, not a product defect or modified deliverable' });
    } finally { await context.close(); }
  }
});

async function checkIconMappingKeyboard(page) {
  // Traverse the closed history summary before the gallery in either mode.
  // Historical links remain available through its separate keyboard journey.
  await focusBeforeIconCards(page);
  const pngEnabled = await page.locator('[data-icon-png]').first().isVisible();
  for (const [id, , packageId] of namedIconApps) {
    for (const action of pngEnabled ? ['Clair', 'Obscur', 'store'] : ['store'])
      await tabToIconAction(page, id, action, packageId);
  }
  return { keyboardReachable: namedIconApps.length, pngActionsReached: pngEnabled ? namedIconApps.length * 2 : 0,
    scope: 'Exact official href, PNG metadata and actual Tab focus; store page and installation unexecuted' };
}

async function tabToIconAction(page, id, action, packageId) {
  await page.keyboard.press('Tab');
  const active = await page.evaluate(() => {
    const node = document.activeElement, box = node.getBoundingClientRect();
    return { id: node.closest('[data-icon-function]')?.dataset.iconFunction, href: node.getAttribute('href'),
      tag: node.tagName, appearance: node.dataset.iconAppearance, filename: node.dataset.iconFilename,
      png: node.hasAttribute('data-icon-png'), text: node.textContent, focused: node.matches(':focus'),
      left: box.left, right: box.right, top: box.top, bottom: box.bottom, width: innerWidth, height: innerHeight };
  });
  assert.equal(active.id, id); assert.equal(active.focused, true);
  if (action === 'store') {
    assert.equal(active.href, appStoreUrl(id, packageId));
    assert.equal(active.text, galaxyIconIds.has(id) ? 'Galaxy Store listing' : 'Google Play listing');
  } else {
    assert.equal(active.tag, 'BUTTON'); assert.equal(active.png, true);
    assert.equal(active.appearance, action);
    assert.equal(active.filename, `Clair-Obscur-0.17.0-${action}-${id}-512.png`);
  }
  assert.ok(active.left >= -1 && active.right <= active.width + 1 && active.bottom > 0 && active.top < active.height,
    JSON.stringify(active));
}

// The full inventory above and the literal subsets below are independent of
// the production matcher. Retain node identity as well as visible result text.
async function snapshotFinderCatalog(page) {
  await page.evaluate(() => {
    window.finderOriginalCards = [...document.querySelectorAll('#icons article.icon-card')]
      .map(node => ({ node, html: node.innerHTML }));
  });
}

async function assertFinderResults(page, expected, { enhanced = true } = {}) {
  const state = await page.evaluate(() => {
    const cards = [...document.querySelectorAll('#icons article.icon-card')];
    const visible = cards.filter(node => node.getClientRects().length && getComputedStyle(node).visibility === 'visible');
    const originals = window.finderOriginalCards;
    return { ids: visible.map(node => node.dataset.iconFunction), allIds: cards.map(node => node.dataset.iconFunction),
      retained: originals && cards.length === originals.length && cards.every((node, index) =>
        node === originals[index].node && node.innerHTML === originals[index].html),
      hidden: cards.filter(node => node.hidden).map(node => node.dataset.iconFunction),
      pairs: visible.map(node => ({ id: node.dataset.iconFunction,
        captions: [...node.querySelectorAll('figcaption')].map(caption => caption.textContent),
        images: [...node.querySelectorAll('img')].map(image => ({ path: image.getAttribute('src'),
          width: image.getBoundingClientRect().width, height: image.getBoundingClientRect().height,
          complete: image.complete, naturalWidth: image.naturalWidth })) })),
      groups: ['app', 'function'].map(kind => {
        const section = document.getElementById('icons-' + kind + '-heading').parentElement;
        return { kind, hidden: section.hidden, visible: Boolean(section.getClientRects().length) };
      }) };
  });
  assert.deepEqual(state.ids, expected, 'Finder must expose independently expected choices in original order');
  assert.deepEqual(state.allIds, iconFunctions, 'Filtering must retain every original card');
  assert.equal(state.retained, true, 'Filtering must retain nodes, artwork, labels and assignment contents');
  if (enhanced) {
    assert.deepEqual(state.hidden, iconFunctions.filter(id => !expected.includes(id)), 'Nonmatches must be hidden rather than transparent or focusable');
    assert.equal(await page.locator('#icon-filter-status').innerText(), 'Showing ' + expected.length + ' of 281 choices.');
    assert.equal(await page.locator('#icon-filter-empty').isVisible(), expected.length === 0);
    for (const group of state.groups) {
      const hasResults = expected.some(id => generalIconFunctions.includes(id) === (group.kind === 'function'));
      assert.equal(group.hidden, !hasResults); assert.equal(group.visible, hasResults);
    }
  } else assert.deepEqual(state.hidden, [], 'Failed enhancement must retain the complete static gallery');
  for (const pair of state.pairs) {
    assert.deepEqual(pair.captions, ['Clair', 'Obscur']); assert.equal(pair.images.length, 2);
    for (const [index, appearance] of ['Clair', 'Obscur'].entries()) {
      const image = pair.images[index];
      assert.equal(image.path, 'icons/' + appearance + '/' + pair.id + '.svg');
      assert.ok(image.width > 0 && image.height > 0, pair.id + ' paired artwork is hidden');
      assert.equal(image.complete, true); assert.equal(image.naturalWidth, 512);
    }
  }
  return { visible: state.ids, originalNodesRetained: state.retained, pairedAppearances: true };
}

async function assertFinderControlLayout(page, { spacing = false } = {}) {
  const state = await page.evaluate(() => ({ width: innerWidth, pageWidth: document.documentElement.scrollWidth,
    controls: [...document.querySelectorAll('#icon-finder label, #icon-query, #icon-kind, #icon-clear, #icon-filter-status, #icon-filter-empty')]
      .filter(node => node.getClientRects().length).map(node => {
        const style = getComputedStyle(node), box = node.getBoundingClientRect(), textRects = [];
        for (const child of node.childNodes) if (child.nodeType === Node.TEXT_NODE && child.textContent.trim()) {
          const range = document.createRange(); range.selectNodeContents(child);
          textRects.push(...[...range.getClientRects()].map(rect => ({ left: rect.left, right: rect.right, width: rect.width, height: rect.height })));
        }
        return { id: node.id || node.tagName + ':' + node.textContent.trim(), tag: node.tagName, text: node.textContent.trim(),
          visibility: style.visibility, opacity: style.opacity, left: box.left, right: box.right, width: box.width, height: box.height,
          textRects, fontSize: style.fontSize, lineHeight: style.lineHeight, letterSpacing: style.letterSpacing,
          wordSpacing: style.wordSpacing, marginBlockEnd: style.marginBlockEnd };
      }) }));
  assert.ok(state.pageWidth <= state.width + 1, JSON.stringify(state));
  const nativeSelect = [];
  for (const control of state.controls) {
    assert.equal(control.visibility, 'visible'); assert.ok(Number(control.opacity) > 0);
    assert.ok(control.width > 0 && control.height > 0 && control.left >= -1 && control.right <= state.width + 1, JSON.stringify(control));
    if (['INPUT', 'SELECT', 'BUTTON'].includes(control.tag)) assert.ok(control.height >= 44, JSON.stringify(control));
    else assert.ok(control.textRects.length > 0, 'Finder text unavailable: ' + control.id);
    for (const rect of control.textRects) assert.ok(rect.width > 0 && rect.height > 0 && rect.left >= control.left - 1 && rect.right <= control.right + 1,
      'Finder text clipped: ' + JSON.stringify(control));
    if (!spacing) continue;
    const size = parseFloat(control.fontSize);
    for (const [property, minimum] of [['lineHeight', 1.5], ['letterSpacing', .12], ['wordSpacing', .16]]) {
      if (control.tag === 'SELECT' && property === 'lineHeight' && control.lineHeight === 'normal')
        nativeSelect.push({ id: control.id, computed: 'normal', scope: 'Native select metric remains unverified, not admitted as 1.5' });
      else assert.ok(parseFloat(control[property]) + .02 >= size * minimum, 'Finder spacing admission ' + property + ': ' + JSON.stringify(control));
    }
    if (control.tag === 'P') assert.ok(parseFloat(control.marginBlockEnd) + .02 >= size * 2, 'Finder paragraph spacing: ' + control.id);
  }
  return { ...state, nativeSelect };
}

async function finderKeyboardRecovery(page) {
  const query = page.locator('#icon-query');
  await query.fill('home'); await assertFinderResults(page, ['home-depot', 'google-home', 'gaming-hub', 'asus-router', 'home']);
  assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-query');
  await page.keyboard.press('Tab'); assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-kind');
  await page.keyboard.press('Home'); await page.keyboard.press('ArrowDown'); await page.keyboard.press('Tab');
  assert.equal(await page.locator('#icon-kind').inputValue(), 'app');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-clear');
  await assertFinderResults(page, ['home-depot', 'google-home', 'gaming-hub', 'asus-router']);
  await focusBeforeIconCards(page);
  const pngEnabled = await page.locator('[data-icon-function="home-depot"] [data-icon-png]').first().isVisible();
  for (const [id, packageId] of [['home-depot', 'com.thehomedepot'], ['google-home', 'com.google.android.apps.chromecast.app'], ['gaming-hub', 'com.samsung.android.game.gamehome'], ['asus-router', 'com.asus.aihome']]) {
    for (const action of pngEnabled ? ['Clair', 'Obscur', 'store'] : ['store'])
      await tabToIconAction(page, id, action, packageId);
  }
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement.closest('[data-icon-function]')?.dataset.iconFunction ?? null), null);
  await page.locator('#icon-kind').focus(); await page.keyboard.press('Home');
  await page.keyboard.press('ArrowDown'); await page.keyboard.press('ArrowDown'); await page.keyboard.press('Tab');
  assert.equal(await page.locator('#icon-kind').inputValue(), 'function'); await assertFinderResults(page, ['home']);
  await page.keyboard.press('Enter');
  assert.equal(await query.inputValue(), ''); assert.equal(await page.locator('#icon-kind').inputValue(), 'all');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-query'); await assertFinderResults(page, iconFunctions);
  return { visibleStoreLinksReachedByTab: 4, visiblePngActionsReachedByTab: pngEnabled ? 8 : 0,
    appAndFunctionKinds: true, clearRestoredAllAndFocusedQuery: true };
}

test('icon finder matches labels, stable IDs and packages literally in both appearances and phone layouts', async () => {
  const cases = [
    // Google Home also matches "chrome" in its documented chromecast package ID.
    ['  \t  ', iconFunctions], ['  gOoGlE  ChRoMe  ', ['google-chrome', 'google-home']], ['maps google', ['google-maps']], ['google maps', ['google-maps']],
    ['  tasks\tgoogle  ', ['google-tasks']], ['COM.FITBIT.FITBITMOBILE', ['fitbit']], ['Google Health', ['fitbit']],
    ['voice-recorder', ['voice-recorder']], ['cLáUdE', ['claude']],
    ["McDonald's", ['mcdonalds']], ['McDonald’s', ['mcdonalds']], ['mcdonalds', ['mcdonalds']],
    ['Wendy’s', ['wendys']], ['DOMINOS', ['dominos']], ['com.kfc.us.mobile', ['kfc-us']],
    ['com.kfc.mobile', []], ['panera bread', ['panera-bread']],
    ['Bank of America', ['bank-of-america']], ['com.wf.wellsfargomobile', ['wells-fargo']],
    ['U.S. Bank', ['us-bank']], ['com.pnc.ecommerce.mobile', ['pnc']],
    ['Discover', ['discover']], ['com.discoverfinancial.mobile', ['discover']],
    ['com.konylabs.capitalone', ['capital-one']], ['Amex', ['amex']],
    ['Fidelity Investments', ['fidelity-investments']], ['com.schwab.mobile', ['schwab']],
    ['SoFi', ['sofi']], ['Robinhood', ['robinhood']],
    ['com.discoverfinancial.mobile capital one', []],
    ['AccuWeather', ['accuweather']], ['com.accuweather.android', ['accuweather']],
    ['The Weather Channel', ['weather-channel']], ['com.weather.Weather', ['weather-channel']],
    ['Weather Underground', ['weather-underground']], ['com.wunderground.android.weather', ['weather-underground']],
    ['Windy.com', ['windy-com']], ['com.windyty.android', ['windy-com']], ['Windy.app', []],
    ['MyRadar', ['myradar']], ['com.acmeaom.android.myradar', ['myradar']],
    ['WeatherBug', ['weatherbug']], ['com.aws.android', ['weatherbug']],
    ['1Weather', ['one-weather']], ['com.handmark.expressweather', ['one-weather']],
    ['Clime', ['clime']], ['com.apalon.weatherradar.free', ['clime']],
    ['Windfinder', ['windfinder']], ['com.studioeleven.windfinder', ['windfinder']],
    ['RainViewer', ['rainviewer']], ['com.lucky_apps.RainViewer', ['rainviewer']],
    ['Nike Run Club', ['nike-run-club']], ['com.nike.plusgps', ['nike-run-club']],
    ['adidas Running', ['adidas-running']], ['com.runtastic.android', ['adidas-running']],
    ['ASICS Runkeeper', ['asics-runkeeper']], ['com.fitnesskeeper.runkeeper.pro', ['asics-runkeeper']],
    ['Map My Run', ['map-my-run']], ['com.mapmyrun.android2', ['map-my-run']],
    ['Runna', ['runna']], ['com.runbuddy.prod', ['runna']],
    ['TrainingPeaks', ['trainingpeaks']], ['com.peaksware.trainingpeaks', ['trainingpeaks']],
    ...learningIconApps.flatMap(([id, label, packageId]) => [[label, [id]], [packageId, [id]]]),
    ...readingIconApps.flatMap(([id, label, packageId]) => [[label, [id]], [packageId, [id]]]),
    ...phoneServiceApps.map(([id, , packageId]) => [packageId, [id]]),
    ['Proton', ['proton-mail', 'proton-authenticator', 'proton-vpn', 'proton-pass']],
    ['Steam', ['steam', 'steam-chat']], ['Steam Chat', ['steam-chat']],
    ['Samsung Pass', ['samsung-pass']], ['Credit One', ['credit-one']], ['USAA', ['usaa']],
    ['Zillow', ['zillow', 'zillow-rentals']], ['com.fandom.fandomapp', []], ['Galaxy Store listing', []],
    ['Zwift Companion', ['zwift-companion']], ['com.zwift.android.prod', ['zwift-companion']],
    ['Relive', ['relive']], ['cc.relive.reliveapp', ['relive']],
    ['com.runbuddy.prod com.strava', []],
    ['Fly Delta', ['fly-delta']], ['United Airlines', ['united-airlines']],
    ['American Airlines', ['american-airlines']], ['Southwest Airlines', ['southwest-airlines']],
    ['airlines', ['united-airlines', 'american-airlines', 'southwest-airlines']],
    ['transit', ['transit']], ['com.tranzmate', ['moovit']], ['citymapper', ['citymapper']],
    ['subway', ['subway']], ['com.thetransitapp.droid', ['transit']], ['tripit', ['tripit']],
    ['microsoft office', ['outlook', 'microsoft-word', 'microsoft-excel', 'microsoft-powerpoint', 'microsoft-copilot']],
    ['office microsoft', ['outlook', 'microsoft-word', 'microsoft-excel', 'microsoft-powerpoint', 'microsoft-copilot']],
    ['mail', ['gmail', 'proton-mail', 'yahoo-mail', 'mail']], ['Clair', []], ['Google Play listing', []],
    ['this app does not exist 8675309', []], ['^(Google|Apple).*', []], ['[', []],
    ['<img src=x onerror="window.finderInjected=true">', []],
  ];
  for (const width of [390, 1280]) {
    const { context, page, consoleErrors } = await pageFor({ viewport: { width, height: 844 } });
    try {
      await snapshotFinderCatalog(page);
      const form = page.getByRole('search', { name: 'Find an icon', exact: true });
      assert.equal(await form.getAttribute('id'), 'icon-finder'); assert.ok(await form.isVisible());
      const searchbox = page.getByRole('searchbox', { name: 'Find an icon', exact: true });
      assert.equal(await searchbox.getAttribute('id'), 'icon-query');
      assert.equal(await searchbox.getAttribute('type'), 'search');
      assert.equal(await page.getByRole('combobox', { name: 'Icon type', exact: true }).getAttribute('id'), 'icon-kind');
      assert.deepEqual(await page.locator('#icon-kind option').evaluateAll(nodes => nodes.map(node => node.value)), ['all', 'app', 'function']);
      const status = page.locator('#icon-filter-status');
      assert.equal(await status.getAttribute('role'), 'status'); assert.equal(await status.getAttribute('aria-live'), 'polite');
      assert.equal(await status.getAttribute('aria-atomic'), 'true'); await assertFinderResults(page, iconFunctions);
      for (const appearance of ['Obscur', 'Clair']) {
        await page.getByRole('button', { name: appearance, exact: true }).click();
        for (const [query, expected] of cases) {
          await page.locator('#icon-query').fill(query); await assertFinderResults(page, expected);
          assert.equal(await page.locator('#icon-query').inputValue(), query);
          assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-query');
        }
        assert.equal(await page.evaluate(() => window.finderInjected), undefined);
        assert.equal(await page.locator('#icon-finder img').count(), 0, 'Literal query markup must never become HTML');
        await page.locator('#icon-query').fill('claude');
        const before = { url: page.url(), timeOrigin: await page.evaluate(() => performance.timeOrigin) };
        await page.keyboard.press('Enter'); await assertFinderResults(page, ['claude']);
        assert.equal(page.url(), before.url); assert.equal(await page.evaluate(() => performance.timeOrigin), before.timeOrigin);
        await page.getByRole('button', { name: appearance === 'Clair' ? 'Obscur' : 'Clair', exact: true }).click();
        assert.equal(await page.locator('#icon-query').inputValue(), 'claude'); await assertFinderResults(page, ['claude']);
        await page.locator('#icon-kind').selectOption('function'); await assertFinderResults(page, []);
        assert.match(await page.locator('#icon-filter-empty').innerText(), /clear|different|another/i);
        await page.getByRole('button', { name: 'Clear filters', exact: true }).click(); await assertFinderResults(page, iconFunctions);
        assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-query');
        await page.locator('#icon-kind').selectOption('app'); await assertFinderResults(page, namedIconApps.map(row => row[0]));
        await page.locator('#icon-kind').selectOption('function'); await assertFinderResults(page, generalIconFunctions);
        await page.locator('#icon-kind').selectOption('all'); await assertFinderResults(page, iconFunctions);
        await assertFinderControlLayout(page);
      }
      const keyboard = await finderKeyboardRecovery(page); assert.deepEqual(consoleErrors, []);
      results.scenarios.push({ name: 'literal icon finder and keyboard recovery', status: 'passed', width, cases: cases.length,
        appearances: ['Clair', 'Obscur'], keyboard, nativePhoneVerified: false });
    } finally { await context.close(); }
  }
});

test('icon finder leaves exact artwork downloads and the independent platform chooser usable', async () => {
  const { context, page, consoleErrors } = await pageFor({ viewport: { width: 390, height: 844 } });
  try {
    await snapshotFinderCatalog(page);
    await page.locator('#package-target').selectOption('equicord'); await page.locator('#package-appearance').selectOption('Clair');
    const chooserBefore = await page.locator('#package-choice-result').innerHTML();
    await page.locator('#icon-query').fill('this app does not exist 8675309'); await assertFinderResults(page, []);
    await setIconHistoryOpen(page, true);
    for (const id of ['icon-artwork-download', 'icon-artwork-reading-download', 'icon-artwork-weather-download', 'icon-artwork-finance-download', 'icon-artwork-travel-download', 'icon-artwork-food-order-download', 'icon-artwork-everyday-download', 'icon-artwork-broad-download', 'icon-artwork-companion-download',
      'icon-artwork-monochrome-download', 'icon-artwork-third-app-download', 'icon-artwork-second-app-download',
      'icon-artwork-first-app-download', 'icon-artwork-previous-download', 'icon-artwork-legacy-download', 'icon-artwork-checksums'])
      assert.ok(await page.locator('#' + id).isVisible(), 'Filtering hid a download: ' + id);
    await page.getByRole('button', { name: 'Obscur', exact: true }).click();
    assert.equal(await page.locator('#package-choice-result').innerHTML(), chooserBefore);
    assert.equal(await page.locator('#package-target').inputValue(), 'equicord');
    assert.equal(await page.locator('#package-appearance').inputValue(), 'Clair');
    assert.equal(await page.locator('#package-choice-file').getAttribute('href'), 'downloads/equicord/Clair-Equicord-0.1.2.theme.css');
    const beforeUrl = page.url(); await page.locator('#icon-artwork-download').focus();
    const [download] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), page.keyboard.press('Enter')]);
    assert.equal(await download.failure(), null); assert.equal(download.suggestedFilename(), path.basename(iconArchive));
    const chunks = []; for await (const chunk of await download.createReadStream()) chunks.push(chunk);
    const expectedBytes = await readFile(path.join(site, iconArchive)), actualBytes = Buffer.concat(chunks);
    assert.deepEqual(actualBytes, expectedBytes); assert.equal(page.url(), beforeUrl);
    const digest = crypto.createHash('sha256').update(actualBytes).digest('hex');
    assert.ok((await readFile(path.join(site, 'icons/SVG-SHA256SUMS'), 'utf8')).includes(digest + '  ' + path.basename(iconArchive) + '\n'));
    await page.locator('#icon-query').fill('claude'); await assertFinderResults(page, ['claude']);
    const assignmentUrl = 'https://play.google.com/store/apps/details?id=com.anthropic.claude';
    const interceptedAssignments = [];
    // Exercise the actual result anchor without contacting the store.
    await page.route(url => url.href === assignmentUrl, async route => {
      interceptedAssignments.push({ url: route.request().url(), method: route.request().method() });
      await route.fulfill({ contentType: 'text/html; charset=utf-8',
        body: '<!doctype html><title>Assignment fixture</title><h1>Claude assignment fixture</h1>' });
    });
    await focusBeforeIconCards(page);
    for (const action of ['Clair', 'Obscur', 'store']) await tabToIconAction(page, 'claude', action, 'com.anthropic.claude');
    assert.equal(await page.evaluate(() => document.activeElement.closest('[data-icon-function]')?.dataset.iconFunction), 'claude');
    assert.equal(await page.evaluate(() => document.activeElement.getAttribute('href')), assignmentUrl);
    await Promise.all([page.waitForURL(assignmentUrl), page.keyboard.press('Enter')]);
    assert.equal(page.url(), assignmentUrl);
    assert.equal(await page.getByRole('heading', { name: 'Claude assignment fixture', exact: true }).textContent(), 'Claude assignment fixture');
    assert.deepEqual(interceptedAssignments, [{ url: assignmentUrl, method: 'GET' }]);
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'filtered icon acquisition and independent platform chooser', status: 'passed', sha256: digest,
      resultLinkActivation: { url: assignmentUrl, method: 'keyboard Enter, exact page route fulfilled with an inert local response', externalStoreContacted: false },
      scope: 'Exact browser-consumed SVG ZIP after zero results and actual result-anchor activation against a local fixture; no store, installation or native acceptance' });
  } finally { await context.close(); }
});

test('icon finder spacing-only overrides preserve readable controls and real keyboard operations', async () => {
  const { context, page, consoleErrors } = await pageFor();
  try {
    await snapshotFinderCatalog(page);
    const baseline = await spacingContentBaseline(page);
    assert.equal(baseline.width, 1280); assert.equal(baseline.rootFontSize, '16px');
    await page.addStyleTag({ content: textSpacingOverride });
    const wholePageAdmission = await assertTextSpacing(page, baseline), controls = [];
    for (const appearance of ['Clair', 'Obscur']) {
      await page.getByRole('button', { name: appearance, exact: true }).click();
      controls.push(await assertFinderControlLayout(page, { spacing: true })); await finderKeyboardRecovery(page);
      await page.locator('#icon-query').fill('no matching icon 8675309'); await assertFinderResults(page, []);
      await assertFinderControlLayout(page, { spacing: true });
      await page.locator('#icon-clear').focus(); await page.keyboard.press('Enter'); await assertFinderResults(page, iconFunctions);
    }
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'icon finder spacing only', status: 'passed', wholePageAdmission, controls,
      scope: 'All four applicable overrides at unchanged 1280 px viewport and 16 px root; native select line-height separately labeled' });
  } finally { await context.close(); }
});

test('icon finder narrow enlarged fallback spacing remains a separate additional stress case', async () => {
  const { context, page, consoleErrors } = await pageFor({ viewport: { width: 320, height: 844 }, missingFont: true });
  try {
    await snapshotFinderCatalog(page); await page.addStyleTag({ content: 'html { font-size: 200%; }' });
    const baseline = await spacingContentBaseline(page);
    assert.equal(baseline.width, 320); assert.equal(baseline.rootFontSize, '32px');
    await page.addStyleTag({ content: textSpacingOverride });
    const wholePageAdmission = await assertTextSpacing(page, baseline);
    for (const appearance of ['Clair', 'Obscur']) {
      await page.getByRole('button', { name: appearance, exact: true }).click();
      await assertFinderControlLayout(page, { spacing: true }); await finderKeyboardRecovery(page);
      await page.locator('#icon-query').fill('COM.FITBIT.FITBITMOBILE'); await assertFinderResults(page, ['fitbit']);
      await assertFinderControlLayout(page, { spacing: true });
      await page.locator('#icon-clear').focus(); await page.keyboard.press('Enter');
    }
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'icon finder responsive spacing stress', status: 'passed', width: 320, rootFontSize: '32px', wholePageAdmission,
      scope: 'Combined narrow layout, enlarged root text and unavailable local Inter alias; separate from spacing-only acceptance and browser zoom' });
  } finally { await context.close(); }
});

test('icon finder enhancement failure preserves every static choice and download', async () => {
  for (const failure of ['no-script', 'blocked-script', 'missing-control', 'invalid-record']) {
    const { context, page, consoleErrors } = await pageFor({ javaScriptEnabled: failure !== 'no-script', viewport: { width: 390, height: 844 },
      setup: async (context, page) => {
        if (failure === 'blocked-script') await page.route('**/preview.js', route => route.abort('blockedbyclient'));
        if (failure === 'missing-control' || failure === 'invalid-record') await page.route(origin + '/', async route => {
          const original = await readFile(path.join(site, 'index.html'), 'utf8');
          const from = failure === 'missing-control' ? 'id="icon-query"' : 'data-icon-kind="app"';
          const to = failure === 'missing-control' ? 'id="icon-query-unavailable"' : 'data-icon-kind="unknown"';
          assert.ok(original.includes(from), 'Fallback fault must reach the intended current markup');
          await route.fulfill({ contentType: 'text/html; charset=utf-8', body: original.replace(from, to) });
        });
      } });
    try {
      await snapshotFinderCatalog(page);
      assert.ok(await page.locator('#icon-finder').isHidden(), failure + ' must not expose an inert finder');
      await assertFinderResults(page, iconFunctions, { enhanced: false });
      await setIconHistoryOpen(page, true);
      assert.deepEqual(await page.locator('#icons article.icon-card p a').evaluateAll(nodes => nodes.map(node => ({
        id: node.closest('[data-icon-function]').dataset.iconFunction, href: node.getAttribute('href') }))),
      namedIconApps.map(([id, , packageId]) => ({ id, href: appStoreUrl(id, packageId) })));
      for (const id of ['icon-artwork-download', 'icon-artwork-reading-download', 'icon-artwork-weather-download', 'icon-artwork-finance-download', 'icon-artwork-travel-download', 'icon-artwork-food-order-download', 'icon-artwork-everyday-download', 'icon-artwork-broad-download', 'icon-artwork-companion-download',
        'icon-artwork-monochrome-download', 'icon-artwork-third-app-download', 'icon-artwork-second-app-download',
        'icon-artwork-first-app-download', 'icon-artwork-previous-download', 'icon-artwork-legacy-download']) assert.ok(await page.locator('#' + id).isVisible());
      if (failure === 'missing-control' || failure === 'invalid-record') {
        await page.locator('#sample-button').click(); assert.match(await page.locator('#control-status').innerText(), /Control activated/);
        assert.deepEqual(consoleErrors, [], 'Failed finder admission must not break unrelated enhancement');
      }
      results.scenarios.push({ name: 'icon finder static fallback', failure, status: 'passed', retainedChoices: 281, retainedMappings: 257,
        scope: 'Isolated fixture initialization fault or script absence, not a product defect' });
    } finally { await context.close(); }
  }
});

test('icon finder qualification rejects an initialized but inert query control', async () => {
  const { context, page, consoleErrors } = await pageFor({ setup: async (context, page) => {
    await page.route('**/preview.js', async route => {
      const original = await readFile(path.join(site, 'preview.js'), 'utf8');
      const listener = "query.addEventListener('input', updateIconFilter);";
      assert.equal(original.split(listener).length - 1, 1, 'Fault must target exactly the current finder input listener');
      await route.fulfill({ contentType: 'text/javascript', body: original.replace(listener, '/* disposable inert-query fault */') });
    });
  } });
  try {
    await snapshotFinderCatalog(page); assert.ok(await page.locator('#icon-finder').isVisible());
    await assertFinderResults(page, iconFunctions); await page.locator('#icon-query').fill('claude');
    await assert.rejects(assertFinderResults(page, ['claude']), /Finder must expose independently expected choices/);
    assert.equal(await page.locator('#icon-query').inputValue(), 'claude'); assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'icon finder controlled operation failure', fault: 'input listener removed after valid initialization',
      status: 'rejected as expected', scope: 'Disposable browser response fault, not a product defect' });
  } finally { await context.close(); }
});

const iconPngButton = (page, id, appearance) => page.locator(
  `[data-icon-function="${id}"] button[data-icon-png][data-icon-appearance="${appearance}"]`);

// Decode the downloaded bytes in Node, independently of the page's canvas code.
function decodeIconPng(bytes) {
  assert.deepEqual([...bytes.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
  const crc32 = data => {
    let crc = 0xffffffff;
    for (const value of data) {
      crc ^= value;
      for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
    }
    return (crc ^ 0xffffffff) >>> 0;
  };
  const compressed = [];
  let offset = 8, header = false, end = false;
  while (offset < bytes.length) {
    const length = bytes.readUInt32BE(offset), kind = bytes.toString('ascii', offset + 4, offset + 8);
    assert.ok(offset + 12 + length <= bytes.length, 'Complete PNG chunk');
    assert.equal(crc32(bytes.subarray(offset + 4, offset + 8 + length)), bytes.readUInt32BE(offset + 8 + length));
    const data = bytes.subarray(offset + 8, offset + 8 + length);
    if (kind === 'IHDR') {
      assert.equal(header, false); header = true;
      assert.equal(length, 13); assert.equal(data.readUInt32BE(0), 512); assert.equal(data.readUInt32BE(4), 512);
      assert.deepEqual([...data.subarray(8)], [8, 6, 0, 0, 0], '512 px, 8-bit noninterlaced RGBA');
    } else if (kind === 'IDAT') compressed.push(data);
    else if (kind === 'IEND') { assert.equal(length, 0); end = true; }
    offset += length + 12;
    if (end) break;
  }
  assert.ok(header && end && compressed.length); assert.equal(offset, bytes.length);
  const stride = 512 * 4, raw = inflateSync(Buffer.concat(compressed), { maxOutputLength: (stride + 1) * 512 });
  assert.equal(raw.length, (stride + 1) * 512);
  const rgba = Buffer.alloc(stride * 512);
  const paeth = (a, b, c) => {
    const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
    return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
  };
  for (let y = 0; y < 512; y++) {
    const filter = raw[y * (stride + 1)]; assert.ok(filter <= 4);
    for (let x = 0; x < stride; x++) {
      const index = y * stride + x, left = x >= 4 ? rgba[index - 4] : 0;
      const above = y ? rgba[index - stride] : 0, corner = y && x >= 4 ? rgba[index - stride - 4] : 0;
      const prediction = filter === 0 ? 0 : filter === 1 ? left : filter === 2 ? above :
        filter === 3 ? Math.floor((left + above) / 2) : paeth(left, above, corner);
      rgba[index] = (raw[y * (stride + 1) + x + 1] + prediction) & 255;
    }
  }
  return rgba;
}

async function assertDownloadedIconPng(page, bytes, id, appearance) {
  const rgba = decodeIconPng(bytes), counts = { panel: 0, glyph: 0, transparent: 0 };
  const panel = appearance === 'Clair' ? 255 : 0, glyph = 255 - panel;
  for (let y = 0; y < 512; y++) for (let x = 0; x < 512; x++) {
    const index = (y * 512 + x) * 4, [red, green, blue, alpha] = rgba.subarray(index, index + 4);
    if (!alpha) counts.transparent++;
    else { assert.equal(red, green, 'Neutral red/green'); assert.equal(green, blue, 'Neutral green/blue'); }
    if (x < 32 || y < 32 || x >= 480 || y >= 480) assert.equal(alpha, 0, 'Transparent 32 px outer margin');
    if (alpha === 255 && red === panel) counts.panel++;
    if (alpha === 255 && red === glyph) counts.glyph++;
  }
  // Select a literal source file from the independent requested identity, never
  // the button metadata, clicked DOM image, handler result or a downloaded name.
  const source = await readFile(path.join(site, 'icons', appearance, id + '.svg'));
  const expected = await page.evaluate(async source64 => {
    const image = new Image(); image.src = 'data:image/svg+xml;base64,' + source64; await image.decode();
    const canvas = document.createElement('canvas'); canvas.width = canvas.height = 512;
    const context = canvas.getContext('2d'); context.drawImage(image, 0, 0, 512, 512);
    const pixels = context.getImageData(0, 0, 512, 512).data;
    return [...new Uint8Array(await crypto.subtle.digest('SHA-256', pixels))]
      .map(byte => byte.toString(16).padStart(2, '0')).join('');
  }, source.toString('base64'));
  const actual = crypto.createHash('sha256').update(rgba).digest('hex');
  assert.equal(actual, expected, 'Downloaded PNG must match the independently selected icon and appearance');
  assert.ok(counts.panel > 10000 && counts.glyph > 100 && counts.transparent > 10000, JSON.stringify(counts));
  return { id, appearance, size: 512, pngSha256: crypto.createHash('sha256').update(bytes).digest('hex'), rgbaSha256: actual, counts };
}

async function acquireIconPng(page, id, appearance, { timeout = 5000 } = {}) {
  const button = iconPngButton(page, id, appearance);
  assert.ok(await button.isVisible()); assert.notEqual(await button.getAttribute('aria-disabled'), 'true');
  await button.focus();
  let download;
  try {
    [download] = await Promise.all([page.waitForEvent('download', { timeout }), page.keyboard.press('Enter')]);
  } catch (error) {
    let observation;
    try {
      observation = await page.evaluate(({ id, appearance }) => {
        const button = document.querySelector(
          `[data-icon-function="${id}"] [data-icon-png][data-icon-appearance="${appearance}"]`);
        const image = button?.closest('figure')?.querySelector('img');
        return { readyState: document.readyState, focused: button === document.activeElement,
          button: button && { hidden: button.hidden, disabled: button.disabled, ariaDisabled: button.getAttribute('aria-disabled') },
          image: image && { complete: image.complete, width: image.naturalWidth, height: image.naturalHeight, currentSrc: image.currentSrc },
          status: document.querySelector('#icon-png-status')?.textContent };
      }, { id, appearance });
    } catch (diagnosticError) { observation = { unavailable: diagnosticError.name }; }
    error.message += '\nPNG acquisition state: ' + JSON.stringify(observation);
    throw error;
  }
  assert.equal(download.suggestedFilename(), `Clair-Obscur-0.17.0-${appearance}-${id}-512.png`);
  assert.equal(await download.failure(), null);
  const chunks = []; for await (const chunk of await download.createReadStream()) chunks.push(chunk);
  await page.waitForFunction(({ id, appearance }) => document.querySelector(
    `[data-icon-function="${id}"] [data-icon-png][data-icon-appearance="${appearance}"]`).getAttribute('aria-disabled') !== 'true', { id, appearance });
  return Buffer.concat(chunks);
}

async function iconPngSurroundings(page) {
  return page.evaluate(() => ({ url: location.href, appearance: document.documentElement.dataset.theme,
    pageSwitches: [...document.querySelectorAll('[data-appearance]')].map(node => [node.dataset.appearance, node.getAttribute('aria-pressed')]),
    query: document.querySelector('#icon-query').value, kind: document.querySelector('#icon-kind').value,
    chooser: document.querySelector('#package-choice-result').innerHTML,
    target: document.querySelector('#package-target').value, selectedAppearance: document.querySelector('#package-appearance').value,
    visibleIds: [...document.querySelectorAll('#icons .icon-card')].filter(node => node.getClientRects().length).map(node => node.dataset.iconFunction),
    originals: [...document.querySelectorAll('#icons .icon-card')].map(node => [node.dataset.iconFunction,
      node.querySelector('h4').textContent, [...node.querySelectorAll('img')].map(image => image.getAttribute('src'))]) }));
}

async function assertIconPngLayout(page, { spacing = false } = {}) {
  const state = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
    controls: [...document.querySelectorAll('[data-icon-png], #icon-png-help, #icon-png-status')]
      .filter(node => node.getClientRects().length && node.textContent.trim()).map(node => {
        const style = getComputedStyle(node), box = node.getBoundingClientRect(), range = document.createRange();
        range.selectNodeContents(node);
        return { tag: node.tagName, text: node.textContent, width: box.width, height: box.height, left: box.left, right: box.right,
          visibility: style.visibility, opacity: style.opacity, fontSize: style.fontSize, lineHeight: style.lineHeight,
          letterSpacing: style.letterSpacing, wordSpacing: style.wordSpacing, marginBlockEnd: style.marginBlockEnd,
          textRects: [...range.getClientRects()].filter(rect => rect.width && rect.height)
            .map(rect => ({ left: rect.left, right: rect.right, width: rect.width, height: rect.height })) };
      }) }));
  assert.ok(state.scrollWidth <= state.width + 1);
  for (const control of state.controls) {
    assert.equal(control.visibility, 'visible'); assert.ok(Number(control.opacity) > 0);
    assert.ok(control.width > 0 && control.height > 0 && control.left >= -1 && control.right <= state.width + 1, JSON.stringify(control));
    assert.ok(control.textRects.length, 'PNG control text remains present');
    for (const rect of control.textRects) assert.ok(rect.left >= control.left - 1 && rect.right <= control.right + 1, JSON.stringify(control));
    if (control.tag === 'BUTTON') assert.ok(control.height >= 44, JSON.stringify(control));
    if (!spacing) continue;
    const size = parseFloat(control.fontSize);
    for (const [property, ratio] of [['lineHeight', 1.5], ['letterSpacing', .12], ['wordSpacing', .16]])
      assert.ok(parseFloat(control[property]) + .02 >= size * ratio, 'PNG spacing admission ' + property + ': ' + JSON.stringify(control));
    if (control.tag === 'P') assert.ok(parseFloat(control.marginBlockEnd) + .02 >= size * 2, JSON.stringify(control));
  }
  return { visibleControls: state.controls.length, spacing, width: state.width };
}

async function assertIconPngFallback(page) {
  assert.equal(await page.locator('[data-icon-png]').count(), 562);
  assert.equal(await page.locator('[data-icon-png]:visible').count(), 0);
  assert.ok(await page.locator('#icon-artwork-download').isVisible());
  assert.equal(await page.locator('#icon-artwork-download').getAttribute('href'), iconArchive);
  assert.match(await page.locator('#icon-png-help').textContent(), /hosted|HTTPS?/i);
  assert.match(await page.locator('#icon-png-help').textContent(), /SVG/i);
}

test('individual PNG controls bind all 562 local drawings and keyboard acquisition preserves surrounding choices', async () => {
  for (const width of [390, 1280]) {
    const { context, page, consoleErrors, network } = await pageFor({ viewport: { width, height: 900 } });
    try {
      const controls = await page.locator('[data-icon-png]').evaluateAll(nodes => nodes.map(node => ({
        id: node.closest('[data-icon-function]')?.dataset.iconFunction, appearance: node.dataset.iconAppearance,
        filename: node.dataset.iconFilename, source: node.closest('figure')?.querySelector('img')?.getAttribute('src'),
        type: node.type, hidden: node.hidden, name: node.getAttribute('aria-label'), pageAppearance: node.hasAttribute('data-appearance') })));
      assert.equal(controls.length, 562);
      const expected = iconFunctions.flatMap(id => ['Clair', 'Obscur'].map(appearance => ({ id, appearance,
        filename: `Clair-Obscur-0.17.0-${appearance}-${id}-512.png`, source: `icons/${appearance}/${id}.svg` })));
      assert.deepEqual(controls.map(({ id, appearance, filename, source }) => ({ id, appearance, filename, source })), expected);
      for (const control of controls) {
        assert.equal(control.type, 'button'); assert.equal(control.hidden, false); assert.equal(control.pageAppearance, false);
        assert.ok(control.name.includes(control.appearance) && control.name.includes(iconLabels.get(control.id)));
      }
      assert.equal(await page.locator('#icon-png-status').getAttribute('role'), 'status');
      await assertIconPngLayout(page);
      const downloads = [];
      for (const appearance of ['Clair', 'Obscur']) for (const id of ['phone', 'fly-delta', 'bank-of-america', 'discover', 'fidelity-investments',
        'accuweather', 'weather-channel', 'windy-com', 'rainviewer',
        ...runningTrainingIconApps.map(([id]) => id), ...learningIconApps.map(([id]) => id), ...readingIconApps.map(([id]) => id), ...phoneServiceApps.map(([id]) => id)]) {
        if (downloads.length && downloads.length % 8 === 0) await new Promise(resolve => setTimeout(resolve, 1100));
        await page.getByRole('button', { name: appearance === 'Clair' ? 'Obscur' : 'Clair', exact: true }).click();
        await page.locator('#package-target').selectOption('equicord'); await page.locator('#package-appearance').selectOption('Clair');
        await page.locator('#icon-query').fill(id); const before = await iconPngSurroundings(page), requestsBefore = network.length;
        const bytes = await acquireIconPng(page, id, appearance);
        downloads.push(await assertDownloadedIconPng(page, bytes, id, appearance));
        assert.deepEqual(await iconPngSurroundings(page), before);
        assert.equal(network.length, requestsBefore, 'On-demand PNG preparation uses the already loaded local image without a fetch or upload');
        assert.equal(await iconPngButton(page, id, appearance).evaluate(node => node === document.activeElement), true);
      }
      assert.deepEqual(consoleErrors, []);
      results.scenarios.push({ name: 'individual PNG keyboard acquisition', status: 'passed', width, controls: controls.length, downloads,
        scope: 'Browser-downloaded bytes independently decoded and compared with an explicitly selected source SVG; no phone installation or native acceptance' });
    } finally { await context.close(); }
  }
});

test('individual PNG capability and metadata admission preserve the static SVG fallback', async () => {
  for (const fault of ['toBlob', 'object-url', 'wrong-filename']) {
    const { context, page, consoleErrors } = await pageFor({ setup: async (context, page) => {
      if (fault === 'wrong-filename') await page.route(origin + '/', async route => {
        const html = await readFile(path.join(site, 'index.html'), 'utf8');
        const filename = 'Clair-Obscur-0.17.0-Clair-google-chrome-512.png';
        assert.equal(html.split(filename).length - 1, 1);
        await route.fulfill({ contentType: 'text/html', body: html.replace(filename, '../untrusted.png') });
      });
      else await context.addInitScript(fault => {
        if (fault === 'toBlob') HTMLCanvasElement.prototype.toBlob = undefined;
        else URL.createObjectURL = undefined;
      }, fault);
    } });
    try {
      await assertIconPngFallback(page);
      await snapshotFinderCatalog(page);
      await page.locator('#icon-query').fill('fly-delta'); await assertFinderResults(page, ['fly-delta']);
      await page.getByRole('button', { name: 'Clair', exact: true }).click();
      assert.equal(await page.locator('html').getAttribute('data-theme'), 'Clair');
      assert.deepEqual(consoleErrors, []);
      results.scenarios.push({ name: 'individual PNG admission fallback', fault, status: 'passed', controlsExposed: 0 });
    } finally { await context.close(); }
  }
});

test('individual PNG failures report the problem and permit a successful retry without changing the page', async () => {
  for (const fault of ['image-decode', 'null-blob', 'missing-context']) {
    const { context, page, consoleErrors } = await pageFor();
    const downloads = []; page.on('download', download => downloads.push(download));
    try {
      await page.locator('#icon-query').fill('fly-delta'); const before = await iconPngSurroundings(page);
      await page.evaluate(fault => {
        const image = document.querySelector('[data-icon-function="fly-delta"] figure img');
        window.pngFailureFixture = { image, decode: image.decode, toBlob: HTMLCanvasElement.prototype.toBlob,
          getContext: HTMLCanvasElement.prototype.getContext };
        if (fault === 'image-decode') image.decode = async () => { throw new DOMException('Controlled decode failure', 'EncodingError'); };
        if (fault === 'null-blob') HTMLCanvasElement.prototype.toBlob = callback => callback(null);
        if (fault === 'missing-context') HTMLCanvasElement.prototype.getContext = () => null;
      }, fault);
      const button = iconPngButton(page, 'fly-delta', 'Clair'); await button.focus(); await page.keyboard.press('Enter');
      await page.waitForFunction(() => document.querySelector('#icon-png-status').textContent.startsWith('Could not prepare'));
      assert.equal(downloads.length, 0); assert.notEqual(await button.getAttribute('aria-disabled'), 'true');
      assert.deepEqual(await iconPngSurroundings(page), before);
      await page.evaluate(() => {
        const fixture = window.pngFailureFixture; fixture.image.decode = fixture.decode;
        HTMLCanvasElement.prototype.toBlob = fixture.toBlob; HTMLCanvasElement.prototype.getContext = fixture.getContext;
      });
      const bytes = await acquireIconPng(page, 'fly-delta', 'Clair');
      await assertDownloadedIconPng(page, bytes, 'fly-delta', 'Clair');
      assert.equal(downloads.length, 1); assert.deepEqual(await iconPngSurroundings(page), before);
      assert.deepEqual(consoleErrors, []);
      results.scenarios.push({ name: 'individual PNG failure and recovery', fault, status: 'passed', failedDownloads: 0, recoveredDownloads: 1 });
    } finally { await context.close(); }
  }
});

test('individual PNG shared busy state is exposed on other controls and restored after success or failure', async () => {
  for (const outcome of ['success', 'failure']) {
    const { context, page, consoleErrors } = await pageFor();
    const downloads = []; page.on('download', download => downloads.push(download));
    try {
      await page.locator('#package-target').selectOption('equicord');
      await page.locator('#package-appearance').selectOption('Clair');
      await page.locator('#icon-query').fill('phone');
      assert.deepEqual(await page.locator('.icon-card:visible').evaluateAll(nodes => nodes.map(node => node.dataset.iconFunction)), ['phone']);
      const originalStates = await page.locator('[data-icon-png]').evaluateAll(nodes =>
        nodes.map(node => [node.getAttribute('aria-disabled'), node.disabled]));
      assert.equal(originalStates.length, 562);
      await page.evaluate(outcome => {
        const image = document.querySelector('[data-icon-function="phone"] figure img');
        const original = image.decode, decode = original.bind(image);
        const fixture = { image, original, held: false, settled: false };
        image.decode = () => new Promise((resolve, reject) => {
          fixture.held = true;
          const settle = action => { if (!fixture.settled) { fixture.settled = true; action(); } };
          fixture.release = () => settle(() => outcome === 'success' ? decode().then(resolve, reject) :
            reject(new DOMException('Controlled first PNG decode failure', 'EncodingError')));
          fixture.cancel = () => settle(() => reject(new DOMException('Owned PNG fixture cleanup', 'AbortError')));
        });
        window.pngBusyFixture = fixture;
      }, outcome);
      const first = iconPngButton(page, 'phone', 'Clair'), opposite = iconPngButton(page, 'phone', 'Obscur');
      const initial = await iconPngSurroundings(page);
      await first.focus(); await page.keyboard.press('Enter');
      await page.waitForFunction(() => window.pngBusyFixture.held);
      assert.equal(await page.locator('#icon-png-status').innerText(), 'Preparing Clair-Obscur-0.17.0-Clair-phone-512.png...');
      await tabToIconAction(page, 'phone', 'Obscur');
      await page.keyboard.press('Enter');
      assert.equal(await opposite.getAttribute('aria-disabled'), 'true',
        'An opposite-appearance action blocked by pending PNG work must expose its unavailability');
      const busy = await page.locator('[data-icon-png]').evaluateAll(nodes =>
        nodes.map(node => ({ unavailable: node.getAttribute('aria-disabled'), nativeDisabled: node.disabled })));
      assert.equal(busy.length, 562);
      assert.ok(busy.every(node => node.unavailable === 'true'), 'Every serially blocked PNG action must expose its busy state');
      assert.ok(busy.every(node => !node.nativeDisabled), 'Temporary unavailability retains the controls in keyboard order');
      assert.equal(await opposite.evaluate(node => node === document.activeElement), true);
      assert.equal(downloads.length, 0); assert.deepEqual(await iconPngSurroundings(page), initial);

      await page.locator('#icon-query').focus(); await page.keyboard.press('Control+A');
      await page.keyboard.type('com.weather.Weather');
      assert.equal(await page.locator('#icon-query').inputValue(), 'com.weather.Weather');
      assert.deepEqual(await page.locator('.icon-card:visible').evaluateAll(nodes => nodes.map(node => node.dataset.iconFunction)), ['weather-channel']);
      for (const id of ['icon-kind', 'icon-clear', 'icon-history-summary']) {
        await page.keyboard.press('Tab'); assert.equal(await page.evaluate(() => document.activeElement.id), id);
      }
      await tabToIconAction(page, 'weather-channel', 'Clair');
      const other = iconPngButton(page, 'weather-channel', 'Clair'), filtered = await iconPngSurroundings(page);
      await page.keyboard.press('Enter');
      assert.equal(await other.getAttribute('aria-disabled'), 'true');
      assert.equal(await other.evaluate(node => node === document.activeElement), true);
      assert.equal(await page.locator('#icon-png-status').innerText(), 'Preparing Clair-Obscur-0.17.0-Clair-phone-512.png...');
      assert.equal(downloads.length, 0); assert.deepEqual(await iconPngSurroundings(page), filtered);

      let firstAcquisition;
      if (outcome === 'success') {
        const completed = page.waitForEvent('download', { timeout: 5000 });
        await page.evaluate(() => window.pngBusyFixture.release());
        const download = await completed;
        assert.equal(await download.failure(), null);
        assert.equal(download.suggestedFilename(), 'Clair-Obscur-0.17.0-Clair-phone-512.png');
        const chunks = []; for await (const chunk of await download.createReadStream()) chunks.push(chunk);
        firstAcquisition = await assertDownloadedIconPng(page, Buffer.concat(chunks), 'phone', 'Clair');
        assert.equal(downloads.length, 1);
      } else {
        await page.evaluate(() => window.pngBusyFixture.release());
        await page.waitForFunction(() => document.querySelector('#icon-png-status').textContent.startsWith('Could not prepare'));
        assert.equal(downloads.length, 0);
      }
      await page.waitForFunction(() => [...document.querySelectorAll('[data-icon-png]')]
        .every(node => node.getAttribute('aria-disabled') !== 'true'));
      assert.deepEqual(await page.locator('[data-icon-png]').evaluateAll(nodes =>
        nodes.map(node => [node.getAttribute('aria-disabled'), node.disabled])), originalStates);
      assert.equal(await other.evaluate(node => node === document.activeElement), true);
      assert.deepEqual(await iconPngSurroundings(page), filtered);
      const bytes = await acquireIconPng(page, 'weather-channel', 'Clair');
      const retried = await assertDownloadedIconPng(page, bytes, 'weather-channel', 'Clair');
      assert.equal(downloads.length, outcome === 'success' ? 2 : 1);
      assert.deepEqual(await page.locator('[data-icon-png]').evaluateAll(nodes =>
        nodes.map(node => [node.getAttribute('aria-disabled'), node.disabled])), originalStates);
      assert.equal(await other.evaluate(node => node === document.activeElement), true);
      assert.deepEqual(await iconPngSurroundings(page), filtered);
      assert.equal(await page.evaluate(() => window.pngBusyFixture.settled), true);
      assert.deepEqual(consoleErrors, []);
      results.scenarios.push({ name: 'serial PNG cross-control busy state and recovery', outcome, status: 'passed',
        pendingControls: busy.length, ignoredAttempts: ['phone/Obscur', 'weather-channel/Clair'],
        firstAcquisition, retried, downloads: downloads.length,
        scope: 'Controlled delay in a real image decode, keyboard activation, actual downloads and independent PNG pixels. No timing or native-device claim.' });
    } finally {
      try {
        await page.evaluate(() => {
          const fixture = window.pngBusyFixture;
          if (fixture) { fixture.cancel?.(); fixture.image.decode = fixture.original; }
        });
      } finally { await context.close(); }
    }
  }
});

test('individual PNG duplicate activation is bounded and its object URL is retired', async () => {
  const { context, page, consoleErrors } = await pageFor();
  const downloads = []; page.on('download', download => downloads.push(download));
  try {
    await page.locator('#icon-query').fill('phone');
    await page.evaluate(() => {
      const image = document.querySelector('[data-icon-function="phone"] figure img'), decode = image.decode.bind(image);
      image.decode = () => new Promise((resolve, reject) => { window.releasePngDecode = () => decode().then(resolve, reject); });
      window.pngUrls = { created: [], revoked: [] };
      const create = URL.createObjectURL.bind(URL), revoke = URL.revokeObjectURL.bind(URL);
      URL.createObjectURL = blob => { const url = create(blob); window.pngUrls.created.push(url); return url; };
      URL.revokeObjectURL = url => { window.pngUrls.revoked.push(url); return revoke(url); };
    });
    const button = iconPngButton(page, 'phone', 'Clair'); await button.focus();
    await page.keyboard.press('Enter'); await page.keyboard.press('Enter');
    assert.equal(await button.getAttribute('aria-disabled'), 'true'); assert.equal(downloads.length, 0);
    const completed = page.waitForEvent('download', { timeout: 5000 }); await page.evaluate(() => window.releasePngDecode());
    const download = await completed; assert.equal(await download.failure(), null);
    assert.equal(download.suggestedFilename(), 'Clair-Obscur-0.17.0-Clair-phone-512.png');
    await page.waitForFunction(() => window.pngUrls.created.length === 1 && window.pngUrls.revoked.length === 1);
    assert.equal(downloads.length, 1);
    const urls = await page.evaluate(() => window.pngUrls); assert.deepEqual(urls.revoked, urls.created);
    assert.notEqual(await button.getAttribute('aria-disabled'), 'true'); assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'individual PNG duplicate activation and URL retirement', status: 'passed', downloads: 1, createdUrls: 1, retiredUrls: 1 });
  } finally { await context.close(); }
});

for (const stress of [false, true]) test(`individual PNG ${stress ? 'narrow enlarged fallback stress' : 'spacing-only'} keeps real controls operable`, async () => {
  const { context, page, consoleErrors } = await pageFor({ viewport: { width: stress ? 320 : 1280, height: 900 }, missingFont: stress });
  try {
    await snapshotFinderCatalog(page);
    if (stress) await page.addStyleTag({ content: 'html { font-size: 200%; }' });
    const baseline = await spacingContentBaseline(page);
    assert.equal(baseline.width, stress ? 320 : 1280); assert.equal(baseline.rootFontSize, stress ? '32px' : '16px');
    await page.addStyleTag({ content: textSpacingOverride });
    const admission = await assertTextSpacing(page, baseline);
    const controls = await assertIconPngLayout(page, { spacing: true });
    const acquired = [];
    for (const appearance of ['Clair', 'Obscur']) {
      await page.getByRole('button', { name: appearance, exact: true }).click();
      await page.locator('#icon-query').fill('fly-delta');
      await assertFinderResults(page, ['fly-delta']); await assertIconPngLayout(page, { spacing: true });
      acquired.push(await assertDownloadedIconPng(page, await acquireIconPng(page, 'fly-delta', appearance), 'fly-delta', appearance));
    }
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: stress ? 'individual PNG additional reflow stress' : 'individual PNG spacing only', status: 'passed', admission, controls, acquired,
      scope: stress ? 'Separate combined stress at 320 px, 200% root text and unavailable Inter, not browser zoom' :
        'All four applicable SC 1.4.12 overrides at unchanged 1280 px viewport and 16 px root' });
  } finally { await context.close(); }
});

test('individual PNG qualification rejects an inert listener and a wrong-appearance image response', async () => {
  for (const fault of ['inert-listener', 'wrong-appearance']) {
    const { context, page, consoleErrors } = await pageFor({ setup: async (context, page) => {
      if (fault === 'wrong-appearance') await page.route('**/icons/Clair/phone.svg', async route => route.fulfill({
        contentType: 'image/svg+xml', body: await readFile(path.join(site, 'icons', 'Obscur', 'phone.svg')) }));
    } });
    try {
      await page.locator('#icon-query').fill('phone');
      if (fault === 'inert-listener') {
        const control = iconPngButton(page, 'phone', 'Clair'); assert.ok(await control.isVisible());
        await control.evaluate(node => node.replaceWith(node.cloneNode(true)));
        await assert.rejects(acquireIconPng(page, 'phone', 'Clair', { timeout: 500 }), error => error.name === 'TimeoutError');
      } else {
        const bytes = await acquireIconPng(page, 'phone', 'Clair');
        await assert.rejects(assertDownloadedIconPng(page, bytes, 'phone', 'Clair'),
          error => error.code === 'ERR_ASSERTION' && /independently selected icon and appearance/.test(error.message));
      }
      assert.deepEqual(consoleErrors, []);
      results.scenarios.push({ name: 'individual PNG controlled acceptance failure', fault, status: 'rejected as expected',
        scope: 'Disposable DOM or response fault, not a reported product defect' });
    } finally { await context.close(); }
  }
});

test('icon gallery decodes every current appearance at phone widths and enlarged fallback text', async () => {
  for (const scenario of [{ width: 390, enlarged: false }, { width: 320, enlarged: true }]) {
    const { context, page, consoleErrors } = await pageFor({ viewport: { width: scenario.width, height: 844 }, missingFont: scenario.enlarged });
    try {
      if (scenario.enlarged) await page.addStyleTag({ content: 'html { font-size: 200%; }' });
      for (const appearance of ['Obscur', 'Clair']) {
        await page.getByRole('button', { name: appearance, exact: true }).click();
        assert.equal(await page.locator('html').getAttribute('data-theme'), appearance);
        const decoded = await checkIconGallery(page);
        assert.deepEqual(decoded, iconPaths);
        await checkIconMappingKeyboard(page);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        results.scenarios.push({ name: 'complete paired icon gallery', ...scenario, appearance,
          decoded, nativePhoneVerified: false, status: 'passed' });
      }
      assert.deepEqual(consoleErrors, []);
    } finally { await context.close(); }
  }
});

test('no-script keyboard navigation acquires current and all sixteen preserved icon ZIPs with exact checksums', async () => {
  const { context, page, consoleErrors } = await pageFor({ javaScriptEnabled: false, viewport: { width: 320, height: 844 },
    setup: async (context, page) => page.route('**/preview.css', async route => route.fulfill({ contentType: 'text/css',
      body: await readFile(path.join(site, 'preview.css'), 'utf8') + '\nhtml { font-size: 200%; }\n' + textSpacingOverride })) });
  try {
    await assertIconPngFallback(page);
    await checkIconGallery(page);
    await assertIconHistoryStructure(page, { open: false });
    const spacingBaseline = await spacingContentBaseline(page);
    assert.equal(spacingBaseline.width, 320); assert.equal(spacingBaseline.rootFontSize, '32px');
    const spacingAdmission = await assertTextSpacing(page, spacingBaseline);
    let tabs = 0;
    while (await page.evaluate(() => document.activeElement?.id) !== 'icon-gallery-link' && tabs < 40) {
      await page.keyboard.press('Tab'); tabs++;
    }
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-gallery-link');
    await page.keyboard.press('Enter');
    await page.waitForURL(url => url.hash === '#icons');
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-download');
    const [download] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await download.failure(), null);
    assert.equal(download.suggestedFilename(), path.basename(iconArchive));
    const archivePath = path.join(temp, 'keyboard-icons.zip');
    await download.saveAs(archivePath);
    const bytes = await readFile(archivePath);
    assert.deepEqual(bytes, await readFile(path.join(site, ...iconArchive.split('/'))));
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-checksums');
    const [checksumDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await checksumDownload.failure(), null);
    const chunks = []; for await (const chunk of await checksumDownload.createReadStream()) chunks.push(chunk);
    const digest = crypto.createHash('sha256').update(bytes).digest('hex');
    assert.equal(Buffer.concat(chunks).toString('utf8'), iconChecksums(digest));
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-history-summary');
    assert.equal(await page.locator('#icon-history').evaluate(node => node.open), false);
    await page.keyboard.press('Enter');
    assert.equal(await page.locator('#icon-history').evaluate(node => node.open), true);
    await assertIconHistoryLayout(page, { spacing: true });
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-reading-download');
    await acquirePreservedIconArchive(page, ['icon-artwork-reading-download', readingIconArchive, readingIconDigest]);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-study-learning-download');
    const [learningDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await learningDownload.failure(), null);
    assert.equal(learningDownload.suggestedFilename(), path.basename(learningIconArchive));
    const learningArchivePath = path.join(temp, 'keyboard-icons-learning.zip');
    await learningDownload.saveAs(learningArchivePath);
    const learningBytes = await readFile(learningArchivePath);
    assert.deepEqual(learningBytes, await readFile(path.join(site, ...learningIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(learningBytes).digest('hex'), learningIconDigest);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-running-training-download');
    await acquirePreservedIconArchive(page, ['icon-artwork-running-training-download', runningTrainingIconArchive, runningTrainingIconDigest]);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-weather-download');
    const [weatherDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await weatherDownload.failure(), null);
    assert.equal(weatherDownload.suggestedFilename(), path.basename(weatherIconArchive));
    const weatherArchivePath = path.join(temp, 'keyboard-icons-weather.zip');
    await weatherDownload.saveAs(weatherArchivePath);
    const weatherBytes = await readFile(weatherArchivePath);
    assert.deepEqual(weatherBytes, await readFile(path.join(site, ...weatherIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(weatherBytes).digest('hex'), weatherIconDigest);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-finance-download');
    const [financeDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await financeDownload.failure(), null);
    assert.equal(financeDownload.suggestedFilename(), path.basename(financeIconArchive));
    const financeArchivePath = path.join(temp, 'keyboard-icons-finance.zip');
    await financeDownload.saveAs(financeArchivePath);
    const financeBytes = await readFile(financeArchivePath);
    assert.deepEqual(financeBytes, await readFile(path.join(site, ...financeIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(financeBytes).digest('hex'), financeIconDigest);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-travel-download');
    const [travelDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await travelDownload.failure(), null);
    assert.equal(travelDownload.suggestedFilename(), path.basename(travelIconArchive));
    const travelArchivePath = path.join(temp, 'keyboard-icons-travel.zip');
    await travelDownload.saveAs(travelArchivePath);
    const travelBytes = await readFile(travelArchivePath);
    assert.deepEqual(travelBytes, await readFile(path.join(site, ...travelIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(travelBytes).digest('hex'), travelIconDigest);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-food-order-download');
    const [foodOrderDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await foodOrderDownload.failure(), null);
    assert.equal(foodOrderDownload.suggestedFilename(), path.basename(foodOrderIconArchive));
    const foodOrderArchivePath = path.join(temp, 'keyboard-icons-food-order.zip');
    await foodOrderDownload.saveAs(foodOrderArchivePath);
    const foodOrderBytes = await readFile(foodOrderArchivePath);
    assert.deepEqual(foodOrderBytes, await readFile(path.join(site, ...foodOrderIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(foodOrderBytes).digest('hex'), foodOrderIconDigest);
    await page.keyboard.press('Tab');
    // Keep each deliberate archive-and-checksum batch below ten acquisitions.
    await new Promise(resolve => setTimeout(resolve, 1100));
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-everyday-download');
    const [everydayDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await everydayDownload.failure(), null);
    assert.equal(everydayDownload.suggestedFilename(), path.basename(everydayIconArchive));
    const everydayArchivePath = path.join(temp, 'keyboard-icons-everyday.zip');
    await everydayDownload.saveAs(everydayArchivePath);
    const everydayBytes = await readFile(everydayArchivePath);
    assert.deepEqual(everydayBytes, await readFile(path.join(site, ...everydayIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(everydayBytes).digest('hex'), everydayIconDigest);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-broad-download');
    const [broadDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await broadDownload.failure(), null);
    assert.equal(broadDownload.suggestedFilename(), path.basename(broadIconArchive));
    const broadArchivePath = path.join(temp, 'keyboard-icons-broad.zip');
    await broadDownload.saveAs(broadArchivePath);
    const broadBytes = await readFile(broadArchivePath);
    assert.deepEqual(broadBytes, await readFile(path.join(site, ...broadIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(broadBytes).digest('hex'), broadIconDigest);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-companion-download');
    const [companionDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await companionDownload.failure(), null);
    assert.equal(companionDownload.suggestedFilename(), path.basename(companionIconArchive));
    const companionArchivePath = path.join(temp, 'keyboard-icons-companion.zip');
    await companionDownload.saveAs(companionArchivePath);
    const companionBytes = await readFile(companionArchivePath);
    assert.deepEqual(companionBytes, await readFile(path.join(site, ...companionIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(companionBytes).digest('hex'), companionIconDigest);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-monochrome-download');
    const [monochromeDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await monochromeDownload.failure(), null);
    assert.equal(monochromeDownload.suggestedFilename(), path.basename(monochromeIconArchive));
    const monochromeArchivePath = path.join(temp, 'keyboard-icons-monochrome.zip');
    await monochromeDownload.saveAs(monochromeArchivePath);
    const monochromeBytes = await readFile(monochromeArchivePath);
    assert.deepEqual(monochromeBytes, await readFile(path.join(site, ...monochromeIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(monochromeBytes).digest('hex'), monochromeIconDigest);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-third-app-download');
    const [thirdAppDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await thirdAppDownload.failure(), null);
    assert.equal(thirdAppDownload.suggestedFilename(), path.basename(thirdAppIconArchive));
    const thirdAppArchivePath = path.join(temp, 'keyboard-icons-third-app.zip');
    await thirdAppDownload.saveAs(thirdAppArchivePath);
    const thirdAppBytes = await readFile(thirdAppArchivePath);
    assert.deepEqual(thirdAppBytes, await readFile(path.join(site, ...thirdAppIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(thirdAppBytes).digest('hex'), thirdAppIconDigest);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-second-app-download');
    const [secondAppDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await secondAppDownload.failure(), null);
    assert.equal(secondAppDownload.suggestedFilename(), path.basename(secondAppIconArchive));
    const secondAppArchivePath = path.join(temp, 'keyboard-icons-second-app.zip');
    await secondAppDownload.saveAs(secondAppArchivePath);
    const secondAppBytes = await readFile(secondAppArchivePath);
    assert.deepEqual(secondAppBytes, await readFile(path.join(site, ...secondAppIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(secondAppBytes).digest('hex'), secondAppIconDigest);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-first-app-download');
    // Blink throttles more than ten downloads in a one-second burst.
    // https://raw.githubusercontent.com/chromium/chromium/0e66b94549a8bd85f03fbdf189b752d6e7b63c32/third_party/blink/renderer/core/frame/local_frame.cc
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-first-app-download');
    const [firstAppDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await firstAppDownload.failure(), null);
    assert.equal(firstAppDownload.suggestedFilename(), path.basename(firstAppIconArchive));
    const firstAppArchivePath = path.join(temp, 'keyboard-icons-first-app.zip');
    await firstAppDownload.saveAs(firstAppArchivePath);
    const firstAppBytes = await readFile(firstAppArchivePath);
    assert.deepEqual(firstAppBytes, await readFile(path.join(site, ...firstAppIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(firstAppBytes).digest('hex'), firstAppIconDigest);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-previous-download');
    const [previousDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await previousDownload.failure(), null);
    assert.equal(previousDownload.suggestedFilename(), path.basename(previousIconArchive));
    const previousArchivePath = path.join(temp, 'keyboard-icons-previous.zip');
    await previousDownload.saveAs(previousArchivePath);
    const previousBytes = await readFile(previousArchivePath);
    assert.deepEqual(previousBytes, await readFile(path.join(site, ...previousIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(previousBytes).digest('hex'), previousIconDigest);
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'icon-artwork-legacy-download');
    const [legacyDownload] = await Promise.all([page.waitForEvent('download'), page.keyboard.press('Enter')]);
    assert.equal(await legacyDownload.failure(), null);
    assert.equal(legacyDownload.suggestedFilename(), path.basename(legacyIconArchive));
    const legacyArchivePath = path.join(temp, 'keyboard-icons-original.zip');
    await legacyDownload.saveAs(legacyArchivePath);
    const legacyBytes = await readFile(legacyArchivePath);
    assert.deepEqual(legacyBytes, await readFile(path.join(site, ...legacyIconArchive.split('/'))));
    assert.equal(crypto.createHash('sha256').update(legacyBytes).digest('hex'), legacyIconDigest);
    await setIconHistoryOpen(page, false, 'Space');
    await setIconHistoryOpen(page, true, 'Enter');
    await assertIconHistoryLayout(page, { spacing: true });
    await assertTextSpacing(page, spacingBaseline);
    run(['-c', [
      'import hashlib,json,pathlib,sys,zipfile',
      'archive_path,site=map(pathlib.Path,sys.argv[1:])',
      `functions=${JSON.stringify(iconManifestFunctions)}`,
      'expected={f"{appearance}/{function}.svg" for appearance in ("Clair","Obscur") for function in functions}',
      'with zipfile.ZipFile(archive_path) as archive:',
      ' assert len(archive.namelist())==564 and set(archive.namelist())==expected|{"manifest.json","LICENSE.txt"}',
      ' assert archive.testzip() is None',
      ' for name in expected|{"manifest.json","LICENSE.txt"}:',
      '  assert archive.read(name)==(site/"icons"/name).read_bytes()',
      ' manifest=json.loads(archive.read("manifest.json"))',
      ' assert manifest["version"]=="0.17.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==562',
      ' assert [entry["id"] for entry in manifest["catalog"]]==functions',
      ' for record in manifest["files"]:',
      '  assert hashlib.sha256(archive.read(record["path"])).hexdigest()==record["sha256"]',
    ].join('\n'), archivePath, site]);
    run(['-c', [
      'import hashlib,json,sys,zipfile',
      `functions=${JSON.stringify([...generalIconFunctions, ...readingNamedIconApps.map(row => row[0])])}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==484',
      ' manifest_bytes=archive.read("manifest.json")',
      ' assert hashlib.sha256(manifest_bytes).hexdigest()=="edf610a33c55adeecca9c43bde0b0786a4f7d0b81c018880a504068218670b19"',
      ' manifest=json.loads(manifest_bytes)',
      ' assert manifest["version"]=="0.16.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==482',
    ].join('\n'), path.join(site, ...readingIconArchive.split('/'))]);
    run(['-c', [
      'import hashlib,json,sys,zipfile',
      `functions=${JSON.stringify([...generalIconFunctions, ...learningNamedIconApps.map(row => row[0])])}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==468',
      ' manifest_bytes=archive.read("manifest.json")',
      ' assert hashlib.sha256(manifest_bytes).hexdigest()=="3979cc7eaf90a5cf8aab82bd711fc8d2ff92388856cbb41b9321442693b88b2b"',
      ' manifest=json.loads(manifest_bytes)',
      ' assert manifest["version"]=="0.15.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==466',
    ].join('\n'), learningArchivePath]);
    run(['-c', [
      'import hashlib,json,sys,zipfile',
      `functions=${JSON.stringify([...generalIconFunctions, ...weatherNamedIconApps.map(row => row[0])])}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==436',
      ' manifest_bytes=archive.read("manifest.json")',
      ' assert hashlib.sha256(manifest_bytes).hexdigest()=="cc573fb8f3996d05eff6d8e724c179f17001ffcfaff26bbfade76e52591ce723"',
      ' manifest=json.loads(manifest_bytes)',
      ' assert manifest["version"]=="0.13.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==434',
    ].join('\n'), weatherArchivePath]);
    run(['-c', [
      'import json,sys,zipfile',
      `functions=${JSON.stringify([...generalIconFunctions, ...financeNamedIconApps.map(row => row[0])])}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==416',
      ' manifest=json.loads(archive.read("manifest.json"))',
      ' assert manifest["version"]=="0.12.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==414',
    ].join('\n'), financeArchivePath]);
    run(['-c', [
      'import json,sys,zipfile',
      `functions=${JSON.stringify([...generalIconFunctions, ...travelNamedIconApps.map(row => row[0])])}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==396',
      ' manifest=json.loads(archive.read("manifest.json"))',
      ' assert manifest["version"]=="0.11.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==394',
    ].join('\n'), travelArchivePath]);
    run(['-c', [
      'import json,sys,zipfile',
      `functions=${JSON.stringify([...generalIconFunctions, ...foodOrderNamedIconApps.map(row => row[0])])}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==376',
      ' manifest=json.loads(archive.read("manifest.json"))',
      ' assert manifest["version"]=="0.10.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==374',
    ].join('\n'), foodOrderArchivePath]);
    run(['-c', [
      'import json,sys,zipfile',
      `functions=${JSON.stringify([...generalIconFunctions, ...everydayNamedIconApps.map(row => row[0])])}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==352',
      ' manifest=json.loads(archive.read("manifest.json"))',
      ' assert manifest["version"]=="0.9.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==350',
    ].join('\n'), everydayArchivePath]);
    run(['-c', [
      'import hashlib,json,sys,zipfile',
      `functions=${JSON.stringify([...generalIconFunctions, ...broadNamedIconApps.map(row => row[0])])}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==256',
      ' manifest=json.loads(archive.read("manifest.json"))',
      ' assert manifest["version"]=="0.8.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==254',
      ' assert hashlib.sha256(archive.read("manifest.json")).hexdigest()=="7a8a35d6ba1186a718e970e26c5c6b7b19bf4949010c7bc89af3cb6063b95252"',
    ].join('\n'), broadArchivePath]);
    run(['-c', [
      'import json,sys,zipfile',
      `functions=${JSON.stringify([...generalIconFunctions, ...companionNamedIconApps.map(row => row[0])])}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==192',
      ' manifest=json.loads(archive.read("manifest.json"))',
      ' assert manifest["version"]=="0.7.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==190',
    ].join('\n'), companionArchivePath]);
    run(['-c', [
      'import json,sys,zipfile',
      `functions=${JSON.stringify([...generalIconFunctions, ...monochromeNamedIconApps.map(row => row[0])])}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==180',
      ' manifest=json.loads(archive.read("manifest.json"))',
      ' assert manifest["version"]=="0.6.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==178',
    ].join('\n'), monochromeArchivePath]);
    run(['-c', [
      'import json,pathlib,sys,zipfile',
      `functions=${JSON.stringify(generalIconFunctions)}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==50',
      ' manifest=json.loads(archive.read("manifest.json"))',
      ' assert manifest["version"]=="0.1.0" and manifest["stroke_width"]==12',
      ' assert manifest["functions"]==functions and len(manifest["files"])==48',
    ].join('\n'), legacyArchivePath]);
    run(['-c', [
      'import json,sys,zipfile',
      `functions=${JSON.stringify(generalIconFunctions)}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==50',
      ' manifest=json.loads(archive.read("manifest.json"))',
      ' assert manifest["version"]=="0.2.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==48',
    ].join('\n'), previousArchivePath]);
    run(['-c', [
      'import json,sys,zipfile',
      `functions=${JSON.stringify([...generalIconFunctions, ...secondNamedIconApps.map(row => row[0])])}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==164',
      ' manifest=json.loads(archive.read("manifest.json"))',
      ' assert manifest["version"]=="0.4.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==162',
    ].join('\n'), secondAppArchivePath]);
    run(['-c', [
      'import json,sys,zipfile',
      `functions=${JSON.stringify([...generalIconFunctions, ...firstNamedIconApps.map(row => row[0])])}`,
      'with zipfile.ZipFile(sys.argv[1]) as archive:',
      ' assert archive.testzip() is None and len(archive.namelist())==116',
      ' manifest=json.loads(archive.read("manifest.json"))',
      ' assert manifest["version"]=="0.3.0" and manifest["stroke_width"]==16',
      ' assert manifest["functions"]==functions and len(manifest["files"])==114',
    ].join('\n'), firstAppArchivePath]);
    const mappingKeyboard = await checkIconMappingKeyboard(page);
    assert.equal(new URL(page.url()).hash, '#icons');
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'no-script icon artwork keyboard acquisition', status: 'passed', tabs,
      sha256: digest, readingSha256: readingIconDigest, learningSha256: learningIconDigest, weatherSha256: weatherIconDigest, financeSha256: financeIconDigest, travelSha256: travelIconDigest, foodOrderSha256: foodOrderIconDigest, everydaySha256: everydayIconDigest, broadSha256: broadIconDigest, companionSha256: companionIconDigest, monochromeSha256: monochromeIconDigest, secondAppSha256: secondAppIconDigest, firstAppSha256: firstAppIconDigest, previousSha256: previousIconDigest, legacySha256: legacyIconDigest,
      currentArchiveFiles: 564, readingArchiveFiles: 484, learningArchiveFiles: 468, weatherArchiveFiles: 436, financeArchiveFiles: 416, travelArchiveFiles: 396, foodOrderArchiveFiles: 376, everydayArchiveFiles: 352, broadArchiveFiles: 256, companionArchiveFiles: 192, monochromeArchiveFiles: 180, secondAppArchiveFiles: 164, firstAppArchiveFiles: 116, preservedArchiveFiles: 50, nativePhoneVerified: false,
      width: 320, rootFontSize: '32px', spacingAdmission, mappingKeyboard,
      scope: 'Combined no-script, narrow, enlarged and spacing stress; separate from spacing-only acceptance' });
  } finally { await context.close(); }
});

test('icon gallery qualification rejects one missing image and recovers without hiding its label', async () => {
  const { context, page } = await pageFor({ setup: async pageContext => {
    await pageContext.route('**/icons/Clair/phone.svg', route => route.fulfill({ status: 404, contentType: 'image/svg+xml', body: '' }));
  } });
  try {
    await assert.rejects(checkIconGallery(page), /Icon not decoded: icons\/Clair\/phone\.svg/);
    const failed = page.locator('#icons [data-icon-function="phone"] img').first();
    assert.equal(await failed.getAttribute('alt'), 'Clair Phone icon');
    assert.equal(await page.locator('#icons [data-icon-function="phone"] h4').textContent(), 'Phone');
    await context.unroute('**/icons/Clair/phone.svg');
    await page.reload();
    assert.deepEqual(await checkIconGallery(page), iconPaths);
    const packageText = page.locator('#icons [data-icon-function="youtube"] p code');
    await packageText.evaluate(node => { node.style.visibility = 'hidden'; });
    await assert.rejects(checkIconGallery(page), /youtube/);
    await packageText.evaluate(node => { node.style.visibility = ''; });
    assert.deepEqual(await checkIconGallery(page), iconPaths);
    results.scenarios.push({ name: 'controlled missing gallery image', status: 'rejected and recovered',
      scope: 'disposable missing-resource fault, not a product defect' });
  } finally { await context.close(); }
});


function assertTerminalFragment(document) {
  assert.deepEqual(Object.keys(document), ['schemes']);
  assert.ok(Array.isArray(document.schemes));
  assert.equal(document.schemes.length, 2);
  const fields = ['name', 'background', 'foreground', 'cursorColor', 'selectionBackground', ...terminalAnsi.map(([field]) => field)];
  for (const [index, appearance] of ['Clair', 'Obscur'].entries()) {
    const scheme = document.schemes[index];
    assert.deepEqual(Object.keys(scheme).sort(), [...fields].sort());
    assert.equal(scheme.name, `Clair Obscur - ${appearance}`);
    for (const field of fields.filter(field => field !== 'name')) assert.match(scheme[field], /^#[a-f0-9]{6}$/i);
  }
}

function terminalRgb(hex) {
  return `rgb(${[1, 3, 5].map(offset => parseInt(hex.slice(offset, offset + 2), 16)).join(', ')})`;
}

async function checkTerminalSpecimens(page, document) {
  assertTerminalFragment(document);
  assert.equal(await page.locator('#terminal').getAttribute('aria-labelledby'), 'terminal-heading');
  assert.equal(await page.locator('#terminal-heading').textContent(), 'Windows Terminal colors');
  assert.equal(await page.locator('#terminal-download').getAttribute('href'), 'terminal/' + terminalArchive);
  assert.equal(await page.locator('#terminal-checksums').getAttribute('href'), 'terminal/SHA256SUMS');
  assert.equal(await page.locator('#terminal-guide').getAttribute('href'), 'terminal/installation.md');
  const observed = await page.locator('#terminal article.terminal-palette').evaluateAll(cards => {
    function textLayout(node) {
      if (!node) return { missing: true };
      const box = node.getBoundingClientRect(), style = getComputedStyle(node);
      const range = document.createRange(); range.selectNodeContents(node);
      const rects = [...range.getClientRects()].filter(rect => rect.width > 0 && rect.height > 0);
      const clippedBy = [];
      for (let ancestor = node.parentElement; ancestor; ancestor = ancestor.parentElement) {
        const parentStyle = getComputedStyle(ancestor), parent = ancestor.getBoundingClientRect();
        if (parentStyle.visibility !== 'visible' || parentStyle.display === 'none' || Number(parentStyle.opacity) === 0) clippedBy.push('hidden ancestor');
        if (['hidden', 'clip', 'scroll', 'auto'].includes(parentStyle.overflowY)
            && rects.some(rect => rect.top < parent.top - 1 || rect.bottom > parent.bottom + 1)) clippedBy.push('vertical clipping');
        if (['hidden', 'clip', 'scroll', 'auto'].includes(parentStyle.overflowX)
            && rects.some(rect => rect.left < parent.left - 1 || rect.right > parent.right + 1)) clippedBy.push('horizontal clipping');
      }
      return { text: node.textContent, width: box.width, height: box.height, left: box.left, right: box.right,
        clientWidth: node.clientWidth, scrollWidth: node.scrollWidth, display: style.display, visibility: style.visibility,
        opacity: style.opacity, fontSize: style.fontSize, color: style.color, background: style.backgroundColor,
        rects: rects.map(rect => ({ left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom })),
        clippedBy, viewport: innerWidth };
    }
    return cards.map(card => ({
      appearance: card.dataset.palette, background: getComputedStyle(card).backgroundColor, color: getComputedStyle(card).color,
      heading: textLayout(card.querySelector('h3')), name: textLayout(card.querySelector(':scope > p > code')),
      slots: [...card.querySelectorAll('.terminal-slot')].map(slot => ({
        field: slot.dataset.ansi, label: textLayout(slot.querySelector('p')),
        sample: textLayout(slot.querySelector('code')), context: textLayout(slot.querySelector('small')),
      })),
    }));
  });
  assert.equal(observed.length, 2, 'Both static Terminal appearances must remain available');
  for (const [index, appearance] of ['Clair', 'Obscur'].entries()) {
    const card = observed[index], scheme = document.schemes[index];
    assert.equal(card.appearance, appearance);
    assert.equal(card.heading.text, appearance);
    assert.equal(card.name.text, scheme.name);
    assert.equal(card.background, terminalRgb(scheme.background));
    assert.equal(card.color, terminalRgb(scheme.foreground));
    assert.deepEqual(card.slots.map(slot => slot.field), terminalAnsi.map(([field]) => field));
    for (const [slotIndex, [field, label]] of terminalAnsi.entries()) {
      const slot = card.slots[slotIndex];
      const partner = appearance === 'Clair' && ['white', 'brightWhite'].includes(field) ? 'black'
        : appearance === 'Obscur' && ['black', 'brightBlack'].includes(field) ? 'white' : null;
      assert.equal(slot.label.text, `${slotIndex}: ${label}`);
      assert.equal(slot.sample.text, 'Aa 0123');
      assert.equal(slot.context.text, partner ? 'on ' + partner : 'on default');
      assert.equal(slot.sample.color, terminalRgb(scheme[field]), `${appearance} ${field} foreground`);
      assert.equal(slot.sample.background, terminalRgb(partner ? scheme[partner] : scheme.background), `${appearance} ${field} background`);
    }
    for (const node of [card.heading, card.name, ...card.slots.flatMap(slot => [slot.label, slot.sample, slot.context])]) {
      assert.ok(!node.missing && node.text.length > 0 && node.width > 0 && node.height > 0, 'Terminal specimen text unavailable: ' + JSON.stringify(node));
      assert.equal(node.visibility, 'visible'); assert.notEqual(node.display, 'none');
      assert.ok(Number(node.opacity) > 0);
      assert.ok(node.left >= -1 && node.right <= node.viewport + 1, JSON.stringify(node));
      if (node.clientWidth > 0) assert.ok(node.scrollWidth <= node.clientWidth + 1, JSON.stringify(node));
      assert.ok(node.rects.length > 0, 'Retain rendered text rather than an empty colored box');
      assert.ok(node.rects.every(rect => rect.left >= -1 && rect.right <= node.viewport + 1), JSON.stringify(node));
      assert.deepEqual(node.clippedBy, [], JSON.stringify(node));
    }
  }
  const last = page.locator('#terminal .terminal-palette').last().locator('.terminal-slot').last().locator('small');
  await last.scrollIntoViewIfNeeded();
  assert.ok(await last.evaluate(node => {
    const box = node.getBoundingClientRect(); return box.top >= -1 && box.bottom <= innerHeight + 1;
  }), 'The final labeled sample must remain reachable by scrolling');
  assert.equal(await page.locator('#downloads .download-card').count(), 17);
  return observed;
}

async function verifyTerminalDownloads(archiveBytes, checksumBytes, siteRoot) {
  const terminalRoot = path.join(siteRoot, 'terminal');
  assert.deepEqual(archiveBytes, await readFile(path.join(terminalRoot, terminalArchive)), 'Terminal archive bytes differ from captured package');
  assert.deepEqual(checksumBytes, await readFile(path.join(terminalRoot, 'SHA256SUMS')));
  const pairs = checksumBytes.toString('utf8').trimEnd().split('\n').map(line => {
    const match = /^([a-f0-9]{64})  ([A-Za-z0-9._-]+)$/.exec(line);
    assert.ok(match, 'Each checksum must identify one generated local file'); return match.slice(1);
  });
  assert.deepEqual(pairs.map(([, name]) => name).sort(), [terminalFragment, terminalArchive, 'LICENSE.txt', 'manifest.json'].sort());
  for (const [digest, name] of pairs) assert.equal(crypto.createHash('sha256').update(await readFile(path.join(terminalRoot, name))).digest('hex'), digest, 'Terminal checksum mismatch for ' + name);
  const fragment = JSON.parse(await readFile(path.join(terminalRoot, terminalFragment), 'utf8'));
  assertTerminalFragment(fragment);
  const archivePath = path.join(temp, `terminal-acquired-${crypto.createHash('sha256').update(archiveBytes).digest('hex')}.zip`);
  await writeFile(archivePath, archiveBytes);
  run(['-c', [
    'import pathlib,stat,sys,zipfile',
    'archive_path,terminal_root=map(pathlib.Path,sys.argv[1:])',
    `expected={${JSON.stringify(terminalFragment)},"LICENSE.txt"}`,
    'with zipfile.ZipFile(archive_path) as archive:',
    ' names=archive.namelist()',
    ' assert names==sorted(expected) and archive.testzip() is None',
    ' for info in archive.infolist():',
    '  name=pathlib.PurePosixPath(info.filename)',
    '  assert not name.is_absolute() and ".." not in name.parts and "\\\\" not in info.filename',
    '  assert stat.S_ISREG(info.external_attr >> 16)',
    '  assert archive.read(info.filename)==(terminal_root/info.filename).read_bytes()',
  ].join('\n'), archivePath, terminalRoot]);
  return { sha256: crypto.createHash('sha256').update(archiveBytes).digest('hex'), bytes: archiveBytes.length, schemes: fragment.schemes.map(scheme => scheme.name) };
}

async function terminalKeyboardAcquisition(page) {
  assert.equal(await page.evaluate(() => document.activeElement.id), 'terminal-preview-link');
  await page.keyboard.press('Enter');
  await page.waitForURL(url => url.hash === '#terminal');
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'terminal-download');
  const [archive] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), page.keyboard.press('Enter')]);
  assert.equal(await archive.failure(), null);
  assert.equal(archive.suggestedFilename(), terminalArchive);
  const archiveChunks = []; for await (const chunk of await archive.createReadStream()) archiveChunks.push(chunk);
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'terminal-checksums');
  const [checksums] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), page.keyboard.press('Enter')]);
  assert.equal(await checksums.failure(), null);
  const checksumChunks = []; for await (const chunk of await checksums.createReadStream()) checksumChunks.push(chunk);
  const acquisition = await verifyTerminalDownloads(Buffer.concat(archiveChunks), Buffer.concat(checksumChunks), site);
  await page.keyboard.press('Tab');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'terminal-guide');
  const previewUrl = page.url(), guideUrl = origin + '/terminal/installation.md';
  const [guideResponse] = await Promise.all([page.waitForResponse(response => response.url() === guideUrl), page.keyboard.press('Enter')]);
  await page.waitForURL(guideUrl);
  assert.equal(guideResponse.status(), 200);
  const guide = await readFile(path.join(site, 'terminal', 'installation.md'));
  assert.deepEqual(await guideResponse.body(), guide);
  assert.deepEqual(guide, await readFile(path.join(root, 'docs', 'windows-terminal.md')));
  assert.equal((await page.locator('body').innerText()).trim(), guide.toString('utf8').trim());
  return { ...acquisition, previewUrl, guide: 'exact captured repository Markdown',
    guideScope: 'separate plaintext response and content; preview spacing stylesheet does not apply' };
}

test('Windows Terminal specimens show exact package colors and all labels at phone and enlarged fallback sizes', async () => {
  const fragment = JSON.parse(await readFile(path.join(site, 'terminal', terminalFragment), 'utf8'));
  for (const scenario of [{ width: 390, enlarged: false }, { width: 320, enlarged: true }]) {
    const { context, page, consoleErrors } = await pageFor({ viewport: { width: scenario.width, height: 844 }, missingFont: scenario.enlarged });
    try {
      if (scenario.enlarged) await page.addStyleTag({ content: 'html { font-size: 200%; }' });
      assert.equal(await page.locator('html').evaluate(node => getComputedStyle(node).fontSize), scenario.enlarged ? '32px' : '16px');
      for (const appearance of ['Obscur', 'Clair']) {
        await page.getByRole('button', { name: appearance, exact: true }).click();
        assert.equal(await page.locator('html').getAttribute('data-theme'), appearance);
        const specimens = await checkTerminalSpecimens(page, fragment);
        assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        results.scenarios.push({ name: 'complete Terminal color-table specimens', ...scenario, pageAppearance: appearance,
          appearances: specimens.map(card => card.appearance), labeledSlots: 32, nativeTerminalVerified: false, status: 'passed' });
      }
      assert.deepEqual(consoleErrors, []);
    } finally { await context.close(); }
  }
});

test('Windows Terminal no-script sequential keyboard journey acquires the exact ZIP, checksums and captured guide', async () => {
  const { context, page, consoleErrors } = await pageFor({ javaScriptEnabled: false, viewport: { width: 390, height: 844 } });
  try {
    const fragment = JSON.parse(await readFile(path.join(site, 'terminal', terminalFragment), 'utf8'));
    await checkTerminalSpecimens(page, fragment);
    await page.reload();
    let tabs = 0;
    while (await page.evaluate(() => document.activeElement?.id) !== 'terminal-preview-link' && tabs < 40) {
      await page.keyboard.press('Tab'); tabs++;
    }
    const acquisition = await terminalKeyboardAcquisition(page);
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'Terminal sequential no-script acquisition and guide', status: 'passed', tabs,
      ...acquisition, guide: 'exact captured repository Markdown', nativeTerminalVerified: false });
  } finally { await context.close(); }
});

async function waitForGuideDestination(page, anchor, timeout = 2000) {
  // Keyboard dispatch can finish before the fragment navigation is observed.
  // Neither a matching URL alone nor repaired focus proves the keyboard path.
  await page.waitForURL(url => url.hash === '#' + anchor, { timeout, waitUntil: 'commit' });
  const focused = await page.waitForFunction(id => document.activeElement?.id === id, anchor, { timeout });
  await focused.dispose();
}

async function packageCheckerState(page) {
  return page.evaluate(() => {
    function storageEntries(name) {
      try { return Object.entries(window[name]).sort(([a], [b]) => a.localeCompare(b)); }
      catch (error) { return { unavailable: error.name }; }
    }
    return { reading: document.documentElement.dataset.theme,
      target: document.querySelector('#package-target').value,
      appearance: document.querySelector('#package-appearance').value,
      local: storageEntries('localStorage'), session: storageEntries('sessionStorage'), cookie: document.cookie };
  });
}

async function waitForPackageState(page, state) {
  const done = await page.waitForFunction(expected => document.querySelector('#local-package-checker').dataset.state === expected,
    state, { timeout: 2000 });
  await done.dispose();
}

// These are user spacing overrides, not new design defaults. The separate
// Japanese and Arabic samples retain their writing-system-specific spacing.
const textSpacingOverride = `
  body :is(a, p, h1, h2, h3, h4, blockquote, span, strong, b, em, mark, code, pre, label, button, input, select, option, summary, small, li, figcaption):not(:lang(ja), :lang(ar)) {
    line-height: 1.5 !important;
    letter-spacing: .12em !important;
    word-spacing: .16em !important;
  }
  p:not(:lang(ja), :lang(ar)) { margin-block-end: 2em !important; }
`;
const spacingPackages = {
  Clair: { path: 'equicord/Clair-Equicord-0.1.2.theme.css', version: '0.1.2',
    sha256: '0d2184455e281c2e8cd9d5791006a7cc1939a3a5553253c7a6e45b5991bd8054' },
  Obscur: { path: 'equicord/Obscur.theme.css', version: '0.1.1',
    sha256: 'b2fc01e87f749c1138ca5635eb77f1463d2bcb2eac6d5de898bb8d840741d1dd' },
};

async function spacingContentBaseline(page) {
  return page.evaluate(() => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    for (let node; (node = walker.nextNode());) {
      const parent = node.parentElement;
      // Live result text may change after its separately asserted operation.
      if (!node.textContent.trim() || parent.closest('script, style, noscript, option, legend, .skip, #package-chooser, #local-package-checker, #appearance-status, #control-status, #icon-png-status')) continue;
      const range = document.createRange(); range.selectNodeContents(node);
      if (!range.getClientRects().length || getComputedStyle(parent).visibility !== 'visible') continue;
      const steps = [];
      for (let part = node; part !== document.body; part = part.parentNode) {
        steps.unshift([...part.parentNode.childNodes].indexOf(part));
      }
      const style = getComputedStyle(parent);
      nodes.push({ steps, text: node.textContent,
        typography: [style.fontSize, style.fontFamily, style.fontWeight, style.fontStyle],
        languageSpacing: parent.matches(':lang(ja), :lang(ar)')
          ? [style.lineHeight, style.letterSpacing, style.wordSpacing, style.marginBlockEnd] : null });
    }
    return { nodes, rootFontSize: getComputedStyle(document.documentElement).fontSize, width: innerWidth };
  });
}

async function assertTextSpacing(page, baseline) {
  const observed = await page.evaluate(({ nodes, rootFontSize, width }) => {
    const errors = [], nativeSelectLineHeight = [], counts = { retained: 0, admitted: 0, paragraphs: 0 };
    const minimumRatios = { lineHeight: Infinity, letterSpacing: Infinity, wordSpacing: Infinity, paragraph: Infinity };
    const label = node => node.id || node.tagName.toLowerCase();
    function inspectText(node) {
      const parent = node.parentElement, range = document.createRange();
      range.selectNodeContents(node);
      const rects = [...range.getClientRects()];
      if (!rects.length || rects.every(rect => !rect.width || !rect.height)) errors.push(`text unavailable: ${label(parent)}`);
      for (let ancestor = parent; ancestor; ancestor = ancestor.parentElement) {
        const style = getComputedStyle(ancestor), box = ancestor.getBoundingClientRect();
        if (style.visibility !== 'visible' || style.display === 'none' || Number(style.opacity) === 0) errors.push(`text unavailable: ${label(ancestor)}`);
        // Intentionally scrollable code remains available through its own pane.
        for (const rect of rects) {
          if (['hidden', 'clip'].includes(style.overflowX) && (rect.left < box.left - 1 || rect.right > box.right + 1)) errors.push(`text clipped horizontally: ${label(ancestor)}`);
          if (['hidden', 'clip'].includes(style.overflowY) && (rect.top < box.top - 1 || rect.bottom > box.bottom + 1)) errors.push(`text clipped vertically: ${label(ancestor)}`);
        }
      }
    }
    for (const expected of nodes) {
      const node = expected.steps.reduce((parent, index) => parent?.childNodes[index], document.body);
      if (!node || node.nodeType !== Node.TEXT_NODE || node.textContent !== expected.text) { errors.push('retained text changed or disappeared'); continue; }
      inspectText(node);
      const style = getComputedStyle(node.parentElement);
      const typography = [style.fontSize, style.fontFamily, style.fontWeight, style.fontStyle];
      if (JSON.stringify(typography) !== JSON.stringify(expected.typography)) errors.push(`non-spacing typography changed: ${label(node.parentElement)}`);
      if (expected.languageSpacing && JSON.stringify(expected.languageSpacing) !== JSON.stringify([style.lineHeight, style.letterSpacing, style.wordSpacing, style.marginBlockEnd])) errors.push(`writing-system sample spacing changed: ${label(node.parentElement)}`);
      counts.retained++;
    }
    // Assignment paragraphs contain only a link, a break and code. The text
    // walker reaches those children, so admit the paragraph's own spacing too.
    const elements = new Set(document.querySelectorAll('button, input:not([type="checkbox"]), select, summary, #icons [data-icon-kind="app"] > p'));
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node; (node = walker.nextNode());) {
      const parent = node.parentElement;
      if (!node.textContent.trim() || parent.closest('script, style, noscript, option, legend, .skip')) continue;
      const range = document.createRange(); range.selectNodeContents(node);
      const requiredResult = parent.closest('#package-choice-result:not([hidden]), #local-package-result:not([hidden])');
      if (!requiredResult && (!range.getClientRects().length || getComputedStyle(parent).visibility !== 'visible')) continue;
      inspectText(node);
      elements.add(parent);
    }
    for (const node of elements) {
      if (node.matches(':lang(ja), :lang(ar)') || !node.getClientRects().length) continue;
      const style = getComputedStyle(node), size = parseFloat(style.fontSize);
      for (const [property, minimum] of [['lineHeight', 1.5], ['letterSpacing', .12], ['wordSpacing', .16]]) {
        if (node.tagName === 'SELECT' && property === 'lineHeight' && style.lineHeight === 'normal') {
          nativeSelectLineHeight.push({ id: node.id, fontSize: style.fontSize, computed: style.lineHeight,
            letterSpacing: style.letterSpacing, wordSpacing: style.wordSpacing,
            scope: 'unverified native select metric; not admitted as 1.5' });
          continue;
        }
        minimumRatios[property] = Math.min(minimumRatios[property], parseFloat(style[property]) / size);
        if (!(parseFloat(style[property]) + .02 >= size * minimum)) errors.push(`spacing admission ${property}: ${label(node)} = ${style[property]}`);
      }
      if (node.tagName === 'P') {
        minimumRatios.paragraph = Math.min(minimumRatios.paragraph, parseFloat(style.marginBlockEnd) / size);
        if (!(parseFloat(style.marginBlockEnd) + .02 >= size * 2)) errors.push(`spacing admission paragraph: ${label(node)} = ${style.marginBlockEnd}`);
        counts.paragraphs++;
      }
      counts.admitted++;
    }
    if (getComputedStyle(document.documentElement).fontSize !== rootFontSize || innerWidth !== width) errors.push('spacing changed the root font size or viewport');
    const overflow = [];
    if (document.documentElement.scrollWidth > innerWidth + 1) {
      for (const node of document.querySelectorAll('body *')) {
        const box = node.getBoundingClientRect();
        if (box.width && !node.closest('pre, .skip') && (box.left < -1 || box.right > innerWidth + 1 || node.scrollWidth > node.clientWidth + 1)) {
          overflow.push({ element: label(node), text: node.textContent.trim().slice(0, 90),
            left: box.left, right: box.right, width: box.width, scrollWidth: node.scrollWidth,
            clientWidth: node.clientWidth, font: getComputedStyle(node).fontFamily });
        }
      }
    }
    return { errors: [...new Set(errors)], counts, minimumRatios, nativeSelectLineHeight, width: innerWidth,
      documentWidth: document.documentElement.scrollWidth, overflow: overflow.slice(0, 12) };
  }, baseline);
  assert.deepEqual(observed.errors, [], observed.errors.slice(0, 12).join('\n'));
  assert.equal(observed.counts.retained, baseline.nodes.length);
  assert.ok(observed.counts.retained > 150 && observed.counts.paragraphs > 50, 'Admit the real page, not an empty specimen');
  assert.ok(observed.documentWidth <= observed.width + 1, JSON.stringify(observed));
  return observed;
}

async function spacingKeyboardFocus(page, locator) {
  await locator.focus();
  await page.keyboard.press('Tab'); await page.keyboard.press('Shift+Tab');
  assert.ok(await locator.evaluate(node => document.activeElement === node));
  assert.ok(await locator.isVisible());
  assert.equal(await locator.evaluate(node => getComputedStyle(node).outlineWidth), '2px');
}

async function chooseSpacingPackage(page, appearance) {
  const target = page.locator('#package-target');
  await spacingKeyboardFocus(page, target);
  await page.keyboard.press('Home');
  await page.keyboard.press('ArrowDown'); await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Tab');
  assert.equal(await target.inputValue(), 'equicord');
  assert.equal(await page.evaluate(() => document.activeElement.id), 'package-appearance');
  await page.keyboard.press('Home');
  if (appearance === 'Clair') await page.keyboard.press('ArrowDown');
  await page.keyboard.press('Tab');
  assert.equal(await page.locator('#package-appearance').inputValue(), appearance);
  assert.ok(await page.locator('#package-choice-result').isVisible(), 'chooser did not render the selected package');
  const expected = spacingPackages[appearance];
  assert.equal(await page.locator('#package-choice-file').getAttribute('href'), 'downloads/' + expected.path);
  assert.equal(await page.locator('#package-choice-guide').getAttribute('href'), '#guide-equicord-' + appearance.toLowerCase());
  const text = await page.locator('#package-choice-result').innerText();
  assert.ok(text.includes('Package ' + expected.version) && text.includes(expected.sha256));
  assert.match(await page.locator('#package-choice-status').innerText(), new RegExp('Selected ' + appearance));
  return expected;
}

async function assertSpacingIdentity(page, locator, appearance, expected, { chooser = false } = {}) {
  const normalized = text => text.replace(/\s+/g, ' ').trim();
  const visible = normalized(await locator.innerText());
  const excerpts = [`${appearance} for Equibop ${chooser ? '+' : 'with'} Equicord`, 'Package ' + expected.version,
    'downloads/' + expected.path, expected.sha256,
    await page.locator('#equicord-downloads > p').first().textContent(),
    await page.locator('#equicord-' + appearance.toLowerCase() + ' small').first().textContent(),
    await page.locator('#client-mod-limits').textContent()];
  for (const excerpt of excerpts) assert.ok(visible.includes(normalized(excerpt)), `required package text unavailable: ${excerpt}`);
}

async function spacingPackageJourney(page, appearance, baseline) {
  const expected = await chooseSpacingPackage(page, appearance);
  const assertAppearance = async () => assert.equal(await page.locator('html').getAttribute('data-theme'), appearance);
  await assertAppearance();
  await assertSpacingIdentity(page, page.locator('#package-choice-result'), appearance, expected, { chooser: true });
  await assertTextSpacing(page, baseline);
  await spacingKeyboardFocus(page, page.locator('#package-choice-guide'));
  await page.keyboard.press('Enter');
  await waitForGuideDestination(page, 'guide-equicord-' + appearance.toLowerCase());
  const guide = page.locator('#guide-equicord-' + appearance.toLowerCase());
  assert.ok((await guide.innerText()).includes(expected.sha256));
  await guide.locator('a[href="#guide-equicord-procedure"]').focus();
  await page.keyboard.press('Enter'); await waitForGuideDestination(page, 'guide-equicord-procedure');
  const procedure = page.locator('#guide-equicord-procedure');
  for (const heading of ['Install', 'Switch', 'Remove and restore']) assert.ok(await procedure.getByRole('heading', { name: heading, exact: true }).isVisible());
  assert.match(await procedure.innerText(), /Open Themes Folder/);
  await assertTextSpacing(page, baseline); await assertAppearance();
  await spacingKeyboardFocus(page, page.locator('#package-choice-file'));
  const [saved] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), page.keyboard.press('Enter')]);
  assert.equal(await saved.failure(), null); assert.equal(saved.suggestedFilename(), path.basename(expected.path));
  const chunks = []; for await (const chunk of await saved.createReadStream()) chunks.push(chunk);
  const bytes = Buffer.concat(chunks);
  assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), expected.sha256);
  const input = page.locator('#local-package-file');
  await spacingKeyboardFocus(page, input);
  await input.setInputFiles({ name: path.basename(expected.path), mimeType: 'text/css', buffer: bytes });
  await waitForPackageState(page, 'matched');
  assert.equal(await page.locator('.local-file-hash code').textContent(), expected.sha256);
  assert.equal(await page.locator('#local-package-result .identified-package').count(), 1);
  assert.equal(await page.locator('#local-package-result .guide-link').getAttribute('href'), '#guide-equicord-' + appearance.toLowerCase());
  await assertSpacingIdentity(page, page.locator('#local-package-result .identified-package'), appearance, expected);
  await assertTextSpacing(page, baseline); await assertAppearance();
  const changed = Buffer.from(bytes); changed[0] ^= 1;
  await input.setInputFiles({ name: path.basename(expected.path), mimeType: 'text/css', buffer: changed });
  await waitForPackageState(page, 'no-match');
  assert.equal(await page.locator('.local-file-hash code').textContent(), crypto.createHash('sha256').update(changed).digest('hex'));
  assert.equal(await page.locator('#local-package-result .identified-package').count(), 0);
  await assertTextSpacing(page, baseline);
  await spacingKeyboardFocus(page, page.locator('#local-package-clear'));
  await page.keyboard.press('Enter'); await waitForPackageState(page, 'idle');
  assert.equal(await input.evaluate(node => node.files.length), 0);
  assert.ok(await page.locator('#local-package-result').isHidden());
  await assertAppearance();
  assert.equal(await page.locator('#package-target').inputValue(), 'equicord');
  assert.equal(await page.locator('#package-appearance').inputValue(), appearance);
  return { path: expected.path, sha256: expected.sha256, guide: 'guide-equicord-' + appearance.toLowerCase(),
    keyboardSelection: true, actualDownload: true, matchedAndChangedBytes: true, clear: true };
}

async function terminalSpacingAdmission(page) {
  const observed = await page.locator('#terminal').evaluate(section => {
    const errors = [], minimumRatios = { lineHeight: Infinity, letterSpacing: Infinity, wordSpacing: Infinity, paragraph: Infinity };
    const nodes = [...section.querySelectorAll('h2, h3, p, code, small, a')];
    let paragraphs = 0;
    for (const node of nodes) {
      const style = getComputedStyle(node), size = parseFloat(style.fontSize);
      const label = node.id || node.closest('[data-ansi]')?.dataset.ansi || node.tagName.toLowerCase();
      if (!node.getClientRects().length || style.visibility !== 'visible' || Number(style.opacity) === 0) errors.push('Terminal spacing text unavailable: ' + label);
      for (const [property, minimum] of [['lineHeight', 1.5], ['letterSpacing', .12], ['wordSpacing', .16]]) {
        minimumRatios[property] = Math.min(minimumRatios[property], parseFloat(style[property]) / size);
        if (!(parseFloat(style[property]) + .02 >= size * minimum)) errors.push(`Terminal spacing admission ${property}: ${label} = ${style[property]}`);
      }
      if (node.tagName === 'P') {
        minimumRatios.paragraph = Math.min(minimumRatios.paragraph, parseFloat(style.marginBlockEnd) / size);
        if (!(parseFloat(style.marginBlockEnd) + .02 >= size * 2)) errors.push('Terminal spacing admission paragraph: ' + label);
        paragraphs++;
      }
    }
    return { errors, nodes: nodes.length, paragraphs, minimumRatios,
      cards: section.querySelectorAll('.terminal-palette').length,
      labels: section.querySelectorAll('.terminal-slot > p').length,
      samples: section.querySelectorAll('.terminal-slot > code').length,
      contexts: section.querySelectorAll('.terminal-slot > small').length,
      schemeNames: section.querySelectorAll('.terminal-palette > p > code').length,
      actions: section.querySelectorAll('#terminal-download, #terminal-checksums, #terminal-guide').length };
  });
  assert.deepEqual(observed.errors, []);
  assert.deepEqual([observed.cards, observed.labels, observed.samples, observed.contexts, observed.schemeNames, observed.actions], [2, 32, 32, 32, 2, 3]);
  assert.ok(observed.nodes > 100 && observed.paragraphs >= 34, 'Admit the real Terminal text and every action');
  return observed;
}

async function terminalSpacingJourney(page, baseline, { javaScriptEnabled = true } = {}) {
  const fragment = JSON.parse(await readFile(path.join(site, 'terminal', terminalFragment), 'utf8'));
  const appearance = await page.locator('html').getAttribute('data-theme');
  const specimens = await checkTerminalSpecimens(page, fragment);
  const admission = await terminalSpacingAdmission(page);
  await spacingKeyboardFocus(page, page.locator('#terminal-preview-link'));
  const acquisition = await terminalKeyboardAcquisition(page);
  await page.goBack();
  await page.waitForURL(acquisition.previewUrl);
  // The guide is a separate plaintext response. Re-admit preview overrides
  // after returning rather than assuming that injected styles or page state persist.
  if (javaScriptEnabled) {
    if (await page.locator('html').evaluate(node => getComputedStyle(node).fontSize) !== baseline.rootFontSize) {
      await page.addStyleTag({ content: `html { font-size: ${baseline.rootFontSize}; }` });
    }
    await page.getByRole('button', { name: appearance, exact: true }).focus();
    await page.keyboard.press('Enter');
    await page.addStyleTag({ content: textSpacingOverride });
  }
  assert.equal(await page.locator('html').getAttribute('data-theme'), appearance);
  await assertTextSpacing(page, baseline);
  const returnedAdmission = await terminalSpacingAdmission(page);
  await checkTerminalSpecimens(page, fragment);
  return { ...acquisition, appearances: specimens.map(card => card.appearance), labeledSlots: 32, admission,
    returnedAdmission, returnedToPreview: true, previewOverridesReadmitted: true, nativeTerminalVerified: false };
}

test('text spacing alone preserves content and the keyboard package journey in both appearances', async () => {
  for (const appearance of ['Obscur', 'Clair']) {
    const { context, page, consoleErrors } = await pageFor();
    try {
      await page.getByRole('button', { name: appearance, exact: true }).focus(); await page.keyboard.press('Enter');
      const baseline = await spacingContentBaseline(page);
      assert.equal(baseline.rootFontSize, '16px'); assert.equal(baseline.width, 1280);
      await page.addStyleTag({ content: textSpacingOverride });
      const admission = await assertTextSpacing(page, baseline);
      await checkIconGallery(page);
      const journey = await spacingPackageJourney(page, appearance, baseline);
      const terminal = await terminalSpacingJourney(page, baseline);
      assert.deepEqual(consoleErrors, []);
      results.scenarios.push({ name: 'text spacing only', appearance, status: 'passed', admission, journey, terminal,
        scope: 'four spacing overrides at unchanged default typography; English text, not native application or full WCAG acceptance' });
    } finally { await context.close(); }
  }
});

test('text spacing with narrow layout and enlarged fallback text is separate additional stress', async () => {
  for (const scenario of [{ width: 390, scale: 100, missingFont: false }, { width: 320, scale: 200, missingFont: true }]) {
    for (const appearance of ['Obscur', 'Clair']) {
      const { context, page, consoleErrors } = await pageFor({ viewport: { width: scenario.width, height: 844 }, missingFont: scenario.missingFont });
      try {
        if (scenario.scale === 200) await page.addStyleTag({ content: 'html { font-size: 200%; }' });
        await page.getByRole('button', { name: appearance, exact: true }).focus(); await page.keyboard.press('Enter');
        const baseline = await spacingContentBaseline(page);
        assert.equal(baseline.rootFontSize, scenario.scale === 200 ? '32px' : '16px');
        await page.addStyleTag({ content: textSpacingOverride });
        const admission = await assertTextSpacing(page, baseline);
        await checkIconGallery(page);
        const journey = await spacingPackageJourney(page, appearance, baseline);
        const terminal = await terminalSpacingJourney(page, baseline);
        assert.deepEqual(consoleErrors, []);
        results.scenarios.push({ name: 'text spacing additional responsive stress', appearance, ...scenario, status: 'passed', admission, journey, terminal,
          scope: 'narrow viewport and optional root-font enlargement, not browser zoom or spacing-only conformance' });
      } finally { await context.close(); }
    }
  }
});

test('text spacing keeps the no-script catalog and keyboard installation routes readable', async () => {
  const { context, page, consoleErrors } = await pageFor({ javaScriptEnabled: false });
  try {
    await setIconHistoryOpen(page, true);
    const baseline = await spacingContentBaseline(page);
    // Loading CSS does not depend on page script or a script-driven style-load
    // promise. Preserve the real script-disabled route throughout this check.
    await page.route('**/preview.css', async route => route.fulfill({ contentType: 'text/css',
      body: await readFile(path.join(site, 'preview.css'), 'utf8') + textSpacingOverride }));
    await page.reload();
    await setIconHistoryOpen(page, true);
    const admission = await assertTextSpacing(page, baseline);
    await assertIconHistoryLayout(page, { spacing: true });
    await checkIconGallery(page);
    assert.ok(await page.locator('#package-chooser').isHidden());
    assert.ok(await page.locator('#local-package-checker').isHidden());
    for (const appearance of ['Obscur', 'Clair']) {
      assert.ok(await page.locator(`.palette[data-palette="${appearance}"]`).isVisible());
      const expected = spacingPackages[appearance], card = page.locator('#equicord-' + appearance.toLowerCase());
      await spacingKeyboardFocus(page, card.locator('.guide-link')); await page.keyboard.press('Enter');
      await waitForGuideDestination(page, 'guide-equicord-' + appearance.toLowerCase());
      assert.ok((await page.locator('#guide-equicord-' + appearance.toLowerCase()).innerText()).includes(expected.sha256));
      await spacingKeyboardFocus(page, card.locator('a[download]'));
      const [saved] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), page.keyboard.press('Enter')]);
      const chunks = []; for await (const chunk of await saved.createReadStream()) chunks.push(chunk);
      assert.equal(await saved.failure(), null);
      assert.equal(crypto.createHash('sha256').update(Buffer.concat(chunks)).digest('hex'), expected.sha256);
    }
    const terminal = await terminalSpacingJourney(page, baseline, { javaScriptEnabled: false });
    await assertTextSpacing(page, baseline);
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'text spacing no-script static routes', status: 'passed', admission, terminal,
      scope: 'default reading appearance and both static palettes, not an operable no-script appearance switch' });
  } finally { await context.close(); }
});

test('text spacing qualification rejects missing overrides, collapsed assignment spacing, clipped prose and an inert chooser', async () => {
  for (const fault of ['word-spacing', 'gallery-paragraph-margin', 'clipped-prose', 'inert-chooser']) {
    const { context, page } = await pageFor({ setup: async context => {
      if (fault !== 'inert-chooser') return;
      const source = await readFile(path.join(site, 'preview.js'), 'utf8');
      const listener = "target.addEventListener('change', updatePackageChoice);";
      assert.equal(source.split(listener).length, 2, 'The controlled fault must target the real listener');
      await context.route('**/preview.js', route => route.fulfill({ contentType: 'text/javascript', body: source.replace(listener, '') }));
    } });
    try {
      const baseline = await spacingContentBaseline(page);
      await page.addStyleTag({ content: fault === 'word-spacing' ? textSpacingOverride.replace('word-spacing: .16em !important;', '') : textSpacingOverride });
      if (fault === 'word-spacing') await assert.rejects(assertTextSpacing(page, baseline), /spacing admission wordSpacing/);
      if (fault === 'gallery-paragraph-margin') {
        const paragraph = page.locator('#icons [data-icon-function="youtube"] > p');
        await paragraph.evaluate(node => node.style.setProperty('margin-block-end', '0px', 'important'));
        assert.equal(await paragraph.evaluate(node => getComputedStyle(node).marginBlockEnd), '0px');
        await assert.rejects(assertTextSpacing(page, baseline), /spacing admission paragraph: p/);
        await paragraph.evaluate(node => node.style.removeProperty('margin-block-end'));
        await assertTextSpacing(page, baseline);
      }
      if (fault === 'clipped-prose') {
        await chooseSpacingPackage(page, 'Obscur');
        const clipping = await page.addStyleTag({ content: '#package-choice-result p { height: 1px !important; overflow: hidden !important; }' });
        await assert.rejects(assertTextSpacing(page, baseline), /text clipped vertically/);
        await clipping.evaluate(node => node.remove());
        await page.addStyleTag({ content: '#package-choice-result .package-choice-path { display: none !important; }' });
        await assert.rejects(assertTextSpacing(page, baseline), /text unavailable/);
        await assert.rejects(assertSpacingIdentity(page, page.locator('#package-choice-result'), 'Obscur', spacingPackages.Obscur, { chooser: true }), /required package text unavailable/);
      }
      if (fault === 'inert-chooser') {
        await assertTextSpacing(page, baseline);
        await assert.rejects(chooseSpacingPackage(page, 'Obscur'), /chooser did not render/);
      }
      results.scenarios.push({ name: 'text spacing controlled oracle failure', fault, status: 'rejected as expected', scope: 'disposable harness fault, not a product defect' });
    } finally { await context.close(); }
  }
});

test('text spacing Terminal qualification rejects a hidden sample and altered downloaded ZIP bytes', async () => {
  for (const fault of ['hidden-terminal-sample', 'altered-terminal-zip']) {
    const { context, page, consoleErrors } = await pageFor();
    const downloaded = [];
    page.on('download', download => downloaded.push({ filename: download.suggestedFilename(), url: download.url() }));
    try {
      const baseline = await spacingContentBaseline(page);
      await page.addStyleTag({ content: textSpacingOverride });
      await assertTextSpacing(page, baseline);
      if (fault === 'hidden-terminal-sample') {
        const hiding = await page.addStyleTag({ content: '#terminal .terminal-palette[data-palette="Clair"] .terminal-slot[data-ansi="red"] > code { display: none !important; }' });
        await assert.rejects(terminalSpacingJourney(page, baseline), /Terminal specimen text unavailable/);
        await hiding.evaluate(node => node.remove());
        await terminalSpacingAdmission(page);
        await checkTerminalSpecimens(page, JSON.parse(await readFile(path.join(site, 'terminal', terminalFragment), 'utf8')));
      } else {
        // Change only this run's temporary served ZIP. Keep its independent
        // checksums and scheme fragment intact, then restore the fixture in finally.
        assert.ok(site.startsWith(temp + path.sep), 'Fault injection must stay inside the owned temporary preview');
        const fixtureArchive = path.join(site, 'terminal', terminalArchive);
        const original = await readFile(fixtureArchive), altered = Buffer.from(original);
        const checksums = await readFile(path.join(site, 'terminal', 'SHA256SUMS'));
        const fragment = await readFile(path.join(site, 'terminal', terminalFragment));
        altered[0] ^= 1;
        try {
          await writeFile(fixtureArchive, altered);
          assert.deepEqual(await readFile(fixtureArchive), altered, 'The controlled fixture fault must actually be present');
          await assert.rejects(terminalSpacingJourney(page, baseline), /Terminal checksum mismatch for Clair-Obscur-Windows-Terminal-0\.1\.0\.zip/);
          assert.deepEqual(downloaded.map(download => download.url), [origin + '/terminal/' + terminalArchive, origin + '/terminal/SHA256SUMS'], 'Reject bytes acquired by the real keyboard download controls');
          assert.deepEqual(await readFile(path.join(site, 'terminal', 'SHA256SUMS')), checksums);
          assert.deepEqual(await readFile(path.join(site, 'terminal', terminalFragment)), fragment);
        } finally { await writeFile(fixtureArchive, original); }
        assert.deepEqual(await readFile(fixtureArchive), original, 'Restore the owned fixture after the controlled failure');
      }
      assert.deepEqual(consoleErrors, []);
      results.scenarios.push({ name: 'text spacing controlled Terminal oracle failure', fault, status: 'rejected as expected',
        actualDownloads: downloaded, fixtureRestored: true,
        scope: 'disposable hidden sample or changed served fixture bytes, not a product defect' });
    } finally { await context.close(); }
  }
});

async function checkLocalPackageIdentification(page, manifest, payloads, { delivery, textScale = 100 }) {
  const requests = [], downloads = [], identified = [], guides = new Set();
  const onRequest = request => requests.push(request.url());
  const onDownload = download => downloads.push(download.suggestedFilename());
  page.on('request', onRequest);
  page.on('download', onDownload);
  try {
    assert.ok(await page.locator('#local-package-checker').isVisible());
    await waitForPackageState(page, 'idle');
    assert.equal(await page.locator('#local-package-status').getAttribute('role'), 'status');
    const bound = Math.max(...manifest.downloads.map(item => manifest.files.find(record => record.path === item.path).bytes));
    assert.match(await page.locator('#local-package-bound').textContent(), new RegExp(bound.toLocaleString('en-US')));
    await page.locator('#package-target').selectOption('brave');
    await page.locator('#package-appearance').selectOption('Clair');
    await page.getByRole('button', { name: 'Clair', exact: true }).click();
    const before = await packageCheckerState(page);
    const input = page.locator('#local-package-file');
    await input.focus();
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'local-package-clear');
    await page.keyboard.press('Shift+Tab');
    assert.equal(await input.evaluate(node => getComputedStyle(node).outlineWidth), '2px');
    for (const { item, file } of payloads) {
      const bytes = await readFile(file);
      const record = manifest.files.find(record => record.path === item.path);
      const expectedHash = crypto.createHash('sha256').update(bytes).digest('hex');
      assert.equal(expectedHash, record.sha256);
      const expected = manifest.downloads.filter(choice => manifest.files.find(record => record.path === choice.path).sha256 === expectedHash)
        .flatMap(choice => (choice.platform === 'opera-gx' ? ['Clair', 'Obscur'] : [choice.name])
          .map(appearance => ({ choice, anchor: `guide-${choice.platform}-${appearance.toLowerCase()}` })));
      await input.focus();
      const url = page.url();
      await input.setInputFiles(file);
      await waitForPackageState(page, 'matched');
      assert.equal(page.url(), url, 'Identification must not navigate');
      assert.equal(await page.evaluate(() => document.activeElement.id), 'local-package-file');
      assert.equal(await page.locator('.local-file-hash code').textContent(), expectedHash);
      const matches = page.locator('#local-package-result .identified-package');
      assert.equal(await matches.count(), expected.length);
      assert.deepEqual((await matches.locator('.guide-link').evaluateAll(links => links.map(link => link.getAttribute('href')))).sort(),
        expected.map(reference => '#' + reference.anchor).sort());
      for (const { choice, anchor } of expected) {
        const match = matches.filter({ has: page.locator(`a.guide-link[href="#${anchor}"]`) });
        const identity = await match.textContent();
        assert.ok(identity.includes('Package ' + choice.version));
        assert.ok(identity.includes(record.sha256));
        assert.equal(await match.locator('.identified-package-path code').textContent(), 'downloads/' + choice.path);
        assert.match(identity, /Native acceptance pending/);
        assert.ok(identity.includes(await page.locator(`#${choice.platform}-downloads > p`).first().textContent()));
        if (['equicord', 'vencord', 'betterdiscord'].includes(choice.platform)) assert.match(identity, /not Discord-endorsed/);
        const link = match.locator('.guide-link');
        await link.focus();
        await page.keyboard.press('Enter');
        await waitForGuideDestination(page, anchor);
        assert.ok(await page.locator('#' + anchor).isVisible());
        guides.add(anchor);
      }
      const geometry = await page.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth }));
      assert.ok(geometry.document <= geometry.width + 1, JSON.stringify({ textScale, ...geometry }));
      assert.deepEqual(await packageCheckerState(page), before);
      identified.push({ path: item.path, sha256: expectedHash, guides: expected.map(reference => reference.anchor) });
    }
    assert.equal(identified.length, 13);
    assert.equal(guides.size, 18);
    const chrome = payloads.find(payload => payload.item.platform === 'chrome' && payload.item.name === 'Clair');
    const renamed = path.join(temp, `identification-${delivery}-renamed.bin`);
    await writeFile(renamed, await readFile(chrome.file));
    await input.focus();
    const url = page.url();
    await input.setInputFiles(renamed);
    await waitForPackageState(page, 'matched');
    assert.equal(await page.locator('#local-package-result .identified-package').count(), 3);
    const exact = await readFile(chrome.file);
    await input.setInputFiles({ name: '<img src=x onerror="throw 1">.bin', mimeType: 'application/octet-stream', buffer: exact });
    await waitForPackageState(page, 'matched');
    assert.match(await page.locator('#local-package-selection').textContent(), /<img src=x/);
    assert.equal(await page.locator('#local-package-selection img').count(), 0);
    const changed = Buffer.from(exact);
    changed[0] ^= 1;
    for (const bytes of [changed, Buffer.from('an unrelated local file'), Buffer.alloc(0), Buffer.alloc(bound, 19)]) {
      await input.setInputFiles({ name: 'unknown-package.zip', mimeType: 'application/octet-stream', buffer: bytes });
      await waitForPackageState(page, 'no-match');
      assert.equal(await page.locator('.local-file-hash code').textContent(), crypto.createHash('sha256').update(bytes).digest('hex'));
      assert.equal(await page.locator('#local-package-result .identified-package').count(), 0);
      assert.match(await page.locator('#local-package-status').textContent(), /computed SHA-256 matches no package referenced/);
    }
    assert.equal(page.url(), url);
    assert.deepEqual(await packageCheckerState(page), before);
    await page.locator('#local-package-clear').focus();
    await page.keyboard.press('Enter');
    await waitForPackageState(page, 'idle');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'local-package-clear');
    assert.equal(await input.evaluate(node => node.files.length), 0);
    assert.ok(await page.locator('#local-package-result').isHidden());
    assert.equal(await page.locator('#local-package-result').textContent(), '');
    assert.equal(await page.locator('#local-package-selection').textContent(), '');
    assert.equal(await page.locator('#downloads .download-card').count(), 17);
    assert.deepEqual(await packageCheckerState(page), before);
    assert.deepEqual(requests, [], 'Reading, hashing, rendering and guide routing must not request resources');
    assert.deepEqual(downloads, [], 'Identification must not start downloads');
    return { delivery, textScale, identified, routes: guides.size, renamed: 'same bytes matched all Chrome aliases',
      changed: 'same size with a changed byte computed no match', unknown: 'small, empty and bound-sized computed no match',
      filename: 'plain text', storage: 'unchanged', requests, downloads, focus: 'preserved', clear: 'passed' };
  } finally {
    page.off('request', onRequest);
    page.off('download', onDownload);
  }
}

test('actual public package downloads identify all captured guides locally without filename inference', async () => {
  const payloads = [];
  let manifest;
  for (const name of ['Clair', 'Obscur', 'Clair and Obscur']) {
    const { context, page, consoleErrors } = await pageFor();
    try {
      manifest = await (await context.request.get(origin + '/downloads/artifact-manifest.json')).json();
      const distinct = manifest.downloads.filter((item, index, items) => items.findIndex(choice => choice.path === item.path) === index);
      for (const item of distinct.filter(item => item.name === name)) {
        const file = path.join(temp, 'identified-public', ...item.path.split('/'));
        await mkdir(path.dirname(file), { recursive: true });
        const link = page.locator(`#${item.platform}-downloads a.button[download][href="downloads/${item.path}"]`);
        const [download] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), link.click()]);
        assert.equal(await download.failure(), null);
        await download.saveAs(file);
        assert.equal(page.url(), origin + '/');
        payloads.push({ item, file });
      }
      assert.deepEqual(consoleErrors, []);
    } finally { await context.close(); }
  }
  assert.equal(payloads.length, 13);
  for (const width of [320, 390]) {
    for (const textScale of [100, 200]) {
      const { context, page, consoleErrors } = await pageFor({ viewport: { width, height: 844 } });
      try {
        await page.evaluate(scale => document.documentElement.style.fontSize = scale + '%', textScale);
        const identified = await checkLocalPackageIdentification(page, manifest, payloads, { delivery: 'public', textScale });
        assert.deepEqual(consoleErrors, []);
        results.scenarios.push({ name: 'actual public package identification', status: 'passed', width, ...identified });
      } finally { await context.close(); }
    }
  }
});

test('local package failures remain uncomputed and late work cannot replace a new selection or Clear', async () => {
  const { context, page, consoleErrors } = await pageFor({ viewport: { width: 320, height: 844 } });
  const requests = [], downloads = [];
  try {
    const manifest = await (await context.request.get(origin + '/downloads/artifact-manifest.json')).json();
    const item = manifest.downloads.find(item => item.platform === 'chrome' && item.name === 'Clair');
    const exact = await readFile(path.join(site, 'downloads', ...item.path.split('/')));
    const record = manifest.files.find(record => record.path === item.path);
    const bound = Math.max(...manifest.downloads.map(item => manifest.files.find(record => record.path === item.path).bytes));
    page.on('request', request => requests.push(request.url()));
    page.on('download', download => downloads.push(download.suggestedFilename()));
    await page.evaluate(() => {
      const originalRead = File.prototype.arrayBuffer;
      const subtle = crypto.subtle;
      const originalHash = subtle.digest.bind(subtle);
      const controls = { reads: 0, hashes: 0, holdRead: false, holdHash: false, rejectRead: false, rejectHash: false,
        pendingReads: [], pendingHashes: [] };
      window.packageFixture = controls;
      File.prototype.arrayBuffer = function () {
        controls.reads++;
        if (controls.rejectRead) return Promise.reject(new Error('Controlled read rejection'));
        if (controls.holdRead) {
          controls.holdRead = false;
          return new Promise((resolve, reject) => controls.pendingReads.push({
            resolve: () => originalRead.call(this).then(resolve, reject), reject: () => reject(new Error('Controlled stale read rejection')) }));
        }
        return originalRead.call(this);
      };
      subtle.digest = function (algorithm, bytes) {
        controls.hashes++;
        if (controls.rejectHash) return Promise.reject(new Error('Controlled hash rejection'));
        if (controls.holdHash) {
          controls.holdHash = false;
          return new Promise((resolve, reject) => controls.pendingHashes.push({
            resolve: () => originalHash(algorithm, bytes).then(resolve, reject), reject: () => reject(new Error('Controlled stale hash rejection')) }));
        }
        return originalHash(algorithm, bytes);
      };
    });
    const input = page.locator('#local-package-file');
    await input.focus();
    const before = await packageCheckerState(page), url = page.url();
    const matched = () => input.setInputFiles({ name: 'current-package.bin', mimeType: 'application/octet-stream', buffer: exact });
    const snapshot = () => page.locator('#local-package-checker').evaluate(node => ({
      state: node.dataset.state, status: node.querySelector('#local-package-status').textContent,
      result: node.querySelector('#local-package-result').textContent, hidden: node.querySelector('#local-package-result').hidden,
      selection: node.querySelector('#local-package-selection').textContent }));
    const settle = () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    async function waitPending(kind) {
      const waiting = await page.waitForFunction(name => window.packageFixture[name].length === 1, kind, { timeout: 2000 });
      await waiting.dispose();
    }
    async function startPending(kind) {
      await page.evaluate(name => window.packageFixture[name] = true, kind === 'pendingReads' ? 'holdRead' : 'holdHash');
      await input.setInputFiles({ name: 'older-package.bin', mimeType: 'application/octet-stream', buffer: Buffer.from('older bytes') });
      await waitPending(kind);
      await waitForPackageState(page, 'checking');
      assert.ok(await page.locator('#local-package-result').isHidden());
      assert.equal(await page.locator('#local-package-result').textContent(), '');
      assert.ok(await input.isEnabled());
      assert.ok(await page.locator('#local-package-clear').isEnabled());
    }
    async function release(kind, method) {
      await page.evaluate(async ({ kind, method }) => {
        await window.packageFixture[kind].shift()[method]();
      }, { kind, method });
      await settle();
    }
    const checks = [];
    // Superseded success and rejection in both await phases must stay silent.
    for (const kind of ['pendingReads', 'pendingHashes']) {
      for (const method of ['resolve', 'reject']) {
        await startPending(kind);
        await matched();
        await waitForPackageState(page, 'matched');
        assert.equal(await page.locator('.local-file-hash code').textContent(), record.sha256);
        const current = await snapshot();
        const hashes = await page.evaluate(() => window.packageFixture.hashes);
        await release(kind, method);
        assert.deepEqual(await snapshot(), current);
        assert.equal(await page.evaluate(() => window.packageFixture.hashes), hashes,
          'An obsolete read must not start another hash');
        checks.push({ kind, method, replacement: 'matched selection', status: 'passed' });
      }
    }
    for (const replacement of ['oversize', 'clear', 'empty-selection']) {
      await startPending('pendingReads');
      const reads = await page.evaluate(() => window.packageFixture.reads);
      if (replacement === 'oversize') {
        await input.setInputFiles({ name: 'complete-kit.zip', mimeType: 'application/zip', buffer: Buffer.alloc(bound + 1) });
        await waitForPackageState(page, 'size-rejected');
        assert.equal(await page.evaluate(() => window.packageFixture.reads), reads);
        assert.match(await page.locator('#local-package-status').textContent(), /not read and no digest was computed/);
      } else if (replacement === 'clear') {
        await page.locator('#local-package-clear').focus();
        await page.keyboard.press('Enter');
        await waitForPackageState(page, 'idle');
        assert.equal(await page.evaluate(() => document.activeElement.id), 'local-package-clear');
      } else {
        await input.setInputFiles([]);
        await waitForPackageState(page, 'idle');
      }
      const current = await snapshot();
      const hashes = await page.evaluate(() => window.packageFixture.hashes);
      await release('pendingReads', 'resolve');
      assert.deepEqual(await snapshot(), current);
      assert.equal(await page.evaluate(() => window.packageFixture.hashes), hashes);
      checks.push({ kind: 'pendingReads', method: 'resolve', replacement, status: 'passed' });
    }
    // The Clear generation also owns a pending hash and its later rejection.
    for (const method of ['resolve', 'reject']) {
      await startPending('pendingHashes');
      await page.locator('#local-package-clear').click();
      await waitForPackageState(page, 'idle');
      const current = await snapshot();
      await release('pendingHashes', method);
      assert.deepEqual(await snapshot(), current);
      checks.push({ kind: 'pendingHashes', method, replacement: 'Clear', status: 'passed' });
    }
    for (const [fixture, state, message] of [['rejectRead', 'read-failed', /No digest was computed/],
      ['rejectHash', 'hash-failed', /No digest comparison was made/]]) {
      await matched();
      await waitForPackageState(page, 'matched');
      await page.evaluate(name => window.packageFixture[name] = true, fixture);
      await input.setInputFiles({ name: 'failure.bin', mimeType: 'application/octet-stream', buffer: exact });
      await waitForPackageState(page, state);
      assert.match(await page.locator('#local-package-status').textContent(), message);
      assert.ok(await page.locator('#local-package-result').isHidden());
      assert.equal(await page.locator('#local-package-result').textContent(), '');
      await page.evaluate(name => window.packageFixture[name] = false, fixture);
      await matched();
      await waitForPackageState(page, 'matched');
      checks.push({ failure: state, recovery: 'matched', status: 'passed' });
    }
    await page.evaluate(() => {
      window.savedCrypto = Object.getOwnPropertyDescriptor(window, 'crypto');
      Object.defineProperty(window, 'crypto', { configurable: true, value: undefined });
    });
    const reads = await page.evaluate(() => window.packageFixture.reads);
    await matched();
    await waitForPackageState(page, 'unavailable');
    assert.match(await page.locator('#local-package-status').textContent(), /No digest was computed/);
    assert.equal(await page.evaluate(() => window.packageFixture.reads), reads);
    assert.ok(await page.locator('#local-package-result').isHidden());
    await page.evaluate(() => {
      if (window.savedCrypto) Object.defineProperty(window, 'crypto', window.savedCrypto);
      else delete window.crypto;
    });
    await matched();
    await waitForPackageState(page, 'matched');
    await input.focus();
    assert.equal(await page.evaluate(() => document.activeElement.id), 'local-package-file');
    assert.equal(page.url(), url);
    assert.deepEqual(await packageCheckerState(page), before);
    assert.deepEqual(requests, []);
    assert.deepEqual(downloads, []);
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'local package controlled failures and stale async ownership', status: 'passed',
      checks, oversize: 'rejected before read', cryptoUnavailable: 'no read, recovered', requests, downloads });
  } finally { await context.close(); }
});

test('incomplete captured package metadata is unavailable rather than a computed no match', async () => {
  for (const defect of ['size', 'hash', 'route']) {
    const { context, page, consoleErrors } = await pageFor({ setup: async (_context, fixturePage) => {
      await fixturePage.route('**/preview.js', async route => {
        const script = await readFile(path.join(site, 'preview.js'), 'utf8');
        const change = defect === 'size' ? 'document.querySelector("#chrome-clair").dataset.packageBytes = "-1";'
          : defect === 'hash' ? 'document.querySelector("#guide-chrome-clair .package-hash code").textContent = "not a digest";'
            : 'document.querySelector("#chrome-clair .guide-link").remove();';
        await route.fulfill({ contentType: 'text/javascript', body: change + '\n' + script });
      });
    } });
    try {
      await waitForPackageState(page, 'unavailable');
      assert.ok(await page.locator('#local-package-file').isDisabled());
      assert.match(await page.locator('#local-package-status').textContent(), /references are incomplete. No digest was computed/);
      assert.equal(await page.locator('#local-package-result').textContent(), '');
      assert.ok(await page.locator('#local-package-result').isHidden());
      assert.deepEqual(consoleErrors, []);
      results.scenarios.push({ name: 'invalid local package reference fixture', status: 'passed', defect, result: 'unavailable, uncomputed' });
    } finally { await context.close(); }
  }
});

async function checkPackageChooser(page, manifest, { delivery, textScale = 100 }) {
  const requests = [], downloads = [], routes = [];
  const onRequest = request => requests.push(request.url());
  const onDownload = download => downloads.push(download.suggestedFilename());
  page.on('request', onRequest);
  page.on('download', onDownload);
  try {
    assert.ok(await page.locator('#package-chooser').isVisible());
    assert.equal(await page.locator('#package-target').inputValue(), '');
    assert.equal(await page.locator('#package-appearance').inputValue(), 'Obscur');
    assert.ok(await page.locator('#package-choice-result').isHidden());
    // Exercise native selects with actual keyboard input before the matrix.
    await page.locator('#package-target').focus();
    await page.keyboard.press('Tab');
    await page.keyboard.press('Shift+Tab');
    assert.equal(await page.locator('#package-target').evaluate(node => getComputedStyle(node).outlineWidth), '2px');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Tab');
    assert.equal(await page.locator('#package-target').inputValue(), 'chrome');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Tab');
    assert.equal(await page.locator('#package-appearance').inputValue(), 'Clair');
    const selectedHref = await page.locator('#package-choice-file').getAttribute('href');
    for (const readingAppearance of ['Obscur', 'Clair']) {
      await page.getByRole('button', { name: readingAppearance, exact: true }).focus();
      await page.keyboard.press('Enter');
      assert.equal(await page.locator('#package-appearance').inputValue(), 'Clair');
      assert.equal(await page.locator('#package-target').inputValue(), 'chrome');
      assert.equal(await page.locator('#package-choice-file').getAttribute('href'), selectedHref);
    }
    const records = new Map(manifest.files.map(item => [item.path, item]));
    for (const target of [...new Set(manifest.downloads.map(item => item.platform))]) {
      for (const appearance of ['Clair', 'Obscur']) {
        const item = manifest.downloads.find(item => item.platform === target && (target === 'opera-gx' || item.name === appearance));
        const record = records.get(item.path);
        const readingBefore = await page.locator('html').getAttribute('data-theme');
        await page.locator('#package-target').selectOption(target);
        await page.locator('#package-appearance').selectOption(appearance);
        assert.equal(await page.locator('html').getAttribute('data-theme'), readingBefore);
        const result = page.locator('#package-choice-result');
        assert.ok(await result.isVisible());
        assert.equal(await page.locator('#package-choice-file').getAttribute('href'), 'downloads/' + item.path);
        assert.match(await page.locator('#package-choice-file').textContent(), delivery === 'portable' ? /^Open included / : /^Download /);
        assert.equal(await result.locator('.package-choice-path code').textContent(), 'downloads/' + item.path);
        const identity = await result.textContent();
        assert.ok(identity.includes('Package ' + item.version));
        assert.ok(identity.includes(record.sha256));
        assert.ok(identity.includes('Native acceptance pending'));
        assert.ok(identity.includes(await page.locator(`#${target}-downloads > p`).first().textContent()));
        if (target === 'opera-gx') assert.match(identity, /pairs Clair Light with Obscur Dark/);
        if (['equicord', 'vencord', 'betterdiscord'].includes(target)) assert.match(identity, /not Discord-endorsed/);
        assert.match(await page.locator('#package-choice-status').textContent(), new RegExp('Selected ' + appearance));
        const anchor = `guide-${target}-${appearance.toLowerCase()}`;
        assert.equal(await page.locator('#package-choice-guide').getAttribute('href'), '#' + anchor);
        await page.locator('#package-choice-guide').focus();
        await page.keyboard.press('Enter');
        await waitForGuideDestination(page, anchor);
        assert.ok(await page.locator('#' + anchor).isVisible());
        const geometry = await page.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth }));
        assert.ok(geometry.document <= geometry.width + 1, JSON.stringify({ textScale, ...geometry }));
        routes.push({ target, appearance, path: item.path, guide: anchor, sha256: record.sha256 });
      }
    }
    assert.equal(routes.length, 18);
    assert.equal(new Set(routes.map(route => route.path)).size, 13);
    assert.deepEqual(downloads, [], 'Selection and guide routing cannot start downloads');
    assert.deepEqual(requests, [], 'Selection and local guide routing cannot request resources');
    await page.locator('#package-target').selectOption('');
    assert.ok(await page.locator('#package-choice-result').isHidden());
    assert.equal(await page.locator('#package-choice-file, #package-choice-guide').count(), 0);
    assert.match(await page.locator('#package-choice-status').textContent(), /Choose a target/);
    assert.equal(await page.locator('#downloads .download-card').count(), 17);
    return { delivery, textScale, routes, nativeSelectKeyboard: 'passed', readingAppearanceIndependent: true,
      selectionRequests: requests, selectionDownloads: downloads, explicitTargetReset: 'passed' };
  } finally { page.off('request', onRequest); page.off('download', onDownload); }
}

test('explicit target and package appearance chooser preserves every route and static fallback', async () => {
  for (const width of [320, 390]) {
    for (const textScale of [100, 200]) {
      const { context, page, consoleErrors } = await pageFor({ viewport: { width, height: 844 } });
      try {
        if (textScale === 200) await page.evaluate(() => document.documentElement.style.fontSize = '200%');
        const manifest = await (await context.request.get(origin + '/downloads/artifact-manifest.json')).json();
        const routing = await checkPackageChooser(page, manifest, { delivery: 'public', textScale });
        assert.deepEqual(consoleErrors, []);
        results.scenarios.push({ name: 'explicit public target/package-appearance chooser', status: 'passed', width, ...routing });
      } finally { await context.close(); }
    }
  }
  const { context, page, consoleErrors } = await pageFor({ viewport: { width: 390, height: 844 } });
  try {
    const manifest = await (await context.request.get(origin + '/downloads/artifact-manifest.json')).json();
    for (const [target, appearance] of [['chrome', 'Clair'], ['equicord', 'Obscur']]) {
      await page.locator('#package-target').selectOption(target);
      await page.locator('#package-appearance').selectOption(appearance);
      const item = manifest.downloads.find(item => item.platform === target && item.name === appearance);
      await page.locator('#package-choice-file').focus();
      const [download] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), page.keyboard.press('Enter')]);
      assert.equal(await download.failure(), null);
      const chunks = [];
      for await (const chunk of await download.createReadStream()) chunks.push(chunk);
      const record = manifest.files.find(record => record.path === item.path);
      assert.equal(crypto.createHash('sha256').update(Buffer.concat(chunks)).digest('hex'), record.sha256);
      const anchor = `guide-${target}-${appearance.toLowerCase()}`;
      await page.locator('#package-choice-guide').focus();
      await page.keyboard.press('Enter');
      await waitForGuideDestination(page, anchor);
    }
    assert.deepEqual(consoleErrors, []);
    results.scenarios.push({ name: 'chooser public archive and CSS downloads with keyboard guide return', status: 'passed', choices: 2 });
  } finally { await context.close(); }
  const fallback = await pageFor({ javaScriptEnabled: false, viewport: { width: 320, height: 844 } });
  try {
    assert.ok(await fallback.page.locator('#package-chooser').isHidden());
    assert.ok(await fallback.page.locator('#local-package-checker').isHidden());
    assert.equal(await fallback.page.locator('#downloads .download-card').count(), 17);
    assert.equal(await fallback.page.locator('#downloads .guide-link').count(), 18);
    await fallback.page.locator('#edge-clair .guide-link').focus();
    await fallback.page.keyboard.press('Enter');
    await waitForGuideDestination(fallback.page, 'guide-edge-clair');
    assert.deepEqual(fallback.consoleErrors, []);
    results.scenarios.push({ name: 'chooser progressive enhancement keeps no-script catalog', status: 'passed', width: 320 });
  } finally { await fallback.context.close(); }
});

test('guide destination wait admits delayed navigation and focus without an immediate-read assumption', async () => {
  const { context, page } = await pageFor();
  try {
    await page.setContent('<a id="trigger" href="#destination">Guide</a><section id="destination" tabindex="-1">Destination</section>');
    // Hold the fixture transition behind explicit releases, not a timer.
    await page.locator('#trigger').evaluate(node => node.addEventListener('click', event => event.preventDefault()));
    await page.locator('#trigger').focus();
    await page.keyboard.press('Enter');
    assert.throws(() => assert.equal(new URL(page.url()).hash, '#destination'), { code: 'ERR_ASSERTION' });
    let settled = false;
    const destination = waitForGuideDestination(page, 'destination').then(
      () => { settled = true; return { error: null }; },
      error => ({ error }),
    );
    await page.evaluate(() => history.pushState(null, '', '#destination'));
    await page.waitForURL(url => url.hash === '#destination', { timeout: 2000, waitUntil: 'commit' });
    assert.equal(await page.evaluate(() => document.activeElement.id), 'trigger');
    assert.equal(settled, false, 'Correct fragment without destination focus must remain pending');
    await page.locator('#destination').focus();
    const outcome = await destination;
    if (outcome.error) throw outcome.error;
    assert.equal(new URL(page.url()).hash, '#destination');
    assert.equal(await page.evaluate(() => document.activeElement.id), 'destination');
  } finally { await context.close(); }
});

test('guide destination wait rejects absent navigation, a wrong fragment and wrong focus', async () => {
  for (const scenario of ['absent navigation', 'wrong fragment', 'wrong focus']) {
    const { context, page } = await pageFor();
    try {
      await page.setContent('<a id="trigger" href="#destination">Guide</a><section id="destination" tabindex="-1">Destination</section>');
      await page.locator('#trigger').focus();
      if (scenario === 'wrong fragment') {
        await page.evaluate(() => history.pushState(null, '', '#other'));
        await page.locator('#destination').focus();
      } else if (scenario === 'wrong focus') {
        await page.evaluate(() => history.pushState(null, '', '#destination'));
      }
      await assert.rejects(waitForGuideDestination(page, 'destination', 250), { name: 'TimeoutError' }, scenario);
      assert.equal(await page.evaluate(() => document.activeElement.id), scenario === 'wrong fragment' ? 'destination' : 'trigger');
    } finally { await context.close(); }
  }
});

test('relocated local guides cover every appearance by keyboard without external network or script', async () => {
  for (const javaScriptEnabled of [true, false]) {
    for (const width of [320, 390]) {
      const { context, page, network, consoleErrors } = await pageFor({ javaScriptEnabled, viewport: { width, height: 844 } });
      try {
        const manifest = await (await context.request.get(origin + '/downloads/artifact-manifest.json')).json();
        const records = new Map(manifest.files.map(item => [item.path, item]));
        const links = page.locator('#downloads .guide-link');
        assert.equal(await links.count(), 18, 'Two appearance links for the one paired Opera GX package');
        const appearances = javaScriptEnabled ? ['Obscur', 'Clair'] : ['Obscur'];
        for (const appearance of appearances) {
          if (javaScriptEnabled) {
            await page.getByRole('button', { name: appearance, exact: true }).focus();
            await page.keyboard.press('Enter');
            assert.equal(await page.locator('html').getAttribute('data-theme'), appearance);
          }
          for (const item of manifest.downloads) {
            const names = item.platform === 'opera-gx' ? ['Clair', 'Obscur'] : [item.name];
            const card = page.locator(`#${item.platform}-${item.platform === 'opera-gx' ? 'paired' : item.name.toLowerCase()}`);
            await card.locator('a[download]').focus();
            for (const name of names) {
              // Tab moves from the exact download to its locally bundled guide.
              await page.keyboard.press('Tab');
              const anchor = `guide-${item.platform}-${name.toLowerCase()}`;
              assert.equal(await page.evaluate(() => document.activeElement.getAttribute('href')), '#' + anchor);
              await page.keyboard.press('Enter');
              await waitForGuideDestination(page, anchor);
              assert.equal(new URL(page.url()).hash, '#' + anchor);
              const packageSection = page.locator('#' + anchor);
              assert.ok(await packageSection.isVisible());
              assert.equal(await page.evaluate(() => document.activeElement.id), anchor);
              assert.equal(await packageSection.locator('a[download]').getAttribute('href'), 'downloads/' + item.path);
              assert.ok((await packageSection.textContent()).includes('Package ' + item.version));
              assert.ok((await packageSection.textContent()).includes(records.get(item.path).sha256));
              const guide = page.locator('#guide-' + item.platform);
              for (const heading of ['Prerequisites and status', 'Install', 'Switch', 'Remove and restore', 'Fonts', 'Troubleshooting']) {
                assert.equal(await guide.getByRole('heading', { name: heading, exact: true }).count(), 1);
              }
              const bounds = await guide.evaluate(node => ({ left: node.getBoundingClientRect().left, right: node.getBoundingClientRect().right, width: innerWidth }));
              assert.ok(bounds.left >= -1 && bounds.right <= bounds.width + 1, JSON.stringify(bounds));
              // Resume from this card for the second appearance of the paired file.
              await card.locator(`a.guide-link[href="#${anchor}"]`).focus();
            }
          }
          const geometry = await page.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth }));
          assert.ok(geometry.document <= geometry.width + 1, JSON.stringify(geometry));
        }
        for (const client of ['vencord', 'betterdiscord']) {
          const fontLink = page.locator(`#guide-${client} a[href="#guide-client-fonts"]`);
          await fontLink.focus();
          await page.keyboard.press('Enter');
          await waitForGuideDestination(page, 'guide-client-fonts');
          assert.equal(new URL(page.url()).hash, '#guide-client-fonts');
          assert.equal(await page.evaluate(() => document.activeElement.id), 'guide-client-fonts');
          assert.match(await page.locator('#guide-client-fonts').textContent(), /system sans-serif fallbacks/);
        }
        assert.ok(network.every(url => url.startsWith(origin + '/')), 'Essential guidance cannot require external requests');
        assert.deepEqual(consoleErrors, []);
        assert.deepEqual(failures, []);
        results.scenarios.push({ name: 'relocated complete local target/appearance guides', status: 'passed', width, javaScriptEnabled, pageAppearances: appearances, guideAppearances: 18, externalNetwork: 'blocked', nativeAppsVerified: false });
      } finally { await context.close(); }
    }
  }
});

// Bound each viewport journey separately while retaining both modes and widths.
for (const [javaScriptEnabled, testedWidth] of [[true, 320], [true, 390], [false, 320], [false, 390]]) test(`portable kit downloads, extracts and relocates into a complete offline file page (${javaScriptEnabled ? 'scripted' : 'no-script'}, ${testedWidth}px)`, { timeout: 90000 }, async () => {
  const mode = `${javaScriptEnabled ? 'scripted' : 'no-script'}-${testedWidth}`;
  const modeTemp = path.join(temp, `portable-${mode}`);
  await mkdir(modeTemp);
  const modeEvidence = evidence && path.join(evidence, `portable-${mode}`);
  if (modeEvidence) await mkdir(modeEvidence);
  const archiveName = 'Clair-Obscur-portable-preview.zip';
  const archivePath = path.join(modeTemp, archiveName);
  const checksumPath = path.join(modeTemp, 'portable-SHA256SUMS');
  const extracted = path.join(modeTemp, 'downloaded-kit');
  const relocated = path.join(modeTemp, 'moved-kit', 'preview');
  const { context, page } = await pageFor({ javaScriptEnabled, viewport: { width: 390, height: 844 } });
  let publicManifest;
  const downloadNames = {};
  try {
    publicManifest = await (await context.request.get(origin + '/site-manifest.json')).json();
    for (const [selector, destination] of [['#portable-preview', archivePath], ['#portable-checksums', checksumPath]]) {
      const [download] = await Promise.all([page.waitForEvent('download', { timeout: 5000 }), page.locator(selector).click()]);
      assert.equal(await download.failure(), null);
      const suggested = download.suggestedFilename();
      // Chrome may add .txt to an extensionless text/plain checksum response.
      const acceptedNames = selector === '#portable-checksums'
        ? ['portable-SHA256SUMS', 'portable-SHA256SUMS.txt'] : [archiveName];
      assert.ok(acceptedNames.includes(suggested), suggested);
      downloadNames[selector] = suggested;
      await download.saveAs(destination);
      assert.equal(page.url(), origin + '/');
    }
  } finally { await context.close(); }
  const archiveBytes = await readFile(archivePath);
  const checksum = await readFile(checksumPath, 'utf8');
  const digest = crypto.createHash('sha256').update(archiveBytes).digest('hex');
  assert.equal(checksum, `${digest}  ${archiveName}\n`);
  if (modeEvidence) {
    await writeFile(path.join(modeEvidence, archiveName), archiveBytes);
    await writeFile(path.join(modeEvidence, 'portable-SHA256SUMS'), checksum);
  }
  assert.deepEqual(publicManifest.distribution.portable_kit, {
    archive: archiveName, checksums: 'portable-SHA256SUMS', sha256: digest, bytes: archiveBytes.length,
  });
  // Consume only the actual clicked download. Check ownership and hashes
  // before extracting, then move that complete directory before opening it.
  run(['-c', [
    'import hashlib,json,pathlib,stat,sys,zipfile',
    'archive_path,output=map(pathlib.Path,sys.argv[1:])',
    'with zipfile.ZipFile(archive_path) as archive:',
    ' names=archive.namelist()',
    ' assert names==sorted(set(names)) and archive.testzip() is None',
    ' for info in archive.infolist():',
    '  name=pathlib.PurePosixPath(info.filename)',
    '  assert not name.is_absolute() and ".." not in name.parts and "\\\\" not in info.filename',
    '  assert stat.S_ISREG(info.external_attr >> 16)',
    ' manifest=json.loads(archive.read("site-manifest.json"))',
    ' assert set(manifest["files"])==set(names)-{"site-manifest.json"}',
    ' assert "Clair-Obscur-portable-preview.zip" not in names and "portable-SHA256SUMS" not in names',
    ' for name,digest in manifest["files"].items():',
    '  assert hashlib.sha256(archive.read(name)).hexdigest()==digest',
    ' archive.extractall(output)',
  ].join('\n'), archivePath, extracted]);
  await mkdir(path.dirname(relocated));
  await rename(extracted, relocated);
  const inner = JSON.parse(await readFile(path.join(relocated, 'site-manifest.json'), 'utf8'));
  const packages = JSON.parse(await readFile(path.join(relocated, 'downloads', 'artifact-manifest.json'), 'utf8'));
  const records = new Map(packages.files.map(item => [item.path, item]));
  assert.deepEqual(inner.source, publicManifest.source);
  assert.deepEqual(inner.release, publicManifest.release);
  assert.deepEqual(inner.distribution, { kind: 'portable-kit' });
  assert.equal(packages.downloads.length, 17);
  assert.equal(new Set(packages.downloads.map(item => item.path)).size, 13);
  const requests = [], errors = [], journeys = [], packageJourneys = [], chooserJourneys = [], identificationJourneys = [], iconJourneys = [], terminalJourneys = [];
  const terminalDocument = JSON.parse(await readFile(path.join(relocated, 'terminal', terminalFragment), 'utf8'));
  const includedPayloads = packages.downloads.filter((item, index, items) => items.findIndex(choice => choice.path === item.path) === index)
    .map(item => ({ item, file: path.join(relocated, 'downloads', ...item.path.split('/')) }));
  let closedContexts = 0;
  async function filePage(options) {
    const localContext = await browser.newContext({ serviceWorkers: 'block', ...options });
    try {
      const localPage = await localContext.newPage();
      localPage.on('request', request => requests.push(request.url()));
      localPage.on('pageerror', error => errors.push(String(error)));
      localPage.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
      await localContext.route('**/*', route => {
        if (new URL(route.request().url()).protocol !== 'file:') return route.abort();
        return route.continue();
      });
      await localPage.goto(pathToFileURL(path.join(relocated, 'index.html')).href);
      await localPage.evaluate(() => document.fonts.ready);
      return { localContext, localPage };
    } catch (error) { await localContext.close(); closedContexts++; throw error; }
  }
  for (const width of [testedWidth]) {
    const { localContext, localPage } = await filePage({ javaScriptEnabled, viewport: { width, height: 844 } });
    try {
      assert.match(await localPage.locator('#portable-delivery').textContent(), /extracted portable preview/);
      assert.equal(await localPage.locator('#portable-preview, #portable-checksums').count(), 0);
      assert.equal(await localPage.locator('#downloads .download-card').count(), 17);
      await assertIconPngFallback(localPage);
      const decodedIcons = await checkIconGallery(localPage);
      for (const relative of decodedIcons) {
        const bytes = await readFile(path.join(relocated, ...relative.split('/')));
        assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), inner.files[relative]);
      }
      await localPage.locator('#icon-artwork-download').focus();
      const [iconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await iconDownload.failure(), null);
      assert.equal(iconDownload.suggestedFilename(), path.basename(iconArchive));
      const iconChunks = []; for await (const chunk of await iconDownload.createReadStream()) iconChunks.push(chunk);
      const iconBytes = Buffer.concat(iconChunks), iconDigest = crypto.createHash('sha256').update(iconBytes).digest('hex');
      assert.deepEqual(iconBytes, await readFile(path.join(relocated, ...iconArchive.split('/'))));
      assert.equal(iconDigest, inner.files[iconArchive]);
      assert.equal(await readFile(path.join(relocated, 'icons', 'SVG-SHA256SUMS'), 'utf8'), iconChecksums(iconDigest));
      await setIconHistoryOpen(localPage, true);
      await localPage.locator('#icon-artwork-reading-download').focus();
      const [readingIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await readingIconDownload.failure(), null);
      assert.equal(readingIconDownload.suggestedFilename(), path.basename(readingIconArchive));
      const readingChunks = []; for await (const chunk of await readingIconDownload.createReadStream()) readingChunks.push(chunk);
      const readingIconBytes = Buffer.concat(readingChunks);
      assert.deepEqual(readingIconBytes, await readFile(path.join(relocated, ...readingIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(readingIconBytes).digest('hex'), readingIconDigest);
      assert.equal(inner.files[readingIconArchive], readingIconDigest);
      await localPage.locator('#icon-artwork-study-learning-download').focus();
      const [learningIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await learningIconDownload.failure(), null);
      assert.equal(learningIconDownload.suggestedFilename(), path.basename(learningIconArchive));
      const learningChunks = []; for await (const chunk of await learningIconDownload.createReadStream()) learningChunks.push(chunk);
      const learningIconBytes = Buffer.concat(learningChunks);
      assert.deepEqual(learningIconBytes, await readFile(path.join(relocated, ...learningIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(learningIconBytes).digest('hex'), learningIconDigest);
      assert.equal(inner.files[learningIconArchive], learningIconDigest);
      await localPage.locator('#icon-artwork-running-training-download').focus();
      const [runningIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await runningIconDownload.failure(), null);
      assert.equal(runningIconDownload.suggestedFilename(), path.basename(runningTrainingIconArchive));
      const runningChunks = []; for await (const chunk of await runningIconDownload.createReadStream()) runningChunks.push(chunk);
      const runningIconBytes = Buffer.concat(runningChunks);
      assert.deepEqual(runningIconBytes, await readFile(path.join(relocated, ...runningTrainingIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(runningIconBytes).digest('hex'), runningTrainingIconDigest);
      assert.equal(inner.files[runningTrainingIconArchive], runningTrainingIconDigest);
      await localPage.locator('#icon-artwork-weather-download').focus();
      const [weatherIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await weatherIconDownload.failure(), null);
      assert.equal(weatherIconDownload.suggestedFilename(), path.basename(weatherIconArchive));
      const weatherChunks = []; for await (const chunk of await weatherIconDownload.createReadStream()) weatherChunks.push(chunk);
      const weatherIconBytes = Buffer.concat(weatherChunks);
      assert.deepEqual(weatherIconBytes, await readFile(path.join(relocated, ...weatherIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(weatherIconBytes).digest('hex'), weatherIconDigest);
      assert.equal(inner.files[weatherIconArchive], weatherIconDigest);
      await localPage.locator('#icon-artwork-finance-download').focus();
      const [financeIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await financeIconDownload.failure(), null);
      assert.equal(financeIconDownload.suggestedFilename(), path.basename(financeIconArchive));
      const financeChunks = []; for await (const chunk of await financeIconDownload.createReadStream()) financeChunks.push(chunk);
      const financeIconBytes = Buffer.concat(financeChunks);
      assert.deepEqual(financeIconBytes, await readFile(path.join(relocated, ...financeIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(financeIconBytes).digest('hex'), financeIconDigest);
      assert.equal(inner.files[financeIconArchive], financeIconDigest);
      await localPage.locator('#icon-artwork-travel-download').focus();
      const [travelIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await travelIconDownload.failure(), null);
      assert.equal(travelIconDownload.suggestedFilename(), path.basename(travelIconArchive));
      const travelChunks = []; for await (const chunk of await travelIconDownload.createReadStream()) travelChunks.push(chunk);
      const travelIconBytes = Buffer.concat(travelChunks);
      assert.deepEqual(travelIconBytes, await readFile(path.join(relocated, ...travelIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(travelIconBytes).digest('hex'), travelIconDigest);
      assert.equal(inner.files[travelIconArchive], travelIconDigest);
      await localPage.locator('#icon-artwork-food-order-download').focus();
      const [foodOrderIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await foodOrderIconDownload.failure(), null);
      assert.equal(foodOrderIconDownload.suggestedFilename(), path.basename(foodOrderIconArchive));
      const foodOrderChunks = []; for await (const chunk of await foodOrderIconDownload.createReadStream()) foodOrderChunks.push(chunk);
      const foodOrderIconBytes = Buffer.concat(foodOrderChunks);
      assert.deepEqual(foodOrderIconBytes, await readFile(path.join(relocated, ...foodOrderIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(foodOrderIconBytes).digest('hex'), foodOrderIconDigest);
      assert.equal(inner.files[foodOrderIconArchive], foodOrderIconDigest);
      await localPage.locator('#icon-artwork-everyday-download').focus();
      const [everydayIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await everydayIconDownload.failure(), null);
      assert.equal(everydayIconDownload.suggestedFilename(), path.basename(everydayIconArchive));
      const everydayChunks = []; for await (const chunk of await everydayIconDownload.createReadStream()) everydayChunks.push(chunk);
      const everydayIconBytes = Buffer.concat(everydayChunks);
      assert.deepEqual(everydayIconBytes, await readFile(path.join(relocated, ...everydayIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(everydayIconBytes).digest('hex'), everydayIconDigest);
      assert.equal(inner.files[everydayIconArchive], everydayIconDigest);
      await localPage.locator('#icon-artwork-broad-download').focus();
      const [broadIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await broadIconDownload.failure(), null);
      assert.equal(broadIconDownload.suggestedFilename(), path.basename(broadIconArchive));
      const broadChunks = []; for await (const chunk of await broadIconDownload.createReadStream()) broadChunks.push(chunk);
      const broadIconBytes = Buffer.concat(broadChunks);
      assert.deepEqual(broadIconBytes, await readFile(path.join(relocated, ...broadIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(broadIconBytes).digest('hex'), broadIconDigest);
      assert.equal(inner.files[broadIconArchive], broadIconDigest);
      await localPage.locator('#icon-artwork-companion-download').focus();
      const [companionIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await companionIconDownload.failure(), null);
      assert.equal(companionIconDownload.suggestedFilename(), path.basename(companionIconArchive));
      const companionChunks = []; for await (const chunk of await companionIconDownload.createReadStream()) companionChunks.push(chunk);
      const companionIconBytes = Buffer.concat(companionChunks);
      assert.deepEqual(companionIconBytes, await readFile(path.join(relocated, ...companionIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(companionIconBytes).digest('hex'), companionIconDigest);
      assert.equal(inner.files[companionIconArchive], companionIconDigest);
      await localPage.locator('#icon-artwork-monochrome-download').focus();
      const [monochromeIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await monochromeIconDownload.failure(), null);
      assert.equal(monochromeIconDownload.suggestedFilename(), path.basename(monochromeIconArchive));
      const monochromeChunks = []; for await (const chunk of await monochromeIconDownload.createReadStream()) monochromeChunks.push(chunk);
      const monochromeIconBytes = Buffer.concat(monochromeChunks);
      assert.deepEqual(monochromeIconBytes, await readFile(path.join(relocated, ...monochromeIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(monochromeIconBytes).digest('hex'), monochromeIconDigest);
      assert.equal(inner.files[monochromeIconArchive], monochromeIconDigest);
      await localPage.locator('#icon-artwork-third-app-download').focus();
      const [thirdAppIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await thirdAppIconDownload.failure(), null);
      assert.equal(thirdAppIconDownload.suggestedFilename(), path.basename(thirdAppIconArchive));
      const thirdChunks = []; for await (const chunk of await thirdAppIconDownload.createReadStream()) thirdChunks.push(chunk);
      const thirdAppIconBytes = Buffer.concat(thirdChunks);
      assert.deepEqual(thirdAppIconBytes, await readFile(path.join(relocated, ...thirdAppIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(thirdAppIconBytes).digest('hex'), thirdAppIconDigest);
      assert.equal(inner.files[thirdAppIconArchive], thirdAppIconDigest);
      await localPage.locator('#icon-artwork-second-app-download').focus();
      // Pace actual included-file downloads before the browser's burst limit.
      await new Promise(resolve => setTimeout(resolve, 1100));
      assert.equal(await localPage.evaluate(() => document.activeElement.id), 'icon-artwork-second-app-download');
      const [secondAppIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await secondAppIconDownload.failure(), null);
      assert.equal(secondAppIconDownload.suggestedFilename(), path.basename(secondAppIconArchive));
      const secondAppIconChunks = []; for await (const chunk of await secondAppIconDownload.createReadStream()) secondAppIconChunks.push(chunk);
      const secondAppIconBytes = Buffer.concat(secondAppIconChunks);
      assert.deepEqual(secondAppIconBytes, await readFile(path.join(relocated, ...secondAppIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(secondAppIconBytes).digest('hex'), secondAppIconDigest);
      assert.equal(inner.files[secondAppIconArchive], secondAppIconDigest);
      await localPage.locator('#icon-artwork-first-app-download').focus();
      assert.equal(await localPage.evaluate(() => document.activeElement.id), 'icon-artwork-first-app-download');
      const [firstAppIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await firstAppIconDownload.failure(), null);
      assert.equal(firstAppIconDownload.suggestedFilename(), path.basename(firstAppIconArchive));
      const firstAppIconChunks = []; for await (const chunk of await firstAppIconDownload.createReadStream()) firstAppIconChunks.push(chunk);
      const firstAppIconBytes = Buffer.concat(firstAppIconChunks);
      assert.deepEqual(firstAppIconBytes, await readFile(path.join(relocated, ...firstAppIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(firstAppIconBytes).digest('hex'), firstAppIconDigest);
      assert.equal(inner.files[firstAppIconArchive], firstAppIconDigest);
      await localPage.locator('#icon-artwork-previous-download').focus();
      const [previousIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await previousIconDownload.failure(), null);
      assert.equal(previousIconDownload.suggestedFilename(), path.basename(previousIconArchive));
      const previousIconChunks = []; for await (const chunk of await previousIconDownload.createReadStream()) previousIconChunks.push(chunk);
      const previousIconBytes = Buffer.concat(previousIconChunks);
      assert.deepEqual(previousIconBytes, await readFile(path.join(relocated, ...previousIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(previousIconBytes).digest('hex'), previousIconDigest);
      assert.equal(inner.files[previousIconArchive], previousIconDigest);
      await localPage.locator('#icon-artwork-legacy-download').focus();
      const [legacyIconDownload] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await legacyIconDownload.failure(), null);
      assert.equal(legacyIconDownload.suggestedFilename(), path.basename(legacyIconArchive));
      const legacyIconChunks = []; for await (const chunk of await legacyIconDownload.createReadStream()) legacyIconChunks.push(chunk);
      const legacyIconBytes = Buffer.concat(legacyIconChunks);
      assert.deepEqual(legacyIconBytes, await readFile(path.join(relocated, ...legacyIconArchive.split('/'))));
      assert.equal(crypto.createHash('sha256').update(legacyIconBytes).digest('hex'), legacyIconDigest);
      assert.equal(inner.files[legacyIconArchive], legacyIconDigest);
      iconJourneys.push({ javaScriptEnabled, width, decoded: decodedIcons.length, sha256: iconDigest,
        readingSha256: readingIconDigest, learningSha256: learningIconDigest, weatherSha256: weatherIconDigest, financeSha256: financeIconDigest, travelSha256: travelIconDigest, foodOrderSha256: foodOrderIconDigest, everydaySha256: everydayIconDigest, broadSha256: broadIconDigest, companionSha256: companionIconDigest, monochromeSha256: monochromeIconDigest, secondAppSha256: secondAppIconDigest, firstAppSha256: firstAppIconDigest, previousSha256: previousIconDigest, legacySha256: legacyIconDigest,
        method: 'saved included current and all sixteen preserved SVG archives' });
      const terminalSpecimens = await checkTerminalSpecimens(localPage, terminalDocument);
      await localPage.locator('#terminal-download').focus();
      const [terminalZip] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
      assert.equal(await terminalZip.failure(), null);
      assert.equal(terminalZip.suggestedFilename(), terminalArchive);
      const terminalChunks = []; for await (const chunk of await terminalZip.createReadStream()) terminalChunks.push(chunk);
      await localPage.keyboard.press('Tab');
      assert.equal(await localPage.evaluate(() => document.activeElement.id), 'terminal-checksums');
      const terminalSumUrl = pathToFileURL(path.join(relocated, 'terminal', 'SHA256SUMS')).href;
      let terminalSumText;
      try {
        // Like the included CSS routes below, an extensionless local text
        // file opens in the browser. Qualify that actual consumer behavior.
        await Promise.all([localPage.waitForURL(terminalSumUrl, { timeout: 5000 }), localPage.keyboard.press('Enter')]);
        terminalSumText = await localPage.locator('pre').textContent();
        assert.equal(terminalSumText, await readFile(path.join(relocated, 'terminal', 'SHA256SUMS'), 'utf8'));
      } catch (error) {
        failures.push({ scenario: 'portable Terminal checksum activation', javaScriptEnabled, width,
          pageUrl: localPage.url(), error: error.message, observation: await localPage.evaluate(() => ({
            focusedId: document.activeElement?.id, focusedHref: document.activeElement?.getAttribute('href'),
            bodyText: document.body?.innerText.slice(0, 2400), title: document.title,
          })) });
        throw error;
      }
      const terminalAcquisition = await verifyTerminalDownloads(Buffer.concat(terminalChunks), Buffer.from(terminalSumText, 'utf8'), relocated);
      assert.equal(terminalAcquisition.sha256, inner.files['terminal/' + terminalArchive]);
      await localPage.goBack();
      await localPage.locator('#terminal-checksums').focus();
      await localPage.keyboard.press('Tab');
      assert.equal(await localPage.evaluate(() => document.activeElement.id), 'terminal-guide');
      const terminalGuideUrl = pathToFileURL(path.join(relocated, 'terminal', 'installation.md')).href;
      await Promise.all([localPage.waitForURL(terminalGuideUrl), localPage.keyboard.press('Enter')]);
      const terminalGuide = await readFile(path.join(relocated, 'terminal', 'installation.md'), 'utf8');
      assert.equal((await localPage.locator('body').textContent()).trim(), terminalGuide.trim());
      assert.equal(crypto.createHash('sha256').update(terminalGuide).digest('hex'), inner.files['terminal/installation.md']);
      await localPage.goBack();
      await localPage.evaluate(() => document.fonts.ready);
      terminalJourneys.push({ javaScriptEnabled, width, ...terminalAcquisition, appearances: terminalSpecimens.map(card => card.appearance),
        labeledSlots: 32, checksums: 'opened exact included plaintext and returned', guide: 'opened exact included Markdown and returned',
        method: 'focused archive control, keyboard ZIP acquisition and exact local text routes' });
      if (javaScriptEnabled) {
        chooserJourneys.push({ width, ...await checkPackageChooser(localPage, packages, { delivery: 'portable' }) });
        for (const textScale of [100, 200]) {
          await localPage.evaluate(scale => document.documentElement.style.fontSize = scale + '%', textScale);
          identificationJourneys.push({ width, ...await checkLocalPackageIdentification(localPage, packages, includedPayloads,
            { delivery: 'portable', textScale }) });
        }
        await localPage.evaluate(() => document.documentElement.style.fontSize = '100%');
      } else {
        assert.ok(await localPage.locator('#package-chooser').isHidden());
        assert.ok(await localPage.locator('#local-package-checker').isHidden());
      }
      for (const [appearance, background] of [['Obscur', 'rgb(0, 0, 0)'], ['Clair', 'rgb(255, 255, 255)']]) {
        assert.equal(await localPage.locator(`.palette[data-palette="${appearance}"]`).evaluate(node => getComputedStyle(node).backgroundColor), background);
        if (javaScriptEnabled) {
          await localPage.getByRole('button', { name: appearance, exact: true }).focus();
          await localPage.keyboard.press('Enter');
          assert.equal(await localPage.locator('html').getAttribute('data-theme'), appearance);
        }
      }
      if (javaScriptEnabled) {
        await localPage.locator('#sample-button').focus();
        await localPage.keyboard.press('Enter');
        assert.match(await localPage.locator('#control-status').textContent(), /Control activated/);
      }
      let guideAppearances = 0;
      for (const item of packages.downloads) {
        const card = localPage.locator(`#${item.platform}-${item.platform === 'opera-gx' ? 'paired' : item.name.toLowerCase()}`);
        await card.locator('a[download]').focus();
        for (const name of item.platform === 'opera-gx' ? ['Clair', 'Obscur'] : [item.name]) {
          const anchor = `guide-${item.platform}-${name.toLowerCase()}`;
          await localPage.keyboard.press('Tab');
          assert.equal(await localPage.evaluate(() => document.activeElement.getAttribute('href')), '#' + anchor);
          await localPage.keyboard.press('Enter');
          await waitForGuideDestination(localPage, anchor);
          const section = localPage.locator('#' + anchor);
          assert.ok(await section.isVisible());
          assert.ok((await section.textContent()).includes(records.get(item.path).sha256));
          assert.equal(await section.locator('.local-package-path code').textContent(), 'downloads/' + item.path);
          const guide = localPage.locator('#guide-' + item.platform);
          for (const heading of ['Prerequisites and status', 'Install', 'Switch', 'Remove and restore', 'Fonts', 'Troubleshooting']) {
            assert.equal(await guide.getByRole('heading', { name: heading, exact: true }).count(), 1);
          }
          await card.locator(`a.guide-link[href="#${anchor}"]`).focus();
          guideAppearances++;
        }
      }
      assert.equal(guideAppearances, 18);
      const geometry = await localPage.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth }));
      assert.ok(geometry.document <= geometry.width + 1, JSON.stringify(geometry));
      journeys.push({ javaScriptEnabled, width, guideAppearances, scriptControls: javaScriptEnabled ? 'passed' : 'not applicable' });
    } finally { await localContext.close(); closedContexts++; }
  }
  // Preserve deliberate palette journeys below Chromium's download burst
  // threshold. Use every included choice in this mode. CSS opens as local
  // text in Chrome, while these archive types produce actual downloads.
  for (const name of testedWidth === 390 ? ['Clair', 'Obscur', 'Clair and Obscur'] : []) {
    const { localContext, localPage } = await filePage({ javaScriptEnabled, viewport: { width: 390, height: 844 } });
    try {
      for (const item of packages.downloads.filter(item => item.name === name)) {
        const link = localPage.locator(`#${item.platform}-downloads a[download][href="downloads/${item.path}"]`);
        assert.match(await link.textContent(), /^Open included /);
        const included = await readFile(path.join(relocated, 'downloads', ...item.path.split('/')));
        const expected = records.get(item.path);
        assert.equal(included.length, expected.bytes);
        assert.equal(crypto.createHash('sha256').update(included).digest('hex'), expected.sha256);
        await link.focus();
        let method, matchingGuide = null;
        try {
          if (item.path.endsWith('.css')) {
            const localUrl = pathToFileURL(path.join(relocated, 'downloads', ...item.path.split('/'))).href;
            await Promise.all([localPage.waitForURL(localUrl, { timeout: 5000 }), localPage.keyboard.press('Enter')]);
            assert.equal(await localPage.locator('pre').textContent(), included.toString('utf8'));
            await localPage.goBack();
            assert.equal(await localPage.locator('#portable-delivery').count(), 1);
            matchingGuide = `guide-${item.platform}-${item.name.toLowerCase()}`;
            await localPage.locator(`#${item.platform}-${item.name.toLowerCase()} a.guide-link[href="#${matchingGuide}"]`).focus();
            await localPage.keyboard.press('Enter');
            await waitForGuideDestination(localPage, matchingGuide);
            assert.ok(await localPage.locator('#' + matchingGuide).isVisible());
            await localPage.goBack();
            await localPage.waitForURL(pathToFileURL(path.join(relocated, 'index.html')).href, { timeout: 2000, waitUntil: 'commit' });
            method = 'opened included CSS as exact text, returned and reached matching guide';
          } else {
            const [download] = await Promise.all([localPage.waitForEvent('download', { timeout: 5000 }), localPage.keyboard.press('Enter')]);
            assert.equal(await download.failure(), null);
            assert.equal(download.suggestedFilename(), path.basename(item.path));
            const chunks = [];
            for await (const chunk of await download.createReadStream()) chunks.push(chunk);
            assert.equal(crypto.createHash('sha256').update(Buffer.concat(chunks)).digest('hex'), expected.sha256);
            method = 'saved included archive';
          }
        }
        catch (error) {
          failures.push({ scenario: 'portable included package', javaScriptEnabled, platform: item.platform,
            path: item.path, pageUrl: localPage.url(), requests, errors, error: error.message });
          throw new Error(`Portable ${item.platform} ${item.name} journey failed (${item.path}): ${error.message}`, { cause: error });
        }
        assert.equal(localPage.url(), pathToFileURL(path.join(relocated, 'index.html')).href);
        packageJourneys.push({ javaScriptEnabled, platform: item.platform, path: item.path, sha256: expected.sha256, method, matchingGuide });
      }
    } finally { await localContext.close(); closedContexts++; }
  }
  assert.equal(packageJourneys.length, testedWidth === 390 ? 17 : 0);
  assert.equal(iconJourneys.length, 1);
  assert.equal(packageJourneys.filter(item => item.method === 'saved included archive').length, testedWidth === 390 ? 11 : 0);
  assert.equal(packageJourneys.filter(item => item.method === 'opened included CSS as exact text, returned and reached matching guide').length, testedWidth === 390 ? 6 : 0);
  if (javaScriptEnabled && testedWidth === 390) {
    const chosen = await filePage({ javaScriptEnabled: true, viewport: { width: 390, height: 844 } });
    try {
      for (const [target, appearance] of [['chrome', 'Obscur'], ['equicord', 'Clair']]) {
        await chosen.localPage.locator('#package-target').selectOption(target);
        await chosen.localPage.locator('#package-appearance').selectOption(appearance);
        const item = packages.downloads.find(item => item.platform === target && item.name === appearance);
        const included = await readFile(path.join(relocated, 'downloads', ...item.path.split('/')));
        await chosen.localPage.locator('#package-choice-file').focus();
        if (item.path.endsWith('.css')) {
          const fileUrl = pathToFileURL(path.join(relocated, 'downloads', ...item.path.split('/'))).href;
          await Promise.all([chosen.localPage.waitForURL(fileUrl, { timeout: 5000 }), chosen.localPage.keyboard.press('Enter')]);
          assert.equal(await chosen.localPage.locator('pre').textContent(), included.toString('utf8'));
          await chosen.localPage.goBack();
          await chosen.localPage.locator('#package-target').selectOption(target);
          await chosen.localPage.locator('#package-appearance').selectOption(appearance);
        } else {
          const [download] = await Promise.all([chosen.localPage.waitForEvent('download', { timeout: 5000 }), chosen.localPage.keyboard.press('Enter')]);
          assert.equal(await download.failure(), null);
          const chunks = [];
          for await (const chunk of await download.createReadStream()) chunks.push(chunk);
          assert.deepEqual(Buffer.concat(chunks), included);
        }
        const anchor = `guide-${target}-${appearance.toLowerCase()}`;
        await chosen.localPage.locator('#package-choice-guide').focus();
        await chosen.localPage.keyboard.press('Enter');
        await waitForGuideDestination(chosen.localPage, anchor);
        chooserJourneys.push({ target, appearance, path: item.path, method: item.path.endsWith('.css') ? 'opened included CSS and returned to matching guide' : 'saved included archive and reached matching guide' });
      }
    } finally { await chosen.localContext.close(); closedContexts++; }
  }
  assert.equal(journeys.length, 1);
  assert.equal(terminalJourneys.length, 1);
  assert.equal(chooserJourneys.length, javaScriptEnabled ? (testedWidth === 390 ? 3 : 1) : 0);
  assert.equal(identificationJourneys.length, javaScriptEnabled ? 2 : 0);
  assert.ok(requests.every(url => new URL(url).protocol === 'file:'), 'The extracted consumer must not request network resources');
  assert.deepEqual(errors, []);
  if (modeEvidence) {
    await writeFile(path.join(modeEvidence, 'portable-site-manifest.json'), JSON.stringify(inner, null, 2) + '\n');
  }
  results.scenarios.push({ name: `actual downloaded and relocated offline portable kit (${mode})`, status: 'passed', javaScriptEnabled,
    archive: archiveName, sha256: digest, bytes: archiveBytes.length, downloadNames, source: inner.source,
    protocol: 'file:', network: 'all external requests blocked', requests, errors, journeys, packageJourneys, chooserJourneys, identificationJourneys, iconJourneys, terminalJourneys,
    closedContexts, nativeAppsVerified: false });
});

test('new desktop browser choices remain distinct and readable on a phone', async () => {
  const { context, page, consoleErrors } = await pageFor({ viewport: { width: 390, height: 844 }, hasTouch: true });
  try {
    for (const [platform, label, count] of [['brave', 'Brave', 2], ['vivaldi', 'Vivaldi', 2], ['opera-gx', 'Opera GX', 1]]) {
      await page.getByRole('link', { name: label, exact: true }).click();
      assert.equal(new URL(page.url()).hash, `#${platform}-downloads`);
      const group = page.locator(`#${platform}-downloads`);
      assert.ok(await group.isVisible());
      assert.equal(await group.locator('.download-card').count(), count);
      assert.equal(await group.locator('a[download]').count(), count);
      assert.match(await group.textContent(), /unverified|No Brave installation/);
    }
    assert.match(await page.locator('#opera-gx-downloads').textContent(), /One package pairs Clair Light with Obscur Dark/);
    assert.match(await page.locator('#vivaldi-downloads').textContent(), /5\.0 or later/);
    const geometry = await page.evaluate(() => ({ width: innerWidth, document: document.documentElement.scrollWidth }));
    assert.ok(geometry.document <= geometry.width + 1, JSON.stringify(geometry));
    const manifest = await (await context.request.get(origin + '/downloads/artifact-manifest.json')).json();
    for (const name of ['Clair', 'Obscur']) {
      const chrome = manifest.downloads.find(item => item.name === name && item.platform === 'chrome');
      const brave = manifest.downloads.find(item => item.name === name && item.platform === 'brave');
      assert.equal(brave.path, chrome.path);
      assert.equal(brave.native_acceptance, 'unverified');
    }
    assert.deepEqual(consoleErrors, []);
    assert.deepEqual(failures, []);
    results.scenarios.push({ name: 'phone navigation to Brave, Vivaldi and paired Opera GX desktop candidates', status: 'passed', nativeAppsVerified: false });
  } finally { await context.close(); }
});

test('Equicord CSS consumes host variables only on its matching native base', async () => {
  const { context, page } = await pageFor();
  try {
    const palettes = JSON.parse(await readFile(path.join(root, 'tokens.json'), 'utf8')).themes;
    const color = hex => `rgb(${[1, 3, 5].map(offset => parseInt(hex.slice(offset, offset + 2), 16)).join(', ')})`;
    for (const [name, mode, background, text, filename, nativeFocusRepair] of [
      ['Obscur', 'dark', 'rgb(9, 9, 9)', 'rgb(244, 244, 244)', 'Obscur.theme.css', false],
      ['Clair', 'light', 'rgb(248, 247, 243)', 'rgb(36, 36, 36)', 'Clair.theme.css', false],
      ['Clair', 'light', 'rgb(248, 247, 243)', 'rgb(36, 36, 36)', 'Clair-Equicord-0.1.2.theme.css', true],
    ]) {
      const response = await context.request.get(`${origin}/downloads/equicord/${filename}`);
      assert.equal(response.status(), 200, filename);
      const css = await response.text();
      // Deliberate host-contract fixture. It is not Discord markup or app acceptance.
      await page.setContent(`<html class="theme-${mode}"><head><style>
        body { background:var(--background-primary,#abcdef); color:var(--text-normal,#123456); font-family:var(--font-primary,Arial); }
        button { font-family:var(--font-primary,Arial); background:var(--control-primary-background-default); color:var(--control-primary-text-default); }
        .switch { background:var(--switch-background-default); border:1px solid var(--switch-border-default); }
        .switch.checked { background:var(--switch-background-selected-default); }
        #primary:hover { background:var(--control-primary-background-hover); color:var(--control-primary-text-hover); }
        #secondary { background:var(--control-secondary-background-default); color:var(--control-secondary-text-default); }
        #secondary:hover { background:var(--control-secondary-background-hover); color:var(--control-secondary-text-hover); }
        #mention { display:block; background:var(--mention-background); color:var(--mention-foreground); }
        #mention:hover { background:var(--background-mentioned-hover); }
        .native-control { position:relative; width:44px; height:24px; margin:16px; }
        #native-slider { width:100%; height:100%; background:#eee; }
        .focus-rings-ring {
          display:none; position:absolute; inset:0; box-sizing:border-box;
          box-shadow:0 0 0 4px var(--__adaptive-focus-ring-color,var(--focus-primary,#00b0f4));
          border-radius:var(--__adaptive-focus-ring-radius,4px); pointer-events:none;
        }
        .native-control:focus-within .focus-rings-ring { display:block; }
        .enable-forced-colors .focus-rings-ring {
          forced-color-adjust:none; --__adaptive-focus-ring-color:CanvasText!important;
          border:2px solid Canvas;
        }
        #system-colors { color:CanvasText; background:Canvas; }
      </style></head><body><p id="message-content-fixture">Regular <strong>bold</strong> <em>italic</em> <code>code</code></p>
      <button id="primary" class="vc-btn-base vc-btn-medium">Host control</button><button id="secondary">Secondary control</button>
      <a id="mention" href="#fixture">Mention</a>
      <span class="switch">Off</span><span class="switch checked">On<span class="vc-switch-indicator">Indicator</span></span>
      <div class="native-control"><div id="native-slider" role="slider" tabindex="0" aria-valuemin="12" aria-valuemax="24" aria-valuenow="16" aria-label="Fixture text size"></div>
        <div id="native-ring" class="focus-rings-ring" style="--__adaptive-focus-ring-color:rgba(255,255,255,0.7);--__adaptive-focus-ring-radius:9px"></div></div>
      <span id="system-colors">System color reference</span></body></html>`);
      // Color, radius, pointer and forced-color rules model the inspected host.
      // Position and size are deliberate fixture geometry, not native evidence.
      const nativeRing = () => page.locator('#native-ring').evaluate(node => {
        const style = getComputedStyle(node), box = node.getBoundingClientRect();
        const parentBox = node.parentElement.getBoundingClientRect();
        return {
          shadow:style.boxShadow, adaptiveColor:style.getPropertyValue('--__adaptive-focus-ring-color').trim(),
          display:style.display, forcedColorAdjust:style.forcedColorAdjust,
          border:{ width:style.borderTopWidth, style:style.borderTopStyle, color:style.borderTopColor },
          geometry:{ width:box.width, height:box.height, x:box.x - parentBox.x, y:box.y - parentBox.y,
            position:style.position, radius:style.borderRadius, pointerEvents:style.pointerEvents },
        };
      });
      await page.locator('#native-slider').focus();
      const originalNativeRing = await nativeRing();
      assert.equal(originalNativeRing.shadow, 'rgba(255, 255, 255, 0.7) 0px 0px 0px 4px');
      await page.addStyleTag({ content: css });
      await page.evaluate(() => document.fonts.ready);
      await page.mouse.move(1270, 890);
      const rendered = await page.evaluate(() => ({
        background: getComputedStyle(document.body).backgroundColor,
        text: getComputedStyle(document.body).color,
        controlWeight: getComputedStyle(document.querySelector('button')).fontWeight,
        codeFont: getComputedStyle(document.querySelector('code')).fontFamily,
        off: getComputedStyle(document.querySelector('.switch')).backgroundColor,
        on: getComputedStyle(document.querySelector('.checked')).backgroundColor,
      }));
      assert.equal(rendered.background, background); assert.equal(rendered.text, text);
      assert.equal(rendered.controlWeight, '600'); assert.match(rendered.codeFont, /monospace|Consolas/);
      assert.notEqual(rendered.off, rendered.on);
      const colors = async selector => page.locator(selector).evaluate(node => ({
        background: getComputedStyle(node).backgroundColor, text: getComputedStyle(node).color,
      }));
      const expected = palettes[name];
      assert.deepEqual(await colors('#primary'), { background: color(expected.accent), text: color(expected.on_accent) });
      assert.deepEqual(await colors('#secondary'), { background: color(expected.control), text: color(expected.text) });
      assert.deepEqual(await colors('#mention'), { background: color(expected.selected), text: color(expected.accent) });
      await page.locator('#primary').hover();
      assert.deepEqual(await colors('#primary'), { background: color(expected.accent), text: color(expected.on_accent) });
      await page.locator('#secondary').hover();
      assert.deepEqual(await colors('#secondary'), { background: color(expected.hover), text: color(expected.text) });
      await page.locator('#mention').hover();
      assert.deepEqual(await colors('#mention'), { background: color(expected.hover), text: color(expected.accent) });
      await page.locator('#primary').focus();
      await page.keyboard.press('Tab');
      assert.equal(await page.locator('#secondary').evaluate(node => node.matches(':focus-visible')), true);
      const focus = await page.locator('#secondary').evaluate(node => ({
        width: getComputedStyle(node).outlineWidth, style: getComputedStyle(node).outlineStyle,
        offset: getComputedStyle(node).outlineOffset, color: getComputedStyle(node).outlineColor,
      }));
      assert.deepEqual(focus, { width: '2px', style: 'solid', offset: '2px', color: color(expected.focus) });
      await page.locator('.checked').evaluate(node => node.classList.add('vc-switch-focusVisible'));
      assert.equal(await page.locator('.vc-switch-indicator').evaluate(node => getComputedStyle(node).outlineColor), color(expected.focus));
      assert.equal(await page.locator('.vc-switch-indicator').evaluate(node => getComputedStyle(node).outlineWidth), '2px');
      await page.locator('#native-slider').focus();
      const nativeFocus = await nativeRing();
      assert.equal(nativeFocus.display, 'block');
      assert.equal(await page.locator(':focus').getAttribute('id'), 'native-slider');
      assert.equal(nativeFocus.shadow, nativeFocusRepair ? `${color(expected.focus)} 0px 0px 0px 4px` : originalNativeRing.shadow);
      assert.deepEqual(nativeFocus.geometry, originalNativeRing.geometry);
      assert.equal(nativeFocus.geometry.radius, '9px');
      assert.equal(nativeFocus.geometry.pointerEvents, 'none');
      const hitTarget = await page.locator('#native-slider').evaluate(node => {
        const box = node.getBoundingClientRect();
        return document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2)?.id;
      });
      assert.equal(hitTarget, 'native-slider', 'The overlay must not capture the control hit target');
      await page.emulateMedia({ forcedColors:'active' });
      await page.evaluate(() => document.documentElement.classList.add('enable-forced-colors'));
      const forcedNativeFocus = await nativeRing();
      const systemColors = await page.locator('#system-colors').evaluate(node => ({
        text:getComputedStyle(node).color, canvas:getComputedStyle(node).backgroundColor,
      }));
      assert.equal(forcedNativeFocus.adaptiveColor, 'CanvasText', 'The host important system-color rule must win');
      assert.equal(forcedNativeFocus.forcedColorAdjust, 'none');
      assert.equal(forcedNativeFocus.shadow, `${systemColors.text} 0px 0px 0px 4px`);
      assert.deepEqual(forcedNativeFocus.border, { width:'2px', style:'solid', color:systemColors.canvas });
      assert.deepEqual(forcedNativeFocus.geometry, originalNativeRing.geometry);
      await page.emulateMedia({ forcedColors:'none' });
      await page.evaluate(value => document.documentElement.className = `theme-${value}`, mode === 'dark' ? 'light' : 'dark');
      assert.equal(await page.evaluate(() => getComputedStyle(document.body).backgroundColor), 'rgb(171, 205, 239)');
      assert.deepEqual(await nativeRing(), originalNativeRing, 'The opposite appearance must retain its native ring baseline');
      results.scenarios.push({ name: `${filename} Equicord host-contract fixture`, status: 'passed', rendered, focus,
        nativeFocus:{ original:originalNativeRing, candidate:nativeFocus, forced:forcedNativeFocus, nativeFocusRepair, hitTarget },
        pairedStates: 'primary, secondary and mention default/hover; separate keyboard and switch-class focus',
        oppositeBase: 'retains fixture native baseline', nativeAppVerified: false });
    }
  } finally { await context.close(); }
});

test('client adapters preserve switch geometry and pair their real selector contracts', async () => {
  const { context, page } = await pageFor({ reducedMotion: 'reduce' });
  try {
    const palettes = JSON.parse(await readFile(path.join(root, 'tokens.json'), 'utf8')).themes;
    const color = hex => `rgb(${[1, 3, 5].map(offset => parseInt(hex.slice(offset, offset + 2), 16)).join(', ')})`;
    for (const [client, label] of [['vencord', 'Vencord'], ['betterdiscord', 'BetterDiscord']]) {
      for (const [name, mode] of [['Clair', 'light'], ['Obscur', 'dark']]) {
        const css = await (await context.request.get(`${origin}/downloads/${client}/${name}-${label}.theme.css`)).text();
        // Original synthetic model of the inspected client selectors. It does
        // not contain Discord content or establish a loaded client result.
        const vc = client === 'vencord';
        const markup = vc ? `
          <button id="brand" class="vc-btn-base vc-btn-primary">Brand</button>
          <div id="off" class="vc-switch-container"><svg class="vc-switch-slider" style="transform:translateX(-2px)"><rect fill="white"/><path/></svg></div>
          <div id="on" class="vc-switch-container vc-switch-checked"><svg class="vc-switch-slider" style="transform:translateX(18px)"><rect fill="white"/><path/></svg></div>
          <div id="disabled" class="vc-switch-container vc-switch-disabled">Disabled</div>` : `
          <button id="brand" class="bd-button bd-button-filled bd-button-color-brand">Brand</button>
          <label class="bd-switch"><input id="off-input" type="checkbox"><span id="off" class="bd-switch-body"><svg><rect class="bd-switch-handle" fill="white"/><path/></svg></span></label>
          <label class="bd-switch"><input id="on-input" type="checkbox" checked><span id="on" class="bd-switch-body"><svg style="transform:translateX(18px)"><rect class="bd-switch-handle" fill="white"/><path/></svg></span></label>
          <label id="disabled" class="bd-switch bd-switch-disabled"><input type="checkbox" disabled><span class="bd-switch-body">Disabled</span></label>`;
        await page.setContent(`<html class="theme-${mode}"><head><style>
          body { background:var(--background-primary,#abcdef); color:var(--text-normal,#123456); }
          #brand { width:80px; height:28px; }
          .vc-btn-primary { background:var(--control-primary-background-default,#445566); color:var(--control-primary-text-default,white); }
          .vc-switch-container { width:44px; height:28px; border:1px solid transparent; background:#72767d; transition:background-color 120ms; }
          .vc-switch-checked { background:#445566; }
          .vc-switch-disabled { opacity:.3; }
          .vc-switch-slider { width:28px; height:28px; transition:transform 120ms; }
          .vc-switch-slider path { fill:#72767d; }
          .bd-button-color-brand { background:var(--bd-brand,#445566); color:white; transition:background-color 120ms; }
          .bd-switch { display:block; position:relative; width:40px; height:24px; }
          .bd-switch input { opacity:0; position:absolute; width:100%; height:100%; margin:0; }
          .bd-switch-body { --switch-color:#72767d; display:block; width:40px; height:24px; background:var(--switch-color); transition:background-color 120ms; }
          .bd-switch input:checked + .bd-switch-body { --switch-color:var(--bd-brand,#445566); }
          .bd-switch-body svg { width:24px; height:24px; }
          .bd-switch-body path { fill:var(--switch-color); }
          .bd-switch-disabled { opacity:.5; filter:grayscale(100%); }
          #critical { background:#be1f1f; color:white; }
        </style></head><body>${markup}<button id="critical" class="bd-button bd-button-filled bd-button-color-red">Critical</button></body></html>`);
        const geometry = () => page.evaluate(() => Object.fromEntries(['brand', 'off', 'on', 'disabled'].map(id => {
          const node = document.getElementById(id), style = getComputedStyle(node), svg = node.querySelector('svg');
          return [id, { width:style.width, height:style.height, position:style.position,
            display:style.display, opacity:style.opacity, filter:style.filter,
            transform:svg && getComputedStyle(svg).transform }];
        })));
        const beforeGeometry = await geometry();
        const beforeCritical = await page.locator('#critical').evaluate(node => ({ background:getComputedStyle(node).backgroundColor, text:getComputedStyle(node).color }));
        await page.addStyleTag({ content: css });
        await page.mouse.move(1270, 890);
        const expected = palettes[name];
        const state = await page.evaluate(vcModel => {
          const pair = id => ({ background:getComputedStyle(document.getElementById(id)).backgroundColor, text:getComputedStyle(document.getElementById(id)).color });
          return { brand:pair('brand'), critical:pair('critical'), off:pair('off').background,
            on:pair('on').background,
            offHandle:getComputedStyle(document.querySelector(vcModel ? '#off rect' : '#off .bd-switch-handle')).fill,
            onHandle:getComputedStyle(document.querySelector(vcModel ? '#on rect' : '#on .bd-switch-handle')).fill,
            offMark:getComputedStyle(document.querySelector('#off path')).fill,
            onMark:getComputedStyle(document.querySelector('#on path')).fill,
            reducedTransition:getComputedStyle(document.getElementById('on')).transitionDuration };
        }, vc);
        assert.deepEqual(await geometry(), beforeGeometry);
        assert.deepEqual(state.critical, beforeCritical);
        assert.deepEqual(state.brand, { background:color(expected.accent), text:color(expected.on_accent) });
        assert.equal(state.off, color(expected.control)); assert.equal(state.on, color(expected.accent));
        assert.equal(state.offHandle, color(expected.text)); assert.equal(state.onHandle, color(expected.on_accent));
        assert.equal(state.offMark, color(expected.control)); assert.equal(state.onMark, color(expected.accent));
        assert.equal(state.reducedTransition, '0s');
        await page.locator('#brand').hover();
        assert.deepEqual(await page.locator('#brand').evaluate(node => ({ background:getComputedStyle(node).backgroundColor, text:getComputedStyle(node).color })), state.brand);
        if (vc) await page.locator('#on').evaluate(node => node.classList.add('vc-switch-focusVisible'));
        else { await page.locator('#brand').focus(); await page.keyboard.press('Tab'); await page.keyboard.press('Tab'); }
        const focus = await page.locator('#on').evaluate(node => ({ width:getComputedStyle(node).outlineWidth, color:getComputedStyle(node).outlineColor }));
        assert.deepEqual(focus, { width:'2px', color:color(expected.focus) });
        await page.evaluate(value => document.documentElement.className = `theme-${value}`, mode === 'dark' ? 'light' : 'dark');
        assert.equal(await page.evaluate(() => getComputedStyle(document.body).backgroundColor), 'rgb(171, 205, 239)');
        results.scenarios.push({ name:`${name} ${label} component-contract fixture`, status:'passed', state, focus,
          geometry:'unchanged width, height, display, position, transform and disabled behavior', nativeAppVerified:false });
      }
    }
  } finally { await context.close(); }
});
