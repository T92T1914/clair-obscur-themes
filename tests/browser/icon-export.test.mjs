import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { inflateSync } from 'node:zlib';
import { mkdtemp, readFile, writeFile, mkdir, cp, rm, readdir, symlink, lstat, readlink } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../../', import.meta.url));
const exporter = path.join(root, 'tools', 'export-icons.mjs');
const python = process.platform === 'win32' ? ['py', '-3.11', '-X', 'utf8'] : ['python3'];
const baseFunctions = ('phone messages contacts camera gallery settings calendar clock files notes mail browser maps ' +
  'music video store wallet calculator weather health fitness voice-recorder home search').split(' ');
// Independent assignment identities, rather than an inventory imported from the generator.
const firstApps = [
  ['google-chrome', 'Google Chrome', 'com.android.chrome'],
  ['youtube', 'YouTube', 'com.google.android.youtube'],
  ['google-maps', 'Google Maps', 'com.google.android.apps.maps'],
  ['gmail', 'Gmail', 'com.google.android.gm'],
  ['google-photos', 'Google Photos', 'com.google.android.apps.photos'],
  ['google-messages', 'Google Messages', 'com.google.android.apps.messaging'],
  ['google-calendar', 'Google Calendar', 'com.google.android.calendar'],
  ['google-drive', 'Google Drive', 'com.google.android.apps.docs'],
  ['samsung-browser', 'Samsung Browser', 'com.sec.android.app.sbrowser'],
  ['samsung-notes', 'Samsung Notes', 'com.samsung.android.app.notes'],
  ['samsung-health', 'Samsung Health', 'com.sec.android.app.shealth'],
  ['garmin-connect', 'Garmin Connect', 'com.garmin.android.apps.connectmobile'],
  ['whatsapp', 'WhatsApp', 'com.whatsapp'],
  ['messenger', 'Messenger', 'com.facebook.orca'],
  ['instagram', 'Instagram', 'com.instagram.android'],
  ['facebook', 'Facebook', 'com.facebook.katana'],
  ['snapchat', 'Snapchat', 'com.snapchat.android'],
  ['tiktok', 'TikTok', 'com.zhiliaoapp.musically'],
  ['discord', 'Discord', 'com.discord'],
  ['reddit', 'Reddit', 'com.reddit.frontpage'],
  ['pinterest', 'Pinterest', 'com.pinterest'],
  ['telegram', 'Telegram', 'org.telegram.messenger'],
  ['spotify', 'Spotify', 'com.spotify.music'],
  ['netflix', 'Netflix', 'com.netflix.mediaclient'],
  ['amazon-shopping', 'Amazon Shopping', 'com.amazon.mShop.android.shopping'],
  ['walmart', 'Walmart', 'com.walmart.android'],
  ['temu', 'Temu', 'com.einnovation.temu'],
  ['uber', 'Uber', 'com.ubercab'],
  ['doordash', 'DoorDash', 'com.dd.doordash'],
  ['paypal', 'PayPal', 'com.paypal.android.p2pmobile'],
  ['outlook', 'Microsoft Outlook', 'com.microsoft.office.outlook'],
  ['chatgpt', 'ChatGPT', 'com.openai.chatgpt'],
  ['firefox', 'Firefox', 'org.mozilla.firefox'],
];
const addedApps = [
  ['x', 'X', 'com.twitter.android'],
  ['threads', 'Threads', 'com.instagram.barcelona'],
  ['signal', 'Signal', 'org.thoughtcrime.securesms'],
  ['twitch', 'Twitch', 'tv.twitch.android.app'],
  ['capcut', 'CapCut', 'com.lemon.lvoverseas'],
  ['disney-plus', 'Disney+', 'com.disney.disneyplus'],
  ['prime-video', 'Prime Video', 'com.amazon.avod.thirdpartyclient'],
  ['microsoft-teams', 'Teams', 'com.microsoft.teams'],
  ['zoom', 'Zoom', 'us.zoom.videomeetings'],
  ['google-meet', 'Google Meet', 'com.google.android.apps.tachyon'],
  ['google-docs', 'Google Docs', 'com.google.android.apps.docs.editors.docs'],
  ['google-sheets', 'Google Sheets', 'com.google.android.apps.docs.editors.sheets'],
  ['onedrive', 'OneDrive', 'com.microsoft.skydrive'],
  ['google-translate', 'Google Translate', 'com.google.android.apps.translate'],
  ['google-keep', 'Google Keep', 'com.google.android.keep'],
  ['google-wallet', 'Google Wallet', 'com.google.android.apps.walletnfcrel'],
  ['cash-app', 'Cash App', 'com.squareup.cash'],
  ['venmo', 'Venmo', 'com.venmo'],
  ['ebay', 'eBay', 'com.ebay.mobile'],
  ['mcdonalds', "McDonald's", 'com.mcdonalds.app'],
  ['starbucks', 'Starbucks', 'com.starbucks.mobilecard'],
  ['duolingo', 'Duolingo', 'com.duolingo'],
  ['waze', 'Waze', 'com.waze'],
  ['canva', 'Canva', 'com.canva.editor'],
];
const thirdApps = [
  ['linkedin', 'LinkedIn', 'com.linkedin.android'],
  ['github', 'GitHub', 'com.github.android'],
  ['notion', 'Notion', 'notion.id'],
  ['microsoft-edge', 'Microsoft Edge', 'com.microsoft.emmx'],
  ['brave', 'Brave', 'com.brave.browser'],
  ['microsoft-authenticator', 'Microsoft Authenticator', 'com.azure.authenticator'],
  ['google-authenticator', 'Google Authenticator', 'com.google.android.apps.authenticator2'],
  ['samsung-smartthings', 'SmartThings', 'com.samsung.android.oneconnect'],
];
const secondApps = [...firstApps, ...addedApps];
const retainedApps = [...secondApps, ...thirdApps];
const fourthApps = [
  ['good-lock', 'Good Lock', 'com.samsung.android.goodlock'],
  ['connect-iq-store', 'Connect IQ Store', 'com.garmin.connectiq'],
  ['steam', 'Steam', 'com.valvesoftware.android.steam.community'],
  ['reuters', 'Reuters', 'com.thomsonreuters.reuters'],
  ['home-depot', 'Home Depot', 'com.thehomedepot'],
  ['patreon', 'Patreon', 'com.patreon.android'],
];
const companionApps = [...retainedApps, ...fourthApps];
const fifthApps = [
  ["youtube-music", "YouTube Music", "com.google.android.apps.youtube.music"],
  ["audible", "Audible", "com.audible.application"],
  ["amazon-kindle", "Amazon Kindle", "com.amazon.kindle"],
  ["pocket-casts", "Pocket Casts", "au.com.shiftyjelly.pocketcasts"],
  ["vlc", "VLC", "org.videolan.vlc"],
  ["shazam", "Shazam", "com.shazam.android"],
  ["soundcloud", "SoundCloud", "com.soundcloud.android"],
  ["hulu", "Hulu", "com.hulu.plus"],
  ["target", "Target", "com.target.ui"],
  ["costco", "Costco", "com.costco.app.android"],
  ["best-buy", "Best Buy", "com.bestbuy.android"],
  ["etsy", "Etsy", "com.etsy.android"],
  ["aliexpress", "AliExpress", "com.alibaba.aliexpresshd"],
  ["shein", "SHEIN", "com.zzkko"],
  ["instacart", "Instacart", "com.instacart.client"],
  ["airbnb", "Airbnb", "com.airbnb.android"],
  ["booking", "Booking.com", "com.booking"],
  ["expedia", "Expedia", "com.expedia.bookings"],
  ["lyft", "Lyft", "me.lyft.android"],
  ["uber-eats", "Uber Eats", "com.ubercab.eats"],
  ["google-earth", "Google Earth", "com.google.earth"],
  ["google-news", "Google News", "com.google.android.apps.magazines"],
  ["galaxy-wearable", "Galaxy Wearable", "com.samsung.android.app.watchmanager"],
  ["files-by-google", "Files by Google", "com.google.android.apps.nbu.files"],
  ["adobe-acrobat", "Adobe Acrobat", "com.adobe.reader"],
  ["microsoft-word", "Microsoft Word", "com.microsoft.office.word"],
  ["microsoft-excel", "Microsoft Excel", "com.microsoft.office.excel"],
  ["microsoft-powerpoint", "PowerPoint", "com.microsoft.office.powerpoint"],
  ["google-slides", "Google Slides", "com.google.android.apps.docs.editors.slides"],
  ["google-lens", "Google Lens", "com.google.ar.lens"],
  ["roblox", "Roblox", "com.roblox.client"],
  ["minecraft", "Minecraft", "com.mojang.minecraftpe"],
];
const broadApps = [...companionApps, ...fifthApps];
const sixthApps = [
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
const everydayApps = [...broadApps, ...sixthApps];
const foodOrderApps = [
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
const foodApps = [...everydayApps, ...foodOrderApps];
const travelApps = [
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
const financeApps = [
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
const travelCatalogApps = [...foodApps, ...travelApps];
const financeCatalogApps = [...travelCatalogApps, ...financeApps];
const weatherApps = [
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
const weatherCatalogApps = [...financeCatalogApps, ...weatherApps];
const runningTrainingApps = [
  ['nike-run-club', 'Nike Run Club', 'com.nike.plusgps'],
  ['adidas-running', 'adidas Running', 'com.runtastic.android'],
  ['asics-runkeeper', 'ASICS Runkeeper', 'com.fitnesskeeper.runkeeper.pro'],
  ['map-my-run', 'Map My Run', 'com.mapmyrun.android2'],
  ['runna', 'Runna', 'com.runbuddy.prod'],
  ['trainingpeaks', 'TrainingPeaks', 'com.peaksware.trainingpeaks'],
  ['zwift-companion', 'Zwift Companion', 'com.zwift.android.prod'],
  ['relive', 'Relive', 'cc.relive.reliveapp'],
];
const runningCatalogApps = [...weatherCatalogApps, ...runningTrainingApps];
const learningApps = [
  ['google-classroom', 'Google Classroom', 'com.google.android.apps.classroom'],
  ['khan-academy', 'Khan Academy', 'org.khanacademy.android'],
  ['coursera', 'Coursera', 'org.coursera.android'],
  ['udemy', 'Udemy', 'com.udemy.android'],
  ['edx', 'edX', 'org.edx.mobile'],
  ['quizlet', 'Quizlet', 'com.quizlet.quizletandroid'],
  ['photomath', 'Photomath', 'com.microblink.photomath'],
  ['brainly', 'Brainly', 'co.brainly'],
];
const learningCatalogApps = [...runningCatalogApps, ...learningApps];
const readingApps = [
  ["google-play-books", "Google Play Books", "com.google.android.apps.books"],
  ["libby", "Libby", "com.overdrive.mobile.android.libby"],
  ["kobo-books", "Kobo Books", "com.kobobooks.android"],
  ["goodreads", "Goodreads", "com.goodreads"],
  ["wattpad", "Wattpad", "wp.wattpad"],
  ["webtoon", "WEBTOON", "com.naver.linewebtoon"],
  ["readera", "ReadEra", "org.readera"],
  ["moon-reader", "Moon+ Reader", "com.flyersoft.moonreader"],
];
const readingCatalogApps = [...learningCatalogApps, ...readingApps];
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

const apps = [...readingCatalogApps, ...phoneServiceApps];
const firstFunctions = [...baseFunctions, ...firstApps.map(([id]) => id)];
const secondFunctions = [...baseFunctions, ...secondApps.map(([id]) => id)];
const retainedFunctions = [...baseFunctions, ...retainedApps.map(([id]) => id)];
const companionFunctions = [...baseFunctions, ...companionApps.map(([id]) => id)];
const broadFunctions = [...baseFunctions, ...broadApps.map(([id]) => id)];
const everydayFunctions = [...baseFunctions, ...everydayApps.map(([id]) => id)];
const foodFunctions = [...baseFunctions, ...foodApps.map(([id]) => id)];
const travelFunctions = [...baseFunctions, ...travelCatalogApps.map(([id]) => id)];
const financeFunctions = [...baseFunctions, ...financeCatalogApps.map(([id]) => id)];
const weatherFunctions = [...baseFunctions, ...weatherCatalogApps.map(([id]) => id)];
const runningFunctions = [...baseFunctions, ...runningCatalogApps.map(([id]) => id)];
const learningFunctions = [...baseFunctions, ...learningCatalogApps.map(([id]) => id)];
const readingFunctions = [...baseFunctions, ...readingCatalogApps.map(([id]) => id)];
const galaxyIconIds = new Set(['gaming-hub', 'theme-park', 'samsung-pass', 'tips']);
const functions = [...baseFunctions, ...apps.map(([id]) => id)];
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
let temporary, source, sourceBefore, legacySource, legacyBefore, previousSource, previousBefore,
  firstSource, firstBefore, secondSource, secondBefore, thirdSource, thirdBefore,
  monochromeSource, monochromeBefore, companionSource, companionBefore, broadSource, broadBefore, everydaySource, everydayBefore,
  foodSource, foodBefore, travelSource, travelBefore, financeSource, financeBefore, weatherSource, weatherBefore, runningSource, runningBefore, learningSource, learningBefore, readingSource, readingBefore, phoneServiceSource, phoneServiceBefore;

function execute(command, args, options = {}) {
  return spawnSync(command, args, { cwd: root, encoding: 'utf8', windowsHide: true,
    timeout: 180000, maxBuffer: 4 * 1024 * 1024, ...options });
}

function exportTo(input, output, negative = false) {
  // A bad channel proves admission errors occur before browser selection/launch.
  return execute(process.execPath, [exporter, '--input', input, '--output', output], {
    env: { ...process.env, ...(negative ? { THEME_BROWSER_CHANNEL: 'unavailable-before-admission-test' } : {}) },
  });
}

async function snapshot(directory) {
  const files = {};
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      for (const [name, digest] of Object.entries(await snapshot(path.join(directory, entry.name)))) {
        files[`${entry.name}/${name}`] = digest;
      }
    } else files[entry.name] = sha(await readFile(path.join(directory, entry.name)));
  }
  return files;
}

function assertFailedBeforeBrowser(result, expected) {
  assert.ifError(result.error);
  assert.equal(result.status, 1, result.stdout + result.stderr);
  assert.match(result.stderr, expected);
  assert.doesNotMatch(result.stderr, /browserType\.launch|unavailable-before-admission-test/);
}

function crc32(bytes) {
  let crc = 0xffffffff;
  for (const value of bytes) {
    crc ^= value;
    for (let bit = 0; bit < 8; bit += 1) crc = (crc >>> 1) ^ ((crc & 1) ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

// Decode saved PNG bytes independently of the browser's canvas and admission code.
function decodeRgba(bytes, size) {
  assert.deepEqual([...bytes.subarray(0, 8)], [137, 80, 78, 71, 13, 10, 26, 10]);
  const compressed = [];
  let offset = 8, header = false, end = false;
  while (offset < bytes.length) {
    const length = bytes.readUInt32BE(offset);
    const kind = bytes.toString('ascii', offset + 4, offset + 8);
    assert.ok(offset + 12 + length <= bytes.length, 'PNG chunk is complete');
    assert.equal(crc32(bytes.subarray(offset + 4, offset + 8 + length)), bytes.readUInt32BE(offset + 8 + length));
    const data = bytes.subarray(offset + 8, offset + 8 + length);
    if (kind === 'IHDR') {
      assert.equal(header, false); header = true;
      assert.equal(length, 13); assert.equal(data.readUInt32BE(0), size); assert.equal(data.readUInt32BE(4), size);
      assert.deepEqual([...data.subarray(8)], [8, 6, 0, 0, 0], '8-bit noninterlaced RGBA PNG');
    } else if (kind === 'IDAT') compressed.push(data);
    else if (kind === 'IEND') { assert.equal(length, 0); end = true; }
    offset += length + 12;
    if (end) break;
  }
  assert.ok(header && end && compressed.length > 0);
  assert.equal(offset, bytes.length);
  const stride = size * 4;
  const raw = inflateSync(Buffer.concat(compressed), { maxOutputLength: (stride + 1) * size });
  assert.equal(raw.length, (stride + 1) * size);
  const rgba = Buffer.alloc(stride * size);
  const paeth = (a, b, c) => {
    const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
    return pa <= pb && pa <= pc ? a : (pb <= pc ? b : c);
  };
  for (let y = 0; y < size; y += 1) {
    const filter = raw[y * (stride + 1)];
    assert.ok(filter <= 4);
    for (let index = 0; index < stride; index += 1) {
      const current = y * stride + index;
      const left = index >= 4 ? rgba[current - 4] : 0;
      const above = y > 0 ? rgba[current - stride] : 0;
      const upperLeft = y > 0 && index >= 4 ? rgba[current - stride - 4] : 0;
      const prediction = filter === 0 ? 0 : filter === 1 ? left : filter === 2 ? above :
        filter === 3 ? Math.floor((left + above) / 2) : paeth(left, above, upperLeft);
      rgba[current] = (raw[y * (stride + 1) + index + 1] + prediction) & 255;
    }
  }
  return rgba;
}

function assertMonochromePixels(bytes, size, appearance, record, relative) {
  assert.equal(record.pixel_check.nontransparent_border_pixels, 0);
  assert.equal(record.pixel_check.nonneutral_pixels, 0);
  assert.deepEqual(Object.keys(record.pixel_check.counts).sort(), ['glyph', 'panel', 'transparent']);
  assert.ok(record.pixel_check.counts.glyph > 100, 'One combined glyph color is measured');
  const rgba = decodeRgba(bytes, size);
  const tile = appearance === 'Clair' ? 255 : 0;
  const foreground = appearance === 'Clair' ? 0 : 255;
  const counts = { panel: 0, glyph: 0, transparent: 0 };
  let nonneutral = 0;
  for (let y = 0; y < size; y += 1) for (let x = 0; x < size; x += 1) {
    const index = (y * size + x) * 4, alpha = rgba[index + 3];
    if (alpha === 0) counts.transparent += 1;
    else if (rgba[index] !== rgba[index + 1] || rgba[index + 1] !== rgba[index + 2]) nonneutral += 1;
    if (x < size / 16 || y < size / 16 || x >= size * 15 / 16 || y >= size * 15 / 16) assert.equal(alpha, 0, 'Full outer margin stays transparent');
    if (alpha !== 255) continue;
    if (rgba[index] === tile) counts.panel += 1;
    if (rgba[index] === foreground) counts.glyph += 1;
  }
  assert.ok(counts.transparent > 0 && counts.panel > size * size / 3 && counts.glyph > 100,
    `${relative} preserves its pure tile, pure foreground and transparent margin`);
  assert.equal(nonneutral, 0, 'Every visible RGB triple is neutral; antialias grays are valid');
  assert.deepEqual(record.pixel_check.counts, counts);
}

before(async () => {
  temporary = await mkdtemp(path.join(tmpdir(), 'clair-obscur-icon-export-'));
  source = path.join(temporary, 'svg');
  const result = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', source]);
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  sourceBefore = await snapshot(source);
  phoneServiceSource = path.join(temporary, 'phone-service-svg');
  const phoneService = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', phoneServiceSource, '--version', '0.17.0']);
  assert.ifError(phoneService.error);
  assert.equal(phoneService.status, 0, phoneService.stdout + phoneService.stderr);
  phoneServiceBefore = await snapshot(phoneServiceSource);
  assert.equal(phoneServiceBefore['manifest.json'], 'e1be7375d5697623c539b0b08989be070edf3df5a501a95753d0c78fc44ff503',
    'The accepted phone-service manifest remains exact');
  const changed = Object.keys(phoneServiceBefore).filter(name => name.endsWith('.svg') && sourceBefore[name] !== phoneServiceBefore[name]);
  assert.deepEqual(changed.sort(), ['Clair', 'Obscur'].flatMap(appearance =>
    ['google-messages', 'google-translate', 'fandom', 'ace-hardware', 'dollar-general', 'myfitnesspal', 'wallpaper-engine', 'webtoon']
      .map(name => `${appearance}/${name}.svg`)).sort(), 'Only the eight admitted drawings change in the current revision');
  legacySource = path.join(temporary, 'legacy-svg');
  const legacy = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', legacySource, '--version', '0.1.0']);
  assert.ifError(legacy.error);
  assert.equal(legacy.status, 0, legacy.stdout + legacy.stderr);
  legacyBefore = await snapshot(legacySource);
  previousSource = path.join(temporary, 'previous-svg');
  const previous = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', previousSource, '--version', '0.2.0']);
  assert.ifError(previous.error);
  assert.equal(previous.status, 0, previous.stdout + previous.stderr);
  previousBefore = await snapshot(previousSource);
  firstSource = path.join(temporary, 'first-app-svg');
  const first = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', firstSource, '--version', '0.3.0']);
  assert.ifError(first.error);
  assert.equal(first.status, 0, first.stdout + first.stderr);
  firstBefore = await snapshot(firstSource);
  assert.equal(firstBefore['manifest.json'], 'd52bfef3a1504cfa90117c155458479677f5ecf27a9b98f99df9c3b8c87d15e3',
    'The accepted first-collection manifest remains exact');
  secondSource = path.join(temporary, 'second-app-svg');
  const second = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', secondSource, '--version', '0.4.0']);
  assert.ifError(second.error);
  assert.equal(second.status, 0, second.stdout + second.stderr);
  secondBefore = await snapshot(secondSource);
  assert.equal(secondBefore['manifest.json'], 'e41b32db1e23c63564957f253d81c449f8aa1f85493890cc07908ad1906c7527',
    'The accepted second-collection manifest remains exact');
  thirdSource = path.join(temporary, 'third-app-svg');
  const third = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', thirdSource, '--version', '0.5.0']);
  assert.ifError(third.error);
  assert.equal(third.status, 0, third.stdout + third.stderr);
  thirdBefore = await snapshot(thirdSource);
  assert.equal(thirdBefore['manifest.json'], 'e40a9bd7ae62f677078fb10a48e0ced5901a43bfff06c8684270d560ca4529c8',
    'The accepted third-collection manifest remains exact');
  monochromeSource = path.join(temporary, 'first-monochrome-svg');
  const monochrome = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', monochromeSource, '--version', '0.6.0']);
  assert.ifError(monochrome.error);
  assert.equal(monochrome.status, 0, monochrome.stdout + monochrome.stderr);
  monochromeBefore = await snapshot(monochromeSource);
  assert.equal(monochromeBefore['manifest.json'], '57537e0ad06dee704400160d30ae47f4cce8beba557c347ef5236ac8da32ee92',
    'The accepted first-monochrome manifest remains exact');
  for (const appearance of ['Clair', 'Obscur']) for (const name of retainedFunctions) {
    assert.equal(phoneServiceBefore[`${appearance}/${name}.svg`], monochromeBefore[`${appearance}/${name}.svg`],
      'Every retained monochrome SVG stays byte-identical in the expanded collection');
  }
  companionSource = path.join(temporary, 'companion-svg');
  const companion = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', companionSource, '--version', '0.7.0']);
  assert.ifError(companion.error);
  assert.equal(companion.status, 0, companion.stdout + companion.stderr);
  companionBefore = await snapshot(companionSource);
  assert.equal(companionBefore['manifest.json'], 'a58049892930f817b1376c03510ab408c84d5336d908d885e4ab52e078d238ca',
    'The accepted companion-collection manifest remains exact');
  for (const appearance of ['Clair', 'Obscur']) for (const name of companionFunctions) {
    assert.equal(phoneServiceBefore[`${appearance}/${name}.svg`], companionBefore[`${appearance}/${name}.svg`],
      'All 190 accepted companion SVG bytes remain unchanged in the broader collection');
  }
  broadSource = path.join(temporary, 'broad-svg');
  const broad = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', broadSource, '--version', '0.8.0']);
  assert.ifError(broad.error);
  assert.equal(broad.status, 0, broad.stdout + broad.stderr);
  broadBefore = await snapshot(broadSource);
  assert.equal(broadBefore['manifest.json'], '7a8a35d6ba1186a718e970e26c5c6b7b19bf4949010c7bc89af3cb6063b95252',
    'The accepted broad-collection manifest remains exact');
  for (const appearance of ['Clair', 'Obscur']) for (const name of broadFunctions) {
    assert.equal(phoneServiceBefore[`${appearance}/${name}.svg`], broadBefore[`${appearance}/${name}.svg`],
      'All 254 accepted broad SVG bytes remain unchanged in the everyday collection');
  }
  everydaySource = path.join(temporary, 'everyday-svg');
  const everyday = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', everydaySource, '--version', '0.9.0']);
  assert.ifError(everyday.error);
  assert.equal(everyday.status, 0, everyday.stdout + everyday.stderr);
  everydayBefore = await snapshot(everydaySource);
  assert.equal(everydayBefore['manifest.json'], '7f3e3137cc2b3e72a4861368b6864158de8f5a17e5b2a57a2b0489c5ca0f78b5',
    'The accepted everyday-collection manifest remains exact');
  for (const appearance of ['Clair', 'Obscur']) for (const name of everydayFunctions) {
    assert.equal(phoneServiceBefore[`${appearance}/${name}.svg`], everydayBefore[`${appearance}/${name}.svg`],
      'All 350 accepted everyday SVG bytes remain unchanged in the food-order collection');
  }
  foodSource = path.join(temporary, 'food-order-svg');
  const food = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', foodSource, '--version', '0.10.0']);
  assert.ifError(food.error);
  assert.equal(food.status, 0, food.stdout + food.stderr);
  foodBefore = await snapshot(foodSource);
  assert.equal(foodBefore['manifest.json'], 'b9b1995bee3f538137bd1f5edd4da4ba5358ce3908d19ff9b493c4f19c8ec88d',
    'The accepted food-order manifest remains exact');
  for (const appearance of ['Clair', 'Obscur']) for (const name of foodFunctions) {
    assert.equal(phoneServiceBefore[`${appearance}/${name}.svg`], foodBefore[`${appearance}/${name}.svg`],
      'All 374 accepted food-order SVG bytes remain unchanged in the expanded collection');
  }
  travelSource = path.join(temporary, 'travel-svg');
  const travel = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', travelSource, '--version', '0.11.0']);
  assert.ifError(travel.error);
  assert.equal(travel.status, 0, travel.stdout + travel.stderr);
  travelBefore = await snapshot(travelSource);
  assert.equal(travelBefore['manifest.json'], '1ebc36ff9e29aa9b71a504c393a0028c3338cdd4d341a91dff5f6d6361a2bb57',
    'The accepted travel manifest remains exact');
  for (const appearance of ['Clair', 'Obscur']) for (const name of travelFunctions) {
    assert.equal(phoneServiceBefore[`${appearance}/${name}.svg`], travelBefore[`${appearance}/${name}.svg`],
      'All 394 accepted travel SVG bytes remain unchanged in the finance collection');
  }
  financeSource = path.join(temporary, 'finance-svg');
  const finance = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', financeSource, '--version', '0.12.0']);
  assert.ifError(finance.error);
  assert.equal(finance.status, 0, finance.stdout + finance.stderr);
  financeBefore = await snapshot(financeSource);
  assert.equal(financeBefore['manifest.json'], '7d0f413f04784c2457de5b3667fa8b265d3f3b09efb6be108c135cf6b8d88b3d',
    'The accepted finance manifest remains exact');
  for (const appearance of ['Clair', 'Obscur']) for (const name of financeFunctions) {
    assert.equal(phoneServiceBefore[appearance + '/' + name + '.svg'], financeBefore[appearance + '/' + name + '.svg'],
      'All 414 accepted finance SVG bytes remain unchanged in the running/training collection');
  }
  weatherSource = path.join(temporary, 'weather-svg');
  const weather = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', weatherSource, '--version', '0.13.0']);
  assert.ifError(weather.error);
  assert.equal(weather.status, 0, weather.stdout + weather.stderr);
  weatherBefore = await snapshot(weatherSource);
  assert.equal(weatherBefore['manifest.json'], 'cc573fb8f3996d05eff6d8e724c179f17001ffcfaff26bbfade76e52591ce723',
    'The accepted weather manifest remains exact');
  for (const appearance of ['Clair', 'Obscur']) for (const name of weatherFunctions) {
    assert.equal(phoneServiceBefore[appearance + '/' + name + '.svg'], weatherBefore[appearance + '/' + name + '.svg'],
      'All 434 accepted weather SVG bytes remain unchanged in the running/training collection');
  }
  runningSource = path.join(temporary, 'running-svg');
  const running = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', runningSource, '--version', '0.14.0']);
  assert.ifError(running.error);
  assert.equal(running.status, 0, running.stdout + running.stderr);
  runningBefore = await snapshot(runningSource);
  assert.equal(runningBefore['manifest.json'], '4ac31c55d2723a0e27ee4892eb29d59dbdcb179443f496fced7b69337c0699df',
    'The accepted running and training manifest remains exact');
  for (const appearance of ['Clair', 'Obscur']) for (const name of runningFunctions) {
    assert.equal(phoneServiceBefore[appearance + '/' + name + '.svg'], runningBefore[appearance + '/' + name + '.svg'],
      'All 450 accepted running and training SVG bytes remain unchanged in the learning collection');
  }

  learningSource = path.join(temporary, 'learning-svg');
  const learning = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', learningSource, '--version', '0.15.0']);
  assert.ifError(learning.error);
  assert.equal(learning.status, 0, learning.stdout + learning.stderr);
  learningBefore = await snapshot(learningSource);
  assert.equal(learningBefore['manifest.json'], '3979cc7eaf90a5cf8aab82bd711fc8d2ff92388856cbb41b9321442693b88b2b',
    'The accepted learning and study manifest remains exact');
  for (const appearance of ['Clair', 'Obscur']) for (const name of learningFunctions) {
    assert.equal(phoneServiceBefore[appearance + '/' + name + '.svg'], learningBefore[appearance + '/' + name + '.svg'],
      'All 466 accepted learning and study SVG bytes remain unchanged in the reading collection');
  }

  readingSource = path.join(temporary, 'reading-svg');
  const reading = execute(python[0], [...python.slice(1), '-m', 'themeforge.icons', '--output', readingSource, '--version', '0.16.0']);
  assert.ifError(reading.error);
  assert.equal(reading.status, 0, reading.stdout + reading.stderr);
  readingBefore = await snapshot(readingSource);
  assert.equal(readingBefore['manifest.json'], 'edf610a33c55adeecca9c43bde0b0786a4f7d0b81c018880a504068218670b19',
    'The accepted reading manifest remains exact');
  for (const appearance of ['Clair', 'Obscur']) for (const name of readingFunctions) {
    assert.equal(phoneServiceBefore[appearance + '/' + name + '.svg'], readingBefore[appearance + '/' + name + '.svg'],
      'All 482 accepted reading SVG bytes remain unchanged in the phone-service collection');
  }

});

after(async () => {
  if (temporary) {
    assert.equal(path.dirname(temporary).toLowerCase(), tmpdir().toLowerCase());
    assert.ok(path.basename(temporary).startsWith('clair-obscur-icon-export-'));
    await rm(temporary, { recursive: true });
  }
});

test('PNG command exports 1124 monochrome icons with independent neutral-pixel decoding and assignment identities', async () => {
  const output = path.join(temporary, 'png');
  const result = exportTo(source, output);
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /Exported 1124 PNG icons/);
  const manifestBytes = await readFile(path.join(output, 'manifest.json'));
  const manifest = JSON.parse(manifestBytes);
  const expected = ['manifest.json', 'LICENSE'];
  assert.equal(manifest.version, '0.18.0');
  assert.equal(manifest.exporter_version, '0.11.0');
  assert.equal(manifest.palette_variant, 'monochrome');
  assert.equal(manifest.token_version, '1.0.0');
  assert.equal(manifest.files.length, 1124);
  assert.deepEqual(manifest.functions, functions);
  assert.equal(manifest.source_manifest_sha256, sourceBefore['manifest.json']);
  assert.equal(manifest.tokens_file, 'tokens-monochrome.json');
  assert.equal(manifest.tokens_sha256, sha(await readFile(path.join(root, 'tokens-monochrome.json'))));
  assert.equal(manifest.svg_generator_sha256, sha(await readFile(path.join(root, 'themeforge/icons.py'))));
  assert.equal(manifest.svg_catalog_sha256, sha(await readFile(path.join(root, 'themeforge/icon_apps.py'))));
  const svgManifest = JSON.parse(await readFile(path.join(source, 'manifest.json')));
  assert.deepEqual(manifest.catalog, svgManifest.catalog, 'Complete admitted assignment metadata survives PNG export');
  assert.equal(manifest.catalog.length, 281);
  assert.equal(manifest.catalog_date, '2026-10-21');
  assert.equal(manifest.catalog_scope, svgManifest.catalog_scope);
  assert.match(manifest.catalog_scope, /No popularity ranking, publisher endorsement, security recommendation or installation claim/);
  assert.deepEqual(manifest.catalog.filter(entry => entry.kind === 'function').map(entry => entry.id), baseFunctions);
  assert.deepEqual(manifest.catalog.filter(entry => entry.kind === 'app').map(entry =>
    [entry.id, entry.label, entry.android_package]), apps);
  for (const entry of manifest.catalog.filter(entry => entry.kind === 'app')) {
    assert.equal(entry.store_url, galaxyIconIds.has(entry.id) ?
      `https://galaxystore.samsung.com/detail/${entry.android_package}` :
      `https://play.google.com/store/apps/details?id=${entry.android_package}`);
    for (const field of ['category', 'store_title', 'selection_basis']) assert.ok(entry[field].trim());
  }
  assert.deepEqual(Object.fromEntries(manifest.catalog.filter(entry => fourthApps.some(([id]) => id === entry.id))
    .map(entry => [entry.id, entry.store_title])), {
    'good-lock': 'Good Lock', 'connect-iq-store': 'Connect IQ\u2122 Store', steam: 'Steam',
    reuters: 'Reuters - Breaking World News', 'home-depot': 'The Home Depot', patreon: 'Patreon',
  });
  assert.deepEqual(Object.fromEntries(manifest.catalog.filter(entry => fifthApps.some(([id]) => id === entry.id))
    .map(entry => [entry.id, entry.store_title])), {
    "youtube-music": "YouTube Music",
    "audible": "Audible: Audiobooks & Podcasts",
    "amazon-kindle": "Amazon Kindle: Reading App",
    "pocket-casts": "Pocket Casts - Podcast App",
    "vlc": "VLC for Android",
    "shazam": "Shazam: Find Music & Concerts",
    "soundcloud": "SoundCloud: Discover Music",
    "hulu": "Hulu: Stream TV shows & movies",
    "target": "Target: Shop. Style. Save.",
    "costco": "Costco Wholesale",
    "best-buy": "Best Buy: Shop tech deals",
    "etsy": "Etsy: Shop from Real People",
    "aliexpress": "AliExpress : shopping en ligne",
    "shein": "SHEIN-Shopping Online",
    "instacart": "Instacart: Get Food Delivery",
    "airbnb": "Airbnb",
    "booking": "Booking.com: Hotels & Travel",
    "expedia": "Expedia: Hotels, Flights, Cars",
    "lyft": "Lyft",
    "uber-eats": "Uber Eats: Food and Grocery",
    "google-earth": "Google Earth",
    "google-news": "Google News - Daily Headlines",
    "galaxy-wearable": "Galaxy Wearable",
    "files-by-google": "Files by Google",
    "adobe-acrobat": "Adobe Acrobat Reader: Edit PDF",
    "microsoft-word": "Microsoft Word: Edit Documents",
    "microsoft-excel": "Microsoft Excel: Spreadsheets",
    "microsoft-powerpoint": "Microsoft PowerPoint",
    "google-slides": "Google Slides",
    "google-lens": "Google Lens",
    "roblox": "Roblox",
    "minecraft": "Minecraft: Dream it, Build it!"
});
  assert.deepEqual(Object.fromEntries(manifest.catalog.filter(entry => sixthApps.some(([id]) => id === entry.id))
    .map(entry => [entry.id, entry.store_title])), {
    "slack": "Slack",
    "trello": "Trello: Personal Planner App",
    "todoist": "Todoist: To Do List & Calendar",
    "ticktick": "TickTick:To Do List & Calendar",
    "evernote": "Evernote - Note Organizer",
    "obsidian": "Obsidian",
    "dropbox": "Dropbox: Secure Cloud Storage",
    "proton-mail": "Proton Mail: Encrypted Email",
    "yahoo-mail": "Yahoo Mail: Email & Planner",
    "google-tasks": "Google Tasks",
    "google-one": "Google One",
    "microsoft-copilot": "Microsoft Copilot",
    "google-gemini": "Google Gemini",
    "claude": "Claude by Anthropic",
    "perplexity": "Perplexity - Ask Anything",
    "bitwarden": "Bitwarden Password Manager",
    "apple-music": "Apple Music",
    "apple-tv": "Apple TV: Shows, Movies & More",
    "hbo-max": "HBO Max: Stream TV & Movies",
    "peacock": "Peacock TV: Stream TV & Movies",
    "paramount-plus": "Paramount+",
    "plex": "Plex: Find Movies & TV Shows",
    "tubi": "Tubi: Free Movies & Live TV",
    "pluto-tv": "Pluto TV: Watch Free Movies/TV",
    "crunchyroll": "Crunchyroll: Anime Streaming",
    "pandora": "Pandora - Music & Podcasts",
    "iheartradio": "iHeart: Music, Radio, Podcasts",
    "siriusxm": "SiriusXM: Music, Sports & Talk",
    "adobe-lightroom": "Lightroom Photo & Video Editor",
    "photoshop-express": "Photoshop Express Photo Editor",
    "snapseed": "Snapseed",
    "picsart": "Picsart AI Photo Editor, Video",
    "strava": "Strava: Run, Bike, Walk",
    "fitbit": "Google Health (Fitbit)",
    "google-fit": "Google Fit: Activity Tracking",
    "myfitnesspal": "MyFitnessPal: Calorie Counter",
    "alltrails": "AllTrails: Hike, Bike & Run",
    "komoot": "komoot - hike, bike & run",
    "amazon-alexa": "Amazon Alexa",
    "ring": "Ring - Always Home",
    "blink": "Blink Home Monitor",
    "google-home": "Google Home",
    "zillow": "Zillow: Homes for Sale & Rent",
    "chase": "Chase Mobile",
    "capital-one": "Capital One Mobile",
    "chime": "Chime\u00ae \u2013 Fee-Free Banking",
    "ups": "UPS",
    "fedex": "FedEx Mobile"
});
  assert.deepEqual(Object.fromEntries(manifest.catalog.filter(entry => foodOrderApps.some(([id]) => id === entry.id))
    .map(entry => [entry.id, entry.store_title])), {
    "chipotle": "Chipotle",
    "taco-bell": "Taco Bell Fast Food & Delivery",
    "wendys": "Wendy’s",
    "burger-king": "BURGER KING® App",
    "dunkin": "Dunkin’",
    "chick-fil-a": "Chick-fil-A®",
    "dominos": "Domino's Pizza USA",
    "pizza-hut": "Pizza Hut - Delivery & Takeout",
    "subway": "Subway®",
    "panera-bread": "Panera Bread",
    "kfc-us": "KFC US: Ordering & Delivery",
    "grubhub": "Grubhub: Food Delivery"
});
  assert.deepEqual(Object.fromEntries(manifest.catalog.filter(entry => travelApps.some(([id]) => id === entry.id))
    .map(entry => [entry.id, entry.store_title])), {
    'fly-delta': 'Fly Delta',
    'united-airlines': 'United Airlines',
    'american-airlines': 'American Airlines',
    'southwest-airlines': 'Southwest Airlines: Travel App',
    amtrak: 'Amtrak',
    transit: 'Transit - Subway & Bus Times',
    moovit: 'Moovit: Your Transit Tracker',
    citymapper: 'Citymapper',
    tripit: 'TripIt: Travel Planner',
    hopper: 'Hopper: Hotels, Flights & Cars',
  });
  assert.deepEqual(Object.fromEntries(manifest.catalog.filter(entry => financeApps.some(([id]) => id === entry.id))
    .map(entry => [entry.id, entry.store_title])), {
    'bank-of-america': 'Bank of America Mobile Banking',
    'wells-fargo': 'Wells Fargo Mobile\u00ae',
    'us-bank': 'U.S. Bank Mobile Banking',
    pnc: 'PNC Mobile', discover: 'Discover Mobile', amex: 'Amex',
    'fidelity-investments': 'Fidelity Investments', schwab: 'Schwab Mobile',
    sofi: 'SoFi: Bank, Invest & Crypto', robinhood: 'Robinhood: Trading & Investing',
  });
  assert.equal(manifest.catalog.find(entry => entry.id === 'discover').android_package, 'com.discoverfinancial.mobile');
  assert.equal(manifest.catalog.find(entry => entry.id === 'capital-one').android_package, 'com.konylabs.capitalone');
  assert.deepEqual(Object.fromEntries(manifest.catalog.filter(entry => weatherApps.some(([id]) => id === entry.id))
    .map(entry => [entry.id, entry.store_title])), {
    accuweather: 'AccuWeather: Weather Radar',
    'weather-channel': 'The Weather Channel - Radar',
    'weather-underground': 'Weather data & microclimate :',
    'windy-com': 'Windy.com - Weather Forecast',
    myradar: 'MyRadar Weather Radar',
    weatherbug: 'Weather Forecast by WeatherBug',
    'one-weather': '1Weather Forecasts & Radar',
    clime: 'Clime: NOAA Weather Radar Live',
    windfinder: 'Windfinder: Wind & Weather map',
    rainviewer: 'RainViewer: Live Weather Radar',
  });
  assert.deepEqual(Object.fromEntries(manifest.catalog.filter(entry => runningTrainingApps.some(([id]) => id === entry.id))
    .map(entry => [entry.id, entry.store_title])), {
    'nike-run-club': 'Nike Run Club - Running Coach',
    'adidas-running': 'adidas Running: Run tracker',
    'asics-runkeeper': 'ASICS Runkeeper: Fitness App',
    'map-my-run': 'Map My Run GPS Running Tracker',
    runna: 'Runna: Running Plans & Coach',
    trainingpeaks: 'TrainingPeaks: Plan Train Lift',
    'zwift-companion': 'Zwift Companion',
    relive: 'Relive: Run, Ride, Hike & more',
  });
  assert.equal(manifest.catalog.find(entry => entry.id === 'asics-runkeeper').android_package, 'com.fitnesskeeper.runkeeper.pro');
  assert.deepEqual(Object.fromEntries(manifest.catalog.filter(entry => learningApps.some(([id]) => id === entry.id))
    .map(entry => [entry.id, entry.store_title])), {
    'google-classroom': 'Google Classroom', 'khan-academy': 'Khan Academy',
    coursera: 'Coursera: Grow your career', udemy: 'Udemy - Online Courses',
    edx: 'edX online learning', quizlet: 'Quizlet: More than Flashcards',
    photomath: 'Photomath', brainly: 'Brainly: AI Homework Helper',
  });
  assert.deepEqual(Object.fromEntries(manifest.catalog.filter(entry => readingApps.some(([id]) => id === entry.id))
    .map(entry => [entry.id, entry.store_title])), {"google-play-books": "Google Play Books & Audiobooks", "libby": "Libby: Read Library Books", "kobo-books": "Kobo | eBooks & Audiobooks", "goodreads": "Goodreads: Book Tracker & More", "wattpad": "Wattpad - Read & Write Stories", "webtoon": "WEBTOON: Manga, Comics, Manhwa", "readera": "ReadEra \u2013 book reader pdf epub", "moon-reader": "Moon+ Reader"});
  assert.equal(manifest.catalog.find(entry => entry.id === 'wattpad').android_package, 'wp.wattpad');
  assert.notEqual(manifest.catalog.find(entry => entry.id === 'runna').android_package,
    manifest.catalog.find(entry => entry.id === 'strava').android_package);
  assert.equal(manifest.exporter_sha256, sha(await readFile(exporter)));
  const license = await readFile(path.join(output, 'LICENSE'));
  assert.deepEqual(license, await readFile(path.join(root, 'LICENSE')));
  assert.deepEqual(manifest.license, { path: 'LICENSE', bytes: license.length, sha256: sha(license) });
  assert.equal(manifest.renderer.mode, 'isolated headless');
  assert.equal(manifest.renderer.network_requests, 0);
  assert.ok(manifest.renderer.browser && manifest.renderer.playwright && manifest.renderer.node);
  assert.equal(manifestBytes.toString().includes(root), false, 'No checkout path enters the export manifest');
  assert.equal(manifestBytes.toString().includes(temporary), false, 'No temporary or user path enters the export manifest');
  const records = new Map(manifest.files.map(record => [record.path, record]));
  assert.equal(records.size, 1124);
  for (const appearance of ['Clair', 'Obscur']) for (const size of [512, 1024]) {
    const hashes = functions.map(name => records.get(`${appearance}/${size}/${name}.png`)?.sha256);
    assert.equal(new Set(hashes).size, 281, `${appearance}/${size} retains 281 distinct drawings`);
    assert.equal(hashes.includes(undefined), false);
  }
  for (const appearance of ['Clair', 'Obscur']) for (const size of [512, 1024]) for (const name of functions) {
    const relative = `${appearance}/${size}/${name}.png`;
    expected.push(relative);
    const bytes = await readFile(path.join(output, relative));
    const record = records.get(relative);
    assert.ok(record);
    assert.equal(record.sha256, sha(bytes)); assert.equal(record.bytes, bytes.length);
    assert.equal(record.source_svg_sha256, sourceBefore[`${appearance}/${name}.svg`]);
    assert.equal(record.width, size); assert.equal(record.height, size);
    assertMonochromePixels(bytes, size, appearance, record, relative);
  }
  assert.deepEqual(Object.keys(await snapshot(output)).sort(), expected.sort());
  assert.deepEqual(await snapshot(source), sourceBefore);
});

for (const version of ['0.1.0', '0.2.0', '0.3.0', '0.4.0', '0.5.0', '0.6.0', '0.7.0', '0.8.0', '0.9.0', '0.10.0', '0.11.0', '0.12.0', '0.13.0', '0.14.0', '0.15.0', '0.16.0', '0.17.0']) test(`accepted ${version} SVG artwork exports its complete PNG set with its own version and source identities`, async () => {
  const historical = {
    '0.1.0': { input: legacySource, before: legacyBefore, functions: baseFunctions, images: 96 },
    '0.2.0': { input: previousSource, before: previousBefore, functions: baseFunctions, images: 96 },
    '0.3.0': { input: firstSource, before: firstBefore, functions: firstFunctions, images: 228,
      apps: firstApps, date: '2026-10-18' },
    '0.4.0': { input: secondSource, before: secondBefore, functions: secondFunctions, images: 324,
      apps: secondApps, date: '2026-10-19' },
    '0.5.0': { input: thirdSource, before: thirdBefore, functions: retainedFunctions, images: 356,
      apps: retainedApps, date: '2026-10-19' },
    '0.6.0': { input: monochromeSource, before: monochromeBefore, functions: retainedFunctions, images: 356,
      apps: retainedApps, date: '2026-10-19', monochrome: true },
    '0.7.0': { input: companionSource, before: companionBefore, functions: companionFunctions, images: 380,
      apps: companionApps, date: '2026-10-19', monochrome: true },
    '0.8.0': { input: broadSource, before: broadBefore, functions: broadFunctions, images: 508,
      apps: broadApps, date: '2026-10-19', monochrome: true },
    '0.9.0': { input: everydaySource, before: everydayBefore, functions: everydayFunctions, images: 700,
      apps: everydayApps, date: '2026-10-19', monochrome: true },
    '0.10.0': { input: foodSource, before: foodBefore, functions: foodFunctions, images: 748,
      apps: foodApps, date: '2026-10-19', monochrome: true },
    '0.11.0': { input: travelSource, before: travelBefore, functions: travelFunctions, images: 788,
      apps: travelCatalogApps, date: '2026-10-20', monochrome: true },
    '0.12.0': { input: financeSource, before: financeBefore, functions: financeFunctions, images: 828,
      apps: financeCatalogApps, date: '2026-10-20', monochrome: true },
    '0.13.0': { input: weatherSource, before: weatherBefore, functions: weatherFunctions, images: 868,
      apps: weatherCatalogApps, date: '2026-10-20', monochrome: true },
    '0.14.0': { input: runningSource, before: runningBefore, functions: runningFunctions, images: 900,
      apps: runningCatalogApps, date: '2026-10-20', monochrome: true },
    '0.15.0': { input: learningSource, before: learningBefore, functions: learningFunctions, images: 932,
      apps: learningCatalogApps, date: '2026-10-21', monochrome: true },
    '0.16.0': { input: readingSource, before: readingBefore, functions: readingFunctions, images: 964,
      apps: readingCatalogApps, date: '2026-10-21', monochrome: true },
    '0.17.0': { input: phoneServiceSource, before: phoneServiceBefore, functions, images: 1124,
      apps, date: '2026-10-21', monochrome: true },
  }[version];
  const historicalSource = historical.input, historicalBefore = historical.before;
  const historicalFunctions = historical.functions, imageCount = historical.images;
  const output = path.join(temporary, `historical-png-${version}`);
  const result = exportTo(historicalSource, output);
  assert.ifError(result.error);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, new RegExp(`Exported ${imageCount} PNG icons`));
  const manifest = JSON.parse(await readFile(path.join(output, 'manifest.json')));
  assert.equal(manifest.version, version);
  assert.equal(manifest.exporter_version, '0.11.0');
  const tokenFile = historical.monochrome ? 'tokens-monochrome.json' : 'tokens.json';
  assert.equal(manifest.tokens_file, tokenFile);
  assert.equal(manifest.tokens_sha256, sha(await readFile(path.join(root, tokenFile))));
  assert.equal(manifest.token_version, historical.monochrome ? '1.0.0' : '0.1.1');
  if (historical.monochrome) assert.equal(manifest.palette_variant, 'monochrome');
  else assert.equal(Object.hasOwn(manifest, 'palette_variant'), false);
  assert.equal(manifest.source_manifest_sha256, historicalBefore['manifest.json']);
  assert.deepEqual(manifest.functions, historicalFunctions);
  if (historical.apps) {
    const svgManifest = JSON.parse(await readFile(path.join(historicalSource, 'manifest.json')));
    for (const field of ['catalog', 'catalog_date', 'catalog_scope']) assert.deepEqual(manifest[field], svgManifest[field]);
    assert.equal(manifest.catalog_date, historical.date, 'Historical inspection date is preserved');
    assert.deepEqual(manifest.catalog.filter(entry => entry.kind === 'app').map(entry =>
      [entry.id, entry.label, entry.android_package]), historical.apps);
    assert.equal(manifest.svg_catalog_sha256, sha(await readFile(path.join(root, 'themeforge/icon_apps.py'))),
      'A new rebuild records the catalog module actually used, without rewriting old PNG deliveries');
  } else for (const field of ['catalog', 'catalog_date', 'catalog_scope', 'svg_catalog_sha256']) {
    assert.equal(Object.hasOwn(manifest, field), false, 'Historical functions do not acquire named-app metadata');
  }
  assert.deepEqual(manifest.sizes, [512, 1024]);
  assert.equal(manifest.renderer.network_requests, 0);
  const expected = ['LICENSE', 'manifest.json'];
  assert.equal(manifest.files.length, imageCount);
  const records = new Map(manifest.files.map(record => [record.path, record]));
  assert.equal(records.size, imageCount);
  for (const appearance of ['Clair', 'Obscur']) for (const size of [512, 1024]) {
    const hashes = [];
    for (const name of historicalFunctions) {
      const relative = `${appearance}/${size}/${name}.png`;
      expected.push(relative);
      const record = records.get(relative);
      assert.ok(record, `${relative} has a manifest record`);
      const bytes = await readFile(path.join(output, relative));
      assert.equal(record.sha256, sha(bytes));
      assert.equal(record.bytes, bytes.length);
      assert.equal(record.source_svg_sha256, historicalBefore[`${appearance}/${name}.svg`]);
      assert.equal(record.width, size); assert.equal(record.height, size);
      hashes.push(record.sha256);
      if (historical.monochrome) assertMonochromePixels(bytes, size, appearance, record, relative);
      if (name === 'phone' || name === 'camera') {
        const rgba = decodeRgba(bytes, size);
        assert.equal(rgba[3], 0, 'Legacy PNG keeps its transparent corner');
        assert.ok(rgba.some((value, index) => index % 4 === 3 && value > 0), 'Legacy drawing remains visible');
      }
    }
    assert.equal(new Set(hashes).size, historicalFunctions.length, `${appearance}/${size} retains every historical drawing`);
  }
  assert.deepEqual(Object.keys(await snapshot(output)).sort(), expected.sort());
  assert.deepEqual(await snapshot(historicalSource), historicalBefore);
  assert.deepEqual(await snapshot(source), sourceBefore);
});

test('unknown and mismatched artwork versions are refused before output reservation or browser launch', async () => {
  const admitted = [['0.1.0', legacySource], ['0.2.0', previousSource], ['0.3.0', firstSource],
    ['0.4.0', secondSource], ['0.5.0', thirdSource], ['0.6.0', monochromeSource], ['0.7.0', companionSource], ['0.8.0', broadSource], ['0.9.0', everydaySource], ['0.10.0', foodSource], ['0.11.0', travelSource], ['0.12.0', financeSource], ['0.13.0', weatherSource], ['0.14.0', runningSource], ['0.15.0', learningSource], ['0.16.0', readingSource], ['0.17.0', phoneServiceSource], ['0.18.0', source]];
  const cases = [['unknown', source, '0.19.0']];
  for (const [actual, original] of admitted) for (const [claimed] of admitted) {
    if (actual !== claimed) cases.push([`${actual}-as-${claimed}`, original, claimed]);
  }
  assert.equal(cases.length, 307, 'All 306 cross-version claims and one unsupported future version are exercised');
  for (const [name, original, version] of cases) {
    const input = path.join(temporary, name);
    await cp(original, input, { recursive: true });
    const manifestPath = path.join(input, 'manifest.json');
    const manifest = JSON.parse(await readFile(manifestPath));
    manifest.version = version;
    await writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
    const before = await snapshot(input);
    const output = path.join(temporary, `${name}-output`);
    assertFailedBeforeBrowser(exportTo(input, output, true), name === 'unknown' ? /unsupported artwork version/ : /Icon output differs/);
    await assert.rejects(lstat(output), { code: 'ENOENT' });
    assert.deepEqual(await snapshot(input), before);
  }
});

test('altered app assignments and mixed previous/current artwork fail admission without changing their evidence', async () => {
  for (const mutation of ['label', 'android_package', 'store_url', 'store_title', 'category',
    'selection_basis', 'catalog_date', 'catalog_scope', 'historical-first-label', 'historical-second-label',
    'historical-third-label', 'historical-monochrome-label', 'mixed-version-svg', 'mixed-version-manifest',
    'previous-monochrome-manifest', 'new-svg-in-historical-monochrome', 'historical-companion-label',
    'previous-companion-manifest', 'new-svg-in-historical-companion', 'historical-broad-label',
    'previous-broad-manifest', 'new-svg-in-historical-broad', 'historical-everyday-label',
    'previous-everyday-manifest', 'new-svg-in-historical-everyday', 'historical-food-label',
    'previous-food-manifest', 'new-svg-in-historical-food', 'travel-label', 'travel-android_package',
    'travel-store_url', 'travel-store_title', 'travel-category', 'travel-selection_basis',
    'historical-travel-label', 'previous-travel-manifest', 'new-svg-in-historical-travel',
    'finance-label', 'finance-android_package', 'finance-store_url', 'finance-store_title',
    'finance-category', 'finance-selection_basis', 'historical-finance-label',
    'previous-finance-manifest', 'new-svg-in-historical-finance',
    'weather-label', 'weather-android_package', 'weather-store_url', 'weather-store_title',
    'weather-category', 'weather-selection_basis', 'historical-weather-label',
    'previous-weather-manifest', 'new-svg-in-historical-weather',
    'running-label', 'running-android_package', 'running-store_url', 'running-store_title',
    'running-category', 'running-selection_basis', 'phone-label', 'phone-android_package',
    'phone-store_url', 'phone-store_title', 'phone-category', 'phone-selection_basis',
    'galaxy-store-url', 'previous-reading-manifest', 'new-svg-in-historical-reading']) {
    const input = path.join(temporary, `assignment-${mutation}`);
    await cp(mutation === 'historical-first-label' ? firstSource :
      mutation === 'historical-second-label' ? secondSource :
      mutation === 'historical-third-label' ? thirdSource :
      ['historical-monochrome-label', 'new-svg-in-historical-monochrome'].includes(mutation) ? monochromeSource :
      ['historical-companion-label', 'new-svg-in-historical-companion'].includes(mutation) ? companionSource :
      ['historical-broad-label', 'new-svg-in-historical-broad'].includes(mutation) ? broadSource :
      ['historical-everyday-label', 'new-svg-in-historical-everyday'].includes(mutation) ? everydaySource :
      ['historical-food-label', 'new-svg-in-historical-food'].includes(mutation) ? foodSource :
      ['historical-travel-label', 'new-svg-in-historical-travel'].includes(mutation) ? travelSource :
      ['historical-finance-label', 'new-svg-in-historical-finance'].includes(mutation) ? financeSource :
      ['historical-weather-label', 'new-svg-in-historical-weather'].includes(mutation) ? weatherSource :
      mutation === 'new-svg-in-historical-reading' ? readingSource : source, input, { recursive: true });
    const manifestPath = path.join(input, 'manifest.json');
    const manifest = JSON.parse(await readFile(manifestPath));
    if (mutation === 'new-svg-in-historical-reading') {
      await cp(path.join(source, 'Clair', 'theme-park.svg'), path.join(input, 'Clair', 'theme-park.svg'));
    } else if (mutation === 'previous-reading-manifest') {
      await cp(path.join(readingSource, 'manifest.json'), manifestPath);
    } else if (mutation === 'new-svg-in-historical-weather') {
      await cp(path.join(source, 'Clair', 'nike-run-club.svg'), path.join(input, 'Clair', 'nike-run-club.svg'));
    } else if (mutation === 'previous-weather-manifest') {
      await cp(path.join(weatherSource, 'manifest.json'), manifestPath);
    } else if (mutation === 'new-svg-in-historical-finance') {
      await cp(path.join(source, 'Clair', 'accuweather.svg'), path.join(input, 'Clair', 'accuweather.svg'));
    } else if (mutation === 'previous-finance-manifest') {
      await cp(path.join(financeSource, 'manifest.json'), manifestPath);
    } else if (mutation === 'new-svg-in-historical-travel') {
      await cp(path.join(source, 'Clair', 'bank-of-america.svg'), path.join(input, 'Clair', 'bank-of-america.svg'));
    } else if (mutation === 'previous-travel-manifest') {
      await cp(path.join(travelSource, 'manifest.json'), manifestPath);
    } else if (mutation === 'new-svg-in-historical-food') {
      await cp(path.join(source, 'Clair', 'fly-delta.svg'), path.join(input, 'Clair', 'fly-delta.svg'));
    } else if (mutation === 'previous-food-manifest') {
      await cp(path.join(foodSource, 'manifest.json'), manifestPath);
    } else if (mutation === 'new-svg-in-historical-everyday') {
      await cp(path.join(source, 'Clair', 'chipotle.svg'), path.join(input, 'Clair', 'chipotle.svg'));
    } else if (mutation === 'previous-everyday-manifest') {
      await cp(path.join(everydaySource, 'manifest.json'), manifestPath);
    } else if (mutation === 'new-svg-in-historical-broad') {
      await cp(path.join(source, 'Clair', 'slack.svg'), path.join(input, 'Clair', 'slack.svg'));
    } else if (mutation === 'previous-broad-manifest') {
      await cp(path.join(broadSource, 'manifest.json'), manifestPath);
    } else if (mutation === 'new-svg-in-historical-companion') {
      await cp(path.join(source, 'Clair', 'youtube-music.svg'), path.join(input, 'Clair', 'youtube-music.svg'));
    } else if (mutation === 'previous-companion-manifest') {
      await cp(path.join(companionSource, 'manifest.json'), manifestPath);
    } else if (mutation === 'new-svg-in-historical-monochrome') {
      await cp(path.join(source, 'Clair', 'good-lock.svg'), path.join(input, 'Clair', 'good-lock.svg'));
    } else if (mutation === 'previous-monochrome-manifest') {
      await cp(path.join(monochromeSource, 'manifest.json'), manifestPath);
    } else if (mutation === 'mixed-version-svg') {
      await cp(path.join(thirdSource, 'Clair', 'github.svg'), path.join(input, 'Clair', 'github.svg'));
    } else if (mutation === 'mixed-version-manifest') {
      await cp(path.join(thirdSource, 'manifest.json'), manifestPath);
    } else {
      if (mutation === 'galaxy-store-url') manifest.catalog.find(entry => entry.id === 'theme-park').store_url += '?extra=1';
      else if (mutation.startsWith('phone-')) manifest.catalog.find(entry => entry.id === 'ace-hardware')[mutation.slice(6)] = 'unqualified replacement';
      else if (mutation.startsWith('catalog_')) manifest[mutation] = 'unqualified replacement';
      else if (mutation === 'historical-first-label') manifest.catalog.find(entry => entry.id === 'google-chrome').label = 'unqualified replacement';
      else if (mutation === 'historical-second-label') manifest.catalog.find(entry => entry.id === 'google-meet').label = 'unqualified replacement';
      else if (mutation === 'historical-third-label') manifest.catalog.find(entry => entry.id === 'microsoft-authenticator').label = 'unqualified replacement';
      else if (mutation === 'historical-monochrome-label') manifest.catalog.find(entry => entry.id === 'github').label = 'unqualified replacement';
      else if (mutation === 'historical-companion-label') manifest.catalog.find(entry => entry.id === 'good-lock').label = 'unqualified replacement';
      else if (mutation === 'historical-broad-label') manifest.catalog.find(entry => entry.id === 'youtube-music').label = 'unqualified replacement';
      else if (mutation === 'historical-everyday-label') manifest.catalog.find(entry => entry.id === 'slack').label = 'unqualified replacement';
      else if (mutation === 'historical-food-label') manifest.catalog.find(entry => entry.id === 'chipotle').label = 'unqualified replacement';
      else if (mutation === 'historical-travel-label') manifest.catalog.find(entry => entry.id === 'fly-delta').label = 'unqualified replacement';
      else if (mutation === 'historical-finance-label') manifest.catalog.find(entry => entry.id === 'bank-of-america').label = 'unqualified replacement';
      else if (mutation === 'historical-weather-label') manifest.catalog.find(entry => entry.id === 'accuweather').label = 'unqualified replacement';
      else if (mutation.startsWith('running-')) manifest.catalog.find(entry => entry.id === 'nike-run-club')[mutation.slice(8)] = 'unqualified replacement';
      else if (mutation.startsWith('weather-')) manifest.catalog.find(entry => entry.id === 'accuweather')[mutation.slice(8)] = 'unqualified replacement';
      else if (mutation.startsWith('finance-')) manifest.catalog.find(entry => entry.id === 'bank-of-america')[mutation.slice(8)] = 'unqualified replacement';
      else if (mutation.startsWith('travel-')) manifest.catalog.find(entry => entry.id === 'fly-delta')[mutation.slice(7)] = 'unqualified replacement';
      else manifest.catalog.find(entry => entry.id === 'slack')[mutation] = 'unqualified replacement';
      await writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
    }
    const before = await snapshot(input);
    const output = path.join(temporary, `assignment-${mutation}-output`);
    assertFailedBeforeBrowser(exportTo(input, output, true), /Icon output differs/);
    await assert.rejects(lstat(output), { code: 'ENOENT' });
    assert.deepEqual(await snapshot(input), before);
  }
});

for (const drift of ['catalog', 'tokens']) test(`a ${drift} edit during export refuses the final manifest and preserves rendered evidence`, async () => {
  // A disposable source copy introduces a harmless module edit at the final
  // qualification boundary. The admitted drawings and input manifest stay valid,
  // so the catalog identity check, rather than an unrelated parse error, must fail.
  const fixture = path.join(temporary, `${drift}-drift-fixture`);
  await mkdir(path.join(fixture, 'tools'), { recursive: true });
  await cp(path.join(root, 'themeforge'), path.join(fixture, 'themeforge'), { recursive: true });
  for (const name of ['tokens.json', 'tokens-monochrome.json', 'LICENSE', 'package.json']) {
    await cp(path.join(root, name), path.join(fixture, name));
  }
  await symlink(path.join(root, 'node_modules'), path.join(fixture, 'node_modules'),
    process.platform === 'win32' ? 'junction' : 'dir');
  const original = await readFile(exporter, 'utf8');
  const boundary = '    // Retain any partial output if source changes or final qualification fails.\n';
  assert.equal(original.split(boundary).length, 2, 'One explicit final qualification boundary is instrumented');
  const fixtureExporter = path.join(fixture, 'tools', 'export-icons.mjs');
  const edited = drift === 'catalog' ? 'themeforge/icon_apps.py' : 'tokens-monochrome.json';
  const append = drift === 'catalog' ? '\\n# Owned drift fixture\\n' : '\\n';
  await writeFile(fixtureExporter, original.replace(boundary, boundary +
    `    await writeFile(path.join(root, '${edited}'), '${append}', { flag: 'a' });\n`));
  const output = path.join(temporary, `${drift}-drift-output`);
  const result = execute(process.execPath, [fixtureExporter, '--input', source, '--output', output]);
  assert.ifError(result.error);
  assert.equal(result.status, 1, result.stdout + result.stderr);
  assert.match(result.stderr, drift === 'catalog' ? /Named-app catalog module changed during export/ : /Tokens changed during export/);
  assert.doesNotMatch(result.stderr, /Icon output differs|browserType\.launch|SyntaxError|ModuleNotFoundError/);
  assert.equal((await lstat(path.join(output, 'Clair', '512', 'google-chrome.png'))).isFile(), true,
    'The source-change refusal retains completed image evidence');
  await assert.rejects(lstat(path.join(output, 'manifest.json')), { code: 'ENOENT' });
  assert.deepEqual(await snapshot(source), sourceBefore);
  assert.equal(await readFile(exporter, 'utf8'), original, 'The real exporter was never patched');
  assert.notEqual(sha(await readFile(path.join(fixture, edited))), sha(await readFile(path.join(root, edited))));
});

test('changed, missing and extra SVG or manifest inputs fail before browser launch and preserve evidence', async () => {
  for (const mutation of ['changed-svg', 'missing-svg', 'extra-svg', 'changed-manifest', 'missing-manifest', 'extra-directory']) {
    const input = path.join(temporary, mutation);
    await cp(source, input, { recursive: true });
    if (mutation === 'changed-svg') await writeFile(path.join(input, 'Clair', 'phone.svg'), '<svg/>');
    if (mutation === 'missing-svg') await rm(path.join(input, 'Clair', 'phone.svg'));
    if (mutation === 'extra-svg') await writeFile(path.join(input, 'Clair', 'extra.svg'), '<svg/>');
    if (mutation === 'changed-manifest') await writeFile(path.join(input, 'manifest.json'), '{}');
    if (mutation === 'missing-manifest') await rm(path.join(input, 'manifest.json'));
    if (mutation === 'extra-directory') await mkdir(path.join(input, 'extra'));
    const before = await snapshot(input);
    const output = path.join(temporary, `${mutation}-output`);
    assertFailedBeforeBrowser(exportTo(input, output, true), /Icon output differs/);
    await assert.rejects(lstat(output), { code: 'ENOENT' });
    assert.deepEqual(await snapshot(input), before);
    if (mutation === 'extra-directory') assert.equal((await lstat(path.join(input, 'extra'))).isDirectory(), true);
  }
});

test('existing, nested-input, root and managed output paths are refused before browser launch', async () => {
  const occupied = path.join(temporary, 'occupied');
  const empty = path.join(temporary, 'empty');
  const existingFile = path.join(temporary, 'existing-file');
  await mkdir(occupied); await writeFile(path.join(occupied, 'keep.txt'), 'preserve');
  await mkdir(empty); await writeFile(existingFile, 'preserve file');
  for (const target of [occupied, empty, existingFile]) {
    assertFailedBeforeBrowser(exportTo(source, target, true), /new output directory/);
  }
  assert.deepEqual(await snapshot(occupied), { 'keep.txt': sha('preserve') });
  assert.deepEqual(await readdir(empty), []);
  assert.equal(await readFile(existingFile, 'utf8'), 'preserve file');
  assertFailedBeforeBrowser(exportTo(source, path.join(source, 'new-output'), true), /must not be inside the SVG input tree/);
  await assert.rejects(lstat(path.join(source, 'new-output')), { code: 'ENOENT' });
  assertFailedBeforeBrowser(exportTo(source, path.parse(root).root, true), /filesystem root/);
  assertFailedBeforeBrowser(exportTo(source, path.join(root, 'dist', 'icon-export-test'), true), /managed desktop dist/);
  assert.deepEqual(await snapshot(source), sourceBefore);
});

test('linked or junction output ancestors are refused before browser launch without modifying their target', async () => {
  const destination = path.join(temporary, 'link-target');
  const linked = path.join(temporary, 'linked-output-parent');
  await mkdir(destination); await writeFile(path.join(destination, 'keep.txt'), 'unchanged');
  await symlink(destination, linked, process.platform === 'win32' ? 'junction' : 'dir');
  assertFailedBeforeBrowser(exportTo(source, path.join(linked, 'png'), true), /links or reparse/);
  assert.deepEqual(await snapshot(destination), { 'keep.txt': sha('unchanged') });
  const linkedInput = path.join(temporary, 'linked-input');
  await symlink(source, linkedInput, process.platform === 'win32' ? 'junction' : 'dir');
  const output = path.join(temporary, 'linked-input-output');
  assertFailedBeforeBrowser(exportTo(linkedInput, output, true), /links or reparse/);
  await assert.rejects(lstat(output), { code: 'ENOENT' });
  assert.deepEqual(await snapshot(source), sourceBefore);
});

test('a linked child manifest is refused before parsing its owned target or launching a browser', async t => {
  for (const [name, contents] of [
    ['malformed', '{owned malformed JSON fixture'],
    ['unsupported', JSON.stringify({ version: '0.19.0' })],
  ]) {
    const input = path.join(temporary, `linked-manifest-${name}`);
    await cp(source, input, { recursive: true });
    const manifestPath = path.join(input, 'manifest.json');
    await rm(manifestPath);
    const target = path.join(temporary, `manifest-target-${name}.json`);
    await writeFile(target, contents);
    try {
      await symlink(target, manifestPath, 'file');
    } catch (error) {
      if (process.platform === 'win32' && ['EPERM', 'EACCES', 'ENOTSUP', 'ENOSYS'].includes(error.code)) {
        t.skip(`Windows file symlink fixture unavailable: ${error.code}`);
        return;
      }
      throw error;
    }
    const before = await snapshot(input);
    const targetBefore = await readFile(target);
    const linkBefore = await readlink(manifestPath);
    const output = path.join(temporary, `linked-manifest-${name}-output`);
    const result = exportTo(input, output, true);
    assertFailedBeforeBrowser(result, /links? or reparse/);
    assert.doesNotMatch(result.stderr, /missing or invalid|unsupported artwork version|JSONDecodeError/,
      'Link refusal must precede target parsing or version admission');
    await assert.rejects(lstat(output), { code: 'ENOENT' });
    assert.equal((await lstat(manifestPath)).isSymbolicLink(), true);
    assert.equal(await readlink(manifestPath), linkBefore);
    assert.deepEqual(await readFile(target), targetBefore);
    assert.deepEqual(await snapshot(input), before);
  }
});

test('a failed renderer retains its newly reserved output and never repairs it on a second attempt', async () => {
  const output = path.join(temporary, 'failed-render-output');
  const result = exportTo(source, output, true);
  assert.ifError(result.error);
  assert.equal(result.status, 1);
  assert.match(result.stderr, /browserType\.launch/);
  assert.equal((await lstat(output)).isDirectory(), true);
  assert.deepEqual(await readdir(output), []);
  assert.deepEqual(await snapshot(source), sourceBefore);
  assertFailedBeforeBrowser(exportTo(source, output, true), /new output directory/);
  assert.deepEqual(await readdir(output), []);
});
