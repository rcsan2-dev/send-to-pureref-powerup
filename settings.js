const t = window.TrelloPowerUp.iframe();
const BRIDGE = 'http://127.0.0.1:18765';
const $ = (id) => document.getElementById(id);

function setStatus(message, cls = '') {
  const el = $('status');
  el.textContent = message;
  el.className = 'status ' + cls;
}

function setState(id, text, cls) {
  const el = $(id);
  el.textContent = text;
  el.className = 'state ' + cls;
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
    setStatus('Could not load Trello settings: ' + e.message, 'err');
  }
}

async function testBridge() {
  $('permissionHelp').hidden = true;
  setState('bridgeState', 'Testing…', 'neutral');
  setState('pureState', 'Testing…', 'neutral');
  setState('folderState', 'Testing…', 'neutral');
  setStatus('Testing local Bridge…');

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 5000);
  try {
    const r = await fetch(BRIDGE + '/health', {
      cache: 'no-store',
      signal: controller.signal
    });
    const j = await r.json();
    if (!r.ok) throw new Error(j.error || r.statusText);

    setState('bridgeState', 'Connected ' + (j.version || ''), 'good');
    setState('pureState', j.pureref_found ? 'Detected' : 'Not found', j.pureref_found ? 'good' : 'bad');
    setState('folderState', j.root_folder ? 'Configured' : 'Missing', j.root_folder ? 'good' : 'bad');

    let msg = 'Bridge connected.';
    msg += '\nPureRef: ' + (j.pureref_found ? 'detected' : 'not detected');
    msg += '\nFolder: ' + (j.root_folder || '(not configured)');
    if (!j.pureref_found) msg += '\n\nOpen Local Settings and select PureRef.exe.';
    setStatus(msg, j.pureref_found ? 'ok' : 'warn');
  } catch (e) {
    setState('bridgeState', 'Not reachable', 'bad');
    setState('pureState', 'Unknown', 'neutral');
    setState('folderState', 'Unknown', 'neutral');
    $('permissionHelp').hidden = false;
    setStatus(
      'Could not reach the local Bridge.\n\n' +
      '1. Install/run SendToPureRef_Setup.exe.\n' +
      '2. Open Local Settings.\n' +
      '3. If Chrome asks, allow Apps on device / Local network access.\n' +
      '4. Retry Test Connection.',
      'err'
    );
  } finally {
    clearTimeout(timer);
    await t.sizeTo('body');
  }
}

$('test').addEventListener('click', testBridge);

$('openLocal').addEventListener('click', () => {
  window.open(BRIDGE + '/', '_blank', 'noopener,noreferrer');
});

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

loadSettings();
