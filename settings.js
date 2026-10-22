const t = window.TrelloPowerUp.iframe();
const BRIDGE = 'http://127.0.0.1:18765';

const $ = (id) => document.getElementById(id);

function setStatus(message, cls = '') {
  const el = $('status');
  if (!el) return;
  el.textContent = message;
  el.className = 'status ' + cls;
}

async function loadSettings() {
  try {
    const values = await Promise.all([
      t.get('member', 'private', 'pureRefEnabled', false),
      t.get('member', 'private', 'pureRefIncludeCover', true),
      t.get('member', 'private', 'pureRefIncludeAttachments', true),
      t.get('member', 'private', 'pureRefIncludeDescLinks', true),
      t.get('member', 'private', 'pureRefIncludeHeader', true)
    ]);

    $('enabled').checked = !!values[0];
    $('includeCover').checked = !!values[1];
    $('includeAttachments').checked = !!values[2];
    $('includeDescLinks').checked = !!values[3];
    $('includeHeader').checked = !!values[4];
    await t.sizeTo('body');
  } catch (e) {
    setStatus('Could not load settings: ' + e.message, 'err');
  }
}

$('save').addEventListener('click', async () => {
  try {
    await t.set('member', 'private', {
      pureRefEnabled: $('enabled').checked,
      pureRefIncludeCover: $('includeCover').checked,
      pureRefIncludeAttachments: $('includeAttachments').checked,
      pureRefIncludeDescLinks: $('includeDescLinks').checked,
      pureRefIncludeHeader: $('includeHeader').checked
    });
    setStatus('Settings saved for your Trello user.', 'ok');
    setTimeout(() => t.closePopup(), 700);
  } catch (e) {
    setStatus('Could not save settings: ' + e.message, 'err');
  }
});

$('test').addEventListener('click', async () => {
  setStatus('Testing local bridge...');
  try {
    const r = await fetch(BRIDGE + '/health', { cache: 'no-store' });
    const j = await r.json();

    if (!r.ok) {
      throw new Error(j.error || r.statusText);
    }

    setStatus(
      'Connected.\nPureRef: ' + (j.pureref_found ? 'found' : 'not configured') +
      '\nRoot: ' + (j.root_folder || '(not configured)'),
      j.pureref_found ? 'ok' : 'warn'
    );
  } catch (e) {
    setStatus(
      'Bridge not detected.\nStart START_PURE_REF_BRIDGE.bat on this computer.',
      'err'
    );
  }
});

loadSettings();
