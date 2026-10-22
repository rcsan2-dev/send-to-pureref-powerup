const t = window.TrelloPowerUp.iframe();
const BRIDGE = 'http://127.0.0.1:18765';
const mode = t.arg('mode', 'send');
let payload = null;

const $ = (id) => document.getElementById(id);

function setStatus(message, cls = '') {
  const el = $('status');
  if (!el) return;
  el.textContent = message;
  el.className = 'status ' + cls;
}

function imageLikeAttachment(a) {
  const mime = (a.mimeType || '').toLowerCase();
  const url = (a.url || '').toLowerCase().split('?')[0];
  return mime.startsWith('image/') ||
    /\.(png|jpe?g|webp|gif|bmp|tiff?|svg|avif|heic|heif|exr)$/i.test(url);
}

function bestCoverUrl(cover) {
  if (!cover) return '';
  if (Array.isArray(cover.scaled) && cover.scaled.length) {
    const sorted = cover.scaled.slice().sort((a, b) => (b.width || 0) - (a.width || 0));
    if (sorted[0] && sorted[0].url) return sorted[0].url;
  }
  return cover.url || '';
}

async function prepare() {
  try {
    const card = await t.card('id', 'name', 'desc', 'cover', 'attachments', 'url', 'shortLink');
    const prefs = await Promise.all([
      t.get('member', 'private', 'pureRefIncludeCover', true),
      t.get('member', 'private', 'pureRefIncludeAttachments', true),
      t.get('member', 'private', 'pureRefIncludeDescLinks', true),
      t.get('member', 'private', 'pureRefIncludeHeader', true)
    ]);

    const attachments = (card.attachments || [])
      .filter(imageLikeAttachment)
      .map(a => ({
        id: a.id || '',
        name: a.name || 'reference',
        url: a.url || '',
        mimeType: a.mimeType || ''
      }));

    payload = {
      card: {
        id: card.id,
        shortLink: card.shortLink || '',
        name: card.name || 'Untitled Card',
        desc: card.desc || '',
        url: card.url || ''
      },
      options: {
        includeCover: !!prefs[0],
        includeAttachments: !!prefs[1],
        includeDescLinks: !!prefs[2],
        includeHeader: !!prefs[3]
      },
      coverUrl: prefs[0] ? bestCoverUrl(card.cover) : '',
      attachments: prefs[1] ? attachments : []
    };

    $('cardName').textContent = card.name || 'Untitled Card';
    $('title').textContent = mode === 'open'
      ? 'Open Existing PureRef Board'
      : 'Send to PureRef';

    if (mode === 'open') {
      $('summary').textContent = 'Open the existing .pur board for this card.';
      $('run').textContent = 'OPEN EXISTING BOARD';
    } else {
      $('summary').textContent =
        `Create a moodboard with ${payload.attachments.length} image attachment(s).`;
      $('run').textContent = 'SEND TO PUREREF';
    }
  } catch (e) {
    setStatus('Could not read card: ' + e.message, 'err');
    $('run').disabled = true;
  }

  await t.sizeTo('body');
}

$('run').addEventListener('click', async () => {
  if (!payload) return;

  $('run').disabled = true;
  setStatus(mode === 'open' ? 'Looking for existing board...' : 'Building moodboard...');

  try {
    const endpoint = mode === 'open' ? '/open' : '/create';
    const r = await fetch(BRIDGE + endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const j = await r.json();
    if (!r.ok) throw new Error(j.error || r.statusText);

    if (j.status === 'exists') {
      setStatus(
        'Board already exists:\n' + j.path +
        '\n\nUse OPEN EXISTING BOARD.',
        'warn'
      );
    } else {
      setStatus(
        (mode === 'open' ? 'Opened:\n' : 'Created and opened:\n') + (j.path || ''),
        'ok'
      );
    }
  } catch (e) {
    setStatus(
      'Failed: ' + e.message +
      '\n\nMake sure START_PURE_REF_BRIDGE.bat is running.',
      'err'
    );
  } finally {
    $('run').disabled = false;
    await t.sizeTo('body');
  }
});

prepare();
