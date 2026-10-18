'use strict';

const logWrite = new NativeFunction(Module.getGlobalExportByName('__android_log_write'), 'int', ['int', 'pointer', 'pointer']);
const tag = Memory.allocUtf8String('MocoDiagnostic');
function log(text) {
    logWrite(4, tag, Memory.allocUtf8String(String(text)));
}

rpc.exports = {
    init(stage, parameters) {
        log('Offline loader diagnostics initialized');
        const localNetwork = parameters.local_network === true;
        const gameSockets = new Set();
        const errno = new NativeFunction(Module.getGlobalExportByName('__errno'), 'pointer', []);
        const loopback4 = Memory.allocUtf8String('127.0.0.1');
        const loopback6 = Memory.allocUtf8String('::1');
        for (const resolver of [
            { name: 'getaddrinfo', types: ['pointer', 'pointer', 'pointer', 'pointer'], result: 3 },
            { name: 'android_getaddrinfofornet', types: ['pointer', 'pointer', 'pointer', 'uint', 'uint', 'pointer'], result: 5 },
            { name: 'android_getaddrinfofornetcontext', types: ['pointer', 'pointer', 'pointer', 'pointer', 'pointer'], result: 4 }
        ]) {
            const address = Module.findGlobalExportByName(resolver.name);
            if (address === null) { log('Offline resolver export unavailable: ' + resolver.name); continue; }
            const original = new NativeFunction(address, 'int', resolver.types);
            Interceptor.replace(address, new NativeCallback(function (...args) {
                try { log('Intercepted DNS request: ' + args[0].readUtf8String()); } catch (_) {}
                if (localNetwork) {
                    const family = args[2].isNull() ? 0 : args[2].add(4).readS32();
                    args[0] = family === 10 ? loopback6 : loopback4;
                    errno().writeS32(0);
                    return original(...args);
                }
                if (!args[resolver.result].isNull()) args[resolver.result].writePointer(ptr(0));
                errno().writeS32(0);
                // A normal unresolved-host result is handled by the game's
                // IOException path; no resolver/network request is made.
                return 8;
            }, 'int', resolver.types));
            log('Offline DNS guard installed: ' + resolver.name);
        }
        if (localNetwork) {
            let gameDumped = false;
            let gameKeyConfigured = false;
            let apartmentProbeInstalled = false;
            let localIdlePolicyInstalled = false;
            let localMapControlInstalled = false;
            function installLocalMapControl(owner) {
                if (localMapControlInstalled) return;
                // Native battlehud hides its map hit target in tutorial scenes.
                // Only this UI decision changes; tutorial completion is untouched.
                const predicate = owner.base.add(0x6c2884);
                const actual = Array.from(new Uint8Array(predicate.readByteArray(8)))
                    .map(value => value.toString(16).padStart(2, '0')).join('');
                const caller = owner.base.add(0x499b10);
                const callBytes = Array.from(new Uint8Array(caller.sub(8).readByteArray(12)))
                    .map(value => value.toString(16).padStart(2, '0')).join('');
                if (actual !== '00204439c0035fd6' || callBytes !== '000440f95ea30894c0000036')
                    throw new Error('Unsupported local map-control instruction signature');
                Interceptor.attach(predicate, {
                    onEnter() { this.mapCaller = this.returnAddress.equals(caller); },
                    onLeave(value) { if (this.mapCaller) value.replace(0); }
                });
                localMapControlInstalled = true;
                log('Local tutorial map control enabled');
            }
            function installLocalIdlePolicy(owner) {
                if (localIdlePolicyInstalled) return;
                // 13.5.1's idle-close method sets connection state 9 and
                // closes TCP. State 9 maps to the auto-disconnect dialog.
                const address = owner.base.add(0x7fe3d8);
                const actual = Array.from(new Uint8Array(address.readByteArray(20)))
                    .map(value => value.toString(16).padStart(2, '0')).join('');
                if (actual !== 'fd7bbea9f30b00f9fd030091080040f921018052')
                    throw new Error('Unsupported local idle-close instruction signature');
                // Background resume can exceed the prediction-gap allowance
                // before a fresh acknowledgement is processed. The caller
                // otherwise stops simulation even though idle close is suppressed.
                // Skip only that local-test policy branch; real socket loss
                // still uses the connection's ordinary error/reconnect handling.
                const gapBranch = owner.base.add(0x60e7fc);
                if (gapBranch.readU32() !== 0x540003ad)
                    throw new Error('Unsupported local frame-gap instruction signature');
                Memory.patchCode(gapBranch, 4, code => code.writeU32(0x1400001d));
                let logged = false;
                Interceptor.replace(address, new NativeCallback(function () {
                    if (!logged) { log('Local automatic idle close suppressed'); logged = true; }
                }, 'void', ['pointer']));
                localIdlePolicyInstalled = true;
                log('Local idle-close policy installed');
            }

            let battleBridgeInstalled = false;
            function installBattleBridge(owner) {
                if (battleBridgeInstalled) return;
                for (const [offset, signature] of [[0x5bf784,'ffc301d1fd7b01a9fc6f02a9fa6703a9'],
                    [0x738e58,'fd7bbca9f85f01a9f65702a9f44f03a9'],
                    [0x73a364,'fd7bbea9f30b00f9fd030091089c41b9'],
                    [0x5c10f4,'080440f9680000b4001940f9c0035fd6'],
                    [0x57f870,'ff0302d1eb2b036de923046dfd7b05a9'],
                    [0x5c3654,'fd7bbda9f50b00f9f44f02a9fd03009100168052f30302aaf40301aad4ce229468490090'+
                        'f50300aa085d40f9010140f974860694e00315aae10314aaa3860694e00315aae10313aabc860694'+
                        '484f00d008c12f91000140f9080040f9020140f9e10315aaf44f42a9f50b40f9fd7bc3a840001fd6'],
                    [0x761770,'ff0302d1fd7b06a9f44f07a9fd830191f30300aaa900229460220091b0d70594']]) {
                    const bytes = Array.from(new Uint8Array(owner.base.add(offset).readByteArray(signature.length / 2)))
                        .map(v => v.toString(16).padStart(2,'0')).join('');
                    if (bytes !== signature) throw new Error('Unsupported battle bridge signature');
                }
                const vector = new NativeFunction(owner.base.add(0x725fac),'pointer',['pointer','int']);
                // Kill reports travel on the game connection: the client's own desync
                // report 18855 (0x5c3654: message 0x765054, buffers 0x76511c/0x76518c
                // zlib-compress a native string via 0x8f6f30, then the game messaging
                // [0xfadbf0] sends it). Strings: +4 length, +8 inline below 8 bytes,
                // else a data pointer (0xa3874c, 0x8f6f30). The second buffer is null.
                const sendDesyncReport = new NativeFunction(owner.base.add(0x5c3654),'void',['pointer','pointer','pointer']);
                let battle = null;
                // XP bar display, supplied by the server: XP before this battle and
                // the per-level XP table. Battle XP itself arrives as the game's own
                // XP event (28852/1217), decided by the server from raw kill reports.
                const nativeNew = new NativeFunction(owner.base.add(0xe771c0),'pointer',['uint64']);
                // The client's XP level table (0x5c10f4: [[mgr+8]+0x30]; +0 base XP,
                // +8 int vector {data,+8 capacity,+c count}) arrives empty. Level loop
                // 0x788de8 never ends on an empty table once XP > 0 (the old freeze).
                function xpConfig() {
                    const manager = owner.base.add(0xfadbf8).readPointer();
                    if (manager.isNull()) return null;
                    const holder = manager.add(8).readPointer();
                    if (holder.isNull()) return null;
                    const config = holder.add(0x30).readPointer();
                    return config.isNull() || config.add(8).readPointer().isNull() ? null : config;
                }
                function validLevels(levels) {
                    return Array.isArray(levels) && levels.length >= 1 && levels.length <= 200 &&
                        levels.every(v => Number.isInteger(v) && v > 0 && v < 0x40000000);
                }
                // The runner provisions the server's table so it is in place before the
                // battle HUD copies it at scene start; server XP events carry it too.
                let xpLevels = null;
                try {
                    const provisioned = JSON.parse(File.readAllText('/data/user/0/com.supercell.moco.localtest/files/xp-levels.json'));
                    if (validLevels(provisioned)) xpLevels = provisioned;
                } catch (_) {}
                function fillLevelTable(table, where) {
                    if (table.isNull() || table.add(0xc).readS32() !== 0) return;
                    // Native allocation: the game may free this buffer itself.
                    const data = nativeNew(xpLevels.length * 4);
                    xpLevels.forEach((v, i) => data.add(i * 4).writeS32(v));
                    table.writePointer(data);
                    table.add(8).writeS32(xpLevels.length);
                    table.add(0xc).writeS32(xpLevels.length);  // Count last: readers check it.
                    log('Installed private-server XP level table in '+where+' ('+xpLevels.length+' levels)');
                }
                function installXpLevels() {
                    const config = xpLevels === null ? null : xpConfig();
                    if (config === null) return false;
                    fillLevelTable(config.add(8).readPointer(), 'client config');
                    return true;
                }
                // The battle XP HUD (bar update 0x57f870, reached every frame from
                // 0x57f864) keeps its own table copy at +0x1c8 (+0x198 shares it). On a
                // cold launch it is copied before the config exists, so fill it once
                // from the first HUD update, then detach to keep Mainloop free.
                // It also has its own base XP at +0x178 (0 here); the bar shows base plus
                // battle XP. Both are written on Mainloop while the HUD is live, then the
                // hook detaches, so it runs only for the first frames of a battle.
                // The apartment also reaches 0x57f870, so the hook acts only while a
                // battle is live and fills the HUD table once per scene.
                let hudWatch = null, hudReady = false, hudBase = null, hudTableDone = false;
                function stopHudWatch() {
                    hudReady = true;
                    const listener = hudWatch;
                    hudWatch = null;
                    if (listener !== null) setTimeout(() => listener.detach(), 0);
                }
                function watchHud() {
                    if (hudWatch !== null || hudReady || battle === null || xpLevels === null) return;
                    hudWatch = Interceptor.attach(owner.base.add(0x57f870),{onEnter(args) {
                        if (hudReady || battle === null) return;
                        try {
                            if (!hudTableDone) {
                                hudTableDone = true;
                                installXpLevels();
                                fillLevelTable(args[0].add(0x1c8).readPointer(), 'battle HUD');
                            }
                            // Shrine Canyon's battle-start configuration already gives the
                            // HUD its base; elsewhere it arrives with the first XP event,
                            // which re-arms this hook once.
                            if (hudBase !== null) args[0].add(0x178).writeS32(hudBase);
                        } catch (error) { log('HUD XP display rejected: '+error); }
                        stopHudWatch();  // Detaches outside the native callback.
                    }});
                }
                // Server display data is applied on the Frida JS thread. Only JS state
                // changes there; the native table and base XP writes wait for the next
                // 0x73a364 call on Mainloop, which happens only while a battle HUD is
                // live. Data for an earlier battle (after Leave Battle or a new
                // scene start) is dropped instead of written.
                let pendingXp = null, pendingJobs = null;
                function applyXpDisplay(result, current) {
                    if (Array.isArray(result.jobs) && result.jobs.length <= 8 &&
                        result.jobs.every(v => Number.isInteger(v) && v >= 0 && v <= 100000))
                        pendingJobs = {battle: current, jobs: result.jobs};
                    if (validLevels(result.xp_levels)) xpLevels = result.xp_levels;
                    if (!Number.isInteger(result.xp_before_battle) || result.xp_before_battle < 0) return;
                    if (hudBase === null) { hudBase = result.xp_before_battle; hudReady = false; }
                    watchHud();
                    pendingXp = {battle: current, base: result.xp_before_battle};
                }
                function applyPendingXp() {
                    const pending = pendingXp;
                    pendingXp = null;
                    if (pending.battle !== battle || !installXpLevels()) return;
                    xpConfig().writeS32(pending.base);
                }
                // In-battle jobs tracker: the server sends today's job progress in the
                // order of the battle configuration's quest list (+0x20, 0x78ecf8).
                // The tracker animates a quest when its progress (+8) passes the shown
                // value (+0x70); its own kill counting (0x485f50) reads a frame copy
                // that never sees kills on this server. Only raises type-1 progress,
                // never past the quest's target (+0xc). Mainloop only.
                function applyPendingJobs() {
                    const pending = pendingJobs;
                    pendingJobs = null;
                    if (pending.battle !== battle) return;
                    const config = xpConfig();
                    if (config === null) return;
                    const list = config.add(0x20).readPointer();
                    if (list.isNull()) return;
                    const count = list.add(0x24).readS32(), items = list.add(0x18).readPointer();
                    if (count < 0 || count > 8 || items.isNull()) return;
                    for (let i = 0; i < Math.min(count, pending.jobs.length); i++) {
                        const quest = items.add(i * 8).readPointer();
                        if (quest.isNull() || quest.add(4).readS32() !== 1) continue;
                        const progress = pending.jobs[i];
                        if (progress > quest.add(8).readS32() && progress <= quest.add(0xc).readS32())
                            quest.add(8).writeS32(progress);
                    }
                }
                function dataId(data) {
                    const ref = data.add(0x18);
                    return new NativeFunction(ref.readPointer().add(0x10).readPointer(),'uint64',['pointer'])(ref).toString();
                }
                function belongs(player) {
                    return battle !== null && player.add(0x1e8).readPointer().readU64().toString() === battle.account;
                }
                function counts(player) {
                    const meta = player.add(0x1e8).readPointer(), result = {};
                    const size = meta.add(0xa4).readS32(), start = meta.add(0x98).readPointer();
                    if (size < 0 || size > 4096) throw new Error('Invalid killedEnemies vector');
                    for (let i=0; i<size; i++) {
                        const entry = start.add(i*8).readPointer();
                        const id = dataId(entry.add(0x10).readPointer());
                        // Raw counts for every killed character; the server decides what they are worth.
                        if (!(id in result) && Object.keys(result).length >= 256) continue;
                        result[id] = (result[id] || 0) + entry.add(0x18).readS32();
                    }
                    return result;
                }
                // Raw cumulative counts go to the server in an 18855 on Mainloop (the
                // 0x73a364 hook below), at most once a second and only when changed.
                // The server credits them for the battle its session is in; TCP keeps
                // the reports in order with Leave Battle and scene changes.
                function sendReport() {
                    if (Date.now() - battle.sentAt < 1000) return;
                    const report = JSON.stringify({openmoco:'kills',counts:battle.counts});
                    if (report === battle.sent) return;
                    if (report.length > 8192 || owner.base.add(0xfadbf0).readPointer().isNull()) return;
                    const text = Memory.allocUtf8String(report), string = Memory.alloc(16);
                    string.add(4).writeS32(report.length);  // Always >= 8: a data pointer.
                    string.add(8).writePointer(text);
                    sendDesyncReport(ptr(0), string, ptr(0));  // Copies (compresses) the text.
                    battle.sent = report;
                    battle.sentAt = Date.now();
                    log('Sent private-server kill report on the game connection ('+Object.keys(battle.counts).length+' characters)');
                }
                // Server display data (job progress, the bar's base XP, the levels)
                // trails the server's 28852 XP events: ASCII JSON, its 4-byte
                // big-endian length, then 'OMCO'. The native decoder 0x761770 reads
                // only the frame and the events; the bridge reads the trailer from
                // the end of the message stream (+8: +0x18 length, +0x38 data,
                // 0x8d7b2c) and handles it later on the JS thread.
                Interceptor.attach(owner.base.add(0x761770),{onEnter(args) { this.message = args[0]; },onLeave() {
                    try {
                        const stream = this.message.add(8), length = stream.add(0x18).readS32();
                        const data = stream.add(0x38).readPointer();
                        if (data.isNull() || length < 13 || length > 65536 || data.add(length - 4).readU32() !== 0x4f434d4f) return;
                        const size = data.add(length - 8).readU32();
                        const bytes = (size >>> 24) | ((size >>> 8) & 0xff00) | ((size << 8) & 0xff0000) | ((size & 0xff) << 24);
                        if (bytes <= 0 || bytes > 4096 || bytes > length - 13) return;
                        const text = data.add(length - 8 - bytes).readUtf8String(bytes), current = battle;
                        setTimeout(() => {
                            try { if (battle === current && current !== null) applyXpDisplay(JSON.parse(text), current); }
                            catch (error) { log('Server display data rejected: '+error); }
                        }, 0);
                    } catch (error) { log('Server display trailer rejected: '+error); }
                }});
                Interceptor.attach(owner.base.add(0x5bf784),{onEnter(args) {
                    pendingXp = null;
                    pendingJobs = null;
                    hudReady = false;
                    hudBase = null;
                    hudTableDone = false;
                    try { installXpLevels(); } catch (error) { log('XP level table rejected: '+error); }
                    try {
                        const frame = args[1].add(0xa0).readPointer().add(0x28).readPointer();
                        const players = vector(frame,2009);
                        // Battles have monsters (2002) or monster zones (2008; Shrine Canyon starts with zones only).
                        const hostile = vector(frame,2002).add(12).readS32() + vector(frame,2008).add(12).readS32();
                        if (hostile === 0 || players.add(12).readS32() === 0) battle = null;
                        else {
                            const player = players.readPointer().readPointer();
                            battle = {account:player.add(0x1e8).readPointer().readU64().toString(),
                                counts:counts(player),sent:null,sentAt:0};
                            log('Private-server battle progress bridge active');
                        }
                    } catch (error) { battle = null; log('Battle bridge scene rejected: '+error); }
                    if (battle === null) stopHudWatch();
                    else try { watchHud(); } catch (error) { log('HUD XP watch rejected: '+error); }
                }});
                // Do not force the tutorial's loot-disabled setting (6c2894): enabled
                // XP drops froze Mainloop after warm battle reentry. The server
                // credits XP from reported kills instead.
                Interceptor.attach(owner.base.add(0x738e58),{onEnter(args) { this.player = args[0]; },onLeave() {
                    try { if (belongs(this.player)) battle.counts = counts(this.player); }
                    catch (error) { log('Battle outcome rejected: '+error); }
                }});
                // 0x73a364 returns the local player's battle XP for the HUD (callers
                // 0x612758, 0x60d2a8, 0x60ebf0). It runs on Mainloop only while a battle
                // HUD is live, so queued server base XP is applied and kill reports
                // are sent here. Its result is not changed: server XP is already in
                // the simulation (event 1217).
                Interceptor.attach(owner.base.add(0x73a364),{onLeave() {
                    if (battle !== null) {
                        try { sendReport(); } catch (error) { log('Kill report rejected: '+error); }
                    }
                    if (pendingXp !== null) {
                        try { applyPendingXp(); } catch (error) { log('XP display rejected: '+error); }
                    }
                    if (pendingJobs !== null) {
                        try { applyPendingJobs(); } catch (error) { log('Job display rejected: '+error); }
                    }
                }});
                battleBridgeInstalled = true;
                log('Private-server battle bridge installed');
            }

            function installApartmentProbe(owner) {
                if (parameters.apartment_probe !== true || apartmentProbeInstalled) return;
                apartmentProbeInstalled = true;
                const root = '/data/user/0/com.supercell.moco.localtest/files/diagnostics/';
                try {
                    const script = File.readAllText('/data/user/0/com.supercell.moco.localtest/files/apartment-probe.js');
                    new Function('owner', 'log', script)(owner, log);
                    return;
                } catch (error) { log('Apartment external probe unavailable: '+error); }
            }
            function configureLocalKey(owner) {
                installLocalIdlePolicy(owner);
                installLocalMapControl(owner);
                installBattleBridge(owner);
                let publicKey = parameters.server_public_key;
                const keyPath = '/data/user/0/com.supercell.moco.localtest/files/local-server-public-key.txt';
                try { publicKey = File.readAllText(keyPath).trim(); } catch (_) {}
                if (publicKey === undefined || gameKeyConfigured) return true;
                try {
                    if (!/^[0-9a-f]{64}$/.test(publicKey)) throw new Error('Invalid local public key');
                    const encoded = owner.base.add(0x189738);
                    const masks = owner.base.add(0x189778);
                    function decodeKey() {
                        let value = '';
                        for (let j = 0; j < 16; j++) {
                            const mask = masks.add((31 - j * 2) * 2).readU16();
                            const a = encoded.add(j * 4).readU16() ^ mask;
                            const b = encoded.add(j * 4 + 2).readU16() ^ mask;
                            const shift = 11 - (j % 8);
                            const rotated = ((a | b) << shift) | ((a | b) >>> (16 - shift));
                            const word = (rotated ^ masks.add((31-j)*2).readU16()) & 65535;
                            value += (word & 255).toString(16).padStart(2,'0') + (word >>> 8).toString(16).padStart(2,'0');
                        }
                        return value;
                    }
                    if (decodeKey() !== '94170f4efb518b827d40a3f3f4305856adb49c2ad443816bfc9851611c06754d')
                        throw new Error('13.5.1 key-layout verification failed');
                    const protection = Process.findRangeByAddress(encoded).protection;
                    if (!Memory.protect(encoded, 64, 'rwx')) throw new Error('Key page cannot be updated');
                    try {
                        for (let j = 0; j < 16; j++) {
                            const word = parseInt(publicKey.slice(j*4,j*4+2),16) | (parseInt(publicKey.slice(j*4+2,j*4+4),16) << 8);
                            const value = word ^ masks.add((31-j)*2).readU16();
                            const shift = 11 - (j % 8);
                            const raw = (((value >>> shift) | (value << (16-shift))) ^ masks.add((31-j*2)*2).readU16()) & 65535;
                            encoded.add(j*4).writeU16(raw);
                            encoded.add(j*4+2).writeU16(raw);
                        }
                    } finally { Memory.protect(encoded, 64, protection); }
                    if (decodeKey() !== publicKey) throw new Error('Local key verification failed');
                    gameKeyConfigured = true;
                    log('Configured local server public key for native login encryption');
                    return true;
                } catch (error) { log('Local server key setup failed: ' + error); return false; }
            }
            function route(address, length, caller) {
                if (address.isNull() || length < 4) return { allowed: true, address, length };
                const family = address.readU16();
                if (family !== 2 && family !== 10) return { allowed: true, address, length };
                const owner = Process.findModuleByAddress(caller);
                const oldPort = (address.add(2).readU8() << 8) | address.add(3).readU8();
                const game = owner !== null && owner.name === 'libg.so' && oldPort === 30000;
                if (game && !configureLocalKey(owner)) return { allowed: false, address, length };
                if (game) installApartmentProbe(owner);
                if (game && !gameDumped && parameters.protocol_diagnostics === true) {
                    gameDumped = true;
                    function dumpGame(prefix) { try {
                        const root = '/data/user/0/com.supercell.moco.localtest/files/diagnostics/';
                        for (const segment of [
                            { va: 0, size: 15174656 },
                            { va: 0xe7cc00, size: 482616 },
                            { va: 0xef6940, size: 694104 },
                            { va: 0xfd8000, size: 228212 }
                        ]) {
                            const file = new File(root + prefix + segment.va.toString(16) + '.bin', 'wb');
                            file.write(owner.base.add(segment.va).readByteArray(segment.size));
                            file.flush(); file.close();
                        }
                        const file = new File(root + 'game-metadata.json', 'w');
                        file.write(JSON.stringify({ base: owner.base.toString(), caller: caller.sub(owner.base).toString(), size: owner.size }));
                        file.close();
                        log('Saved loaded game segments at first local connection');
                    } catch (e) { log('Game dump failed: ' + e); } }
                    dumpGame('game-');
                    setTimeout(() => dumpGame('game2-'), 10000);
                    Interceptor.attach(owner.base.add(0xa36c6c), {
                        onEnter(args) {
                            try {
                                const size = args[1].toInt32();
                                if (size < 0 || size > 65536) return;
                                const root = '/data/user/0/com.supercell.moco.localtest/files/diagnostics/';
                                const file = new File(root + 'login-crypto-input.json', 'w');
                                const hex = p => Array.from(new Uint8Array(p)).map(v => v.toString(16).padStart(2, '0')).join('');
                                file.write(JSON.stringify({ size,
                                    plaintext: hex(args[0].readByteArray(size)),
                                    nonce: hex(args[4].readByteArray(24)),
                                    key: hex(args[5].readByteArray(32)) }));
                                file.close();
                                log('Saved isolated login encryption inputs');
                            } catch (e) { log('Login input capture failed: ' + e); }
                        }
                    });
                    Interceptor.attach(owner.base.add(0x44d7d0), {
                        onEnter(args) {
                            if (!this.returnAddress.equals(owner.base.add(0x448758))) return;
                            this.nonceOutput = args[1];
                            try {
                                const file = new File('/data/user/0/com.supercell.moco.localtest/files/diagnostics/login-nonce-input.bin', 'wb');
                                file.write(args[0].add(0x60).readByteArray(64));
                                file.close();
                                const state = new File('/data/user/0/com.supercell.moco.localtest/files/diagnostics/login-hash-state.bin', 'wb');
                                state.write(args[0].readByteArray(384)); state.close();
                                log('Saved isolated login nonce hash input');
                            } catch (e) { log('Nonce capture failed: ' + e); }
                        },
                        onLeave() {
                            if (this.nonceOutput === undefined) return;
                            const file = new File('/data/user/0/com.supercell.moco.localtest/files/diagnostics/login-hash-output.bin', 'wb');
                            file.write(this.nonceOutput.readByteArray(24)); file.close();
                        }
                    });
                    let factorySampled = false;
                    let sceneStarting = false;
                    let primitiveTarget=null;
                    let primitiveTrace=[];
                    let primitiveDepth=0;
                    for(const [offset,kind] of [[0x8d7034,'bool'],[0x8d7160,'flag'],[0x8d7294,'int'],[0x8d7bd8,'vint'],[0x8d80ac,'vlong'],[0x8d7778,'long'],[0x8d6bec,'string'],[0x8d6a70,'floatbits']]) {
                        Interceptor.attach(owner.base.add(offset),{onEnter(args){
                            this.primitiveActive=primitiveTarget!==null && args[0].equals(primitiveTarget);
                            if(!this.primitiveActive)return;
                            if(primitiveDepth++>0)return;
                            let value;
                            if(kind==='long'||kind==='vlong')value=args[1].toString();
                            else if(kind==='string'){
                                const text=args[1];const length=text.add(4).readS32();
                                value=length<8?text.add(8).readUtf8String(length):text.add(8).readPointer().readUtf8String(length);
                            }else value=args[1].toInt32();
                            primitiveTrace.push({kind,value});
                        },onLeave(){if(this.primitiveActive)primitiveDepth--;}});
                    }

                    for (const descriptor of [{name:'unlink', index:0}, {name:'unlinkat', index:1}]) {
                        const address = Module.findGlobalExportByName(descriptor.name);
                        if (address === null) continue;
                        Interceptor.attach(address, {
                            onEnter(args) {
                                try {
                                    const path = args[descriptor.index].readUtf8String();
                                    if (path.includes('com.supercell.moco.localtest/cache/sentry/') && path.endsWith('.envelope')) {
                                        File.writeAllText('/data/user/0/com.supercell.moco.localtest/files/diagnostics/home-crash-envelope.txt', File.readAllText(path));
                                        log('Preserved test-client native crash envelope before local cleanup');
                                    }
                                } catch (_) {}
                            }
                        });
                    }
                    Interceptor.attach(owner.base.add(0x5bf784), {
                        onEnter() { sceneStarting = true; log('Native scene-start handler entered'); },
                        onLeave() { log('Native scene-start handler completed'); }
                    });
                    for (const offset of [0x7b1584, 0x762a10, 0x404fe4, 0x5c21e4, 0x5c3904, 0x5c3a68, 0x5c49e8, 0x5bf55c, 0x7f1364, 0x64213c, 0x6b7b14, 0x6b7b1c, 0x77841c, 0x4f4560, 0x5bdee8, 0x755e34, 0x77e0b8, 0x77c010]) {
                        Interceptor.attach(owner.base.add(offset), {
                            onEnter() { log('Scene stage enter: ' + offset.toString(16)); },
                            onLeave() { log('Scene stage leave: ' + offset.toString(16)); }
                        });
                    }
                    Interceptor.attach(owner.base.add(0x8d8adc), {
                        onEnter(args) { try { log('Native diagnostic: ' + args[0].readUtf8String()); } catch (_) {} }
                    });
                    Interceptor.attach(owner.base.add(0xa39800), {
                        onEnter(args) { if (args[1].isNull()) log('Null SCString assignment caller=' + this.returnAddress.sub(owner.base)); }
                    });
                    Interceptor.attach(owner.base.add(0x80d2e8), {
                        onEnter(args) {
                            this.connection = args[0];
                            const id = args[1].add(0x90).readPointer();
                            log('Native login-success handler entered with local account high=' + id.readU32() + ' low=' + id.add(4).readU32());
                        },
                        onLeave() {
                            log('Native login-success handler completed');
                            try {
                                const count = this.connection.add(0x6c).readS32();
                                const list = this.connection.add(0x60).readPointer();
                                const rows = [];
                                for (let i=0; i<count && i<100; i++) {
                                    const observer = list.add(i*8).readPointer();
                                    const vt = observer.readPointer();
                                    rows.push({table: vt.sub(owner.base).toString(), handler: vt.readPointer().sub(owner.base).toString()});
                                }
                                File.writeAllText('/data/user/0/com.supercell.moco.localtest/files/diagnostics/post-login-observers.json', JSON.stringify(rows));
                            } catch (error) { log('Observer inspection failed: ' + error); }
                        }
                    });
                    Interceptor.attach(owner.base.add(0x80b62c), {
                        onEnter(args) {
                            const table = args[0].readPointer();
                            File.writeAllText('/data/user/0/com.supercell.moco.localtest/files/diagnostics/login-handler.json',
                                JSON.stringify({table: table.sub(owner.base).toString(), method: table.add(0x38).readPointer().sub(owner.base).toString(),
                                    caller: this.returnAddress.sub(owner.base).toString(),
                                    trace: Thread.backtrace(this.context, Backtracer.ACCURATE).map(p => p.sub(owner.base).toString())}));
                        }
                    });
                    Interceptor.attach(owner.base.add(0xa36d1c), {
                        onEnter(args) { this.cipherBytes = args[1].toInt32(); },
                        onLeave(result) { log('Native Box reply verification: status=' + result.toInt32() + ' ciphertextBytes=' + this.cipherBytes); }
                    });
                    Interceptor.attach(owner.base.add(0xa35d2c), {
                        onEnter(args) {
                            try {
                                if(args[1].toInt32()===24548) sceneStarting=true;
                                const factory = args[0].add(0x118).readPointer();
                                const table = factory.readPointer();
                                const file = new File('/data/user/0/com.supercell.moco.localtest/files/diagnostics/incoming-factory.json', 'w');
                                file.write(JSON.stringify({ message_type: args[1].toInt32(),
                                    table: table.sub(owner.base).toString(),
                                    methods: Array.from({length: 8}, (_,i) => table.add(i*8).readPointer().sub(owner.base).toString()) }));
                                file.close();
                                if (!factorySampled) {
                                    factorySampled = true;
                                    setTimeout(() => {
                                        try {
                                            if (sceneStarting) { log('Skipped factory probes during scene startup'); return; }
                                            const create = new NativeFunction(table.add(0x18).readPointer(), 'pointer', ['pointer','int']);
                                            const structured = new NativeFunction(owner.base.add(0x8f0610), 'pointer', ['int']);
                                            const makeStream = new NativeFunction(owner.base.add(0x8d6600), 'void', ['pointer','int']);
                                            const makeWriter = new NativeFunction(owner.base.add(0x8ee5c0), 'void', ['pointer','pointer']);
                                            const scRegistry = owner.base.add(0xfbac88).readPointer();
                                            log('SC registry pointer='+scRegistry);
                                            if (!scRegistry.isNull()) {
                                                const count = scRegistry.add(0x14).readS32();
                                                const entries = scRegistry.add(8).readPointer();
                                                const factories=[];
                                                for (let i=0;i<count && i<128;i++) {
                                                    const entry=entries.add(i*8).readPointer();
                                                    factories.push(entry.readPointer().add(0x18).readPointer().sub(owner.base).toString());
                                                }
                                                File.writeAllText('/data/user/0/com.supercell.moco.localtest/files/diagnostics/scdata-factories.json',JSON.stringify(factories));
                                                log('SC registry factories='+factories.join(','));
                                            }
                                            const typeRows=[];
                                            for (const id of [1201,1210,1211,1212,1213,1214,1215,1216,1217,1218,1219,1220,1221,1230,1231,1232,1234,1235,1236,1240,1241,1242,1243,1244,1245]) {
                                                const ref=structured(id);
                                                if(ref.isNull()) continue;
                                                const primary=ref.sub(8);const vt=primary.readPointer();
                                                typeRows.push({id,table:vt.sub(owner.base).toString(),methods:Array.from({length:16},(_,i)=>vt.add(i*8).readPointer().sub(owner.base).toString()),serializer:ref.readPointer().add(0x28).readPointer().sub(owner.base).toString()});
                                            }
                                            File.writeAllText('/data/user/0/com.supercell.moco.localtest/files/diagnostics/scene-types.json',JSON.stringify(typeRows));
                                            for (const type of [1003, 1200, 1004]) {
                                                const value = structured(type);
                                                if (value.isNull()) continue;
                                                const stream = Memory.alloc(0x90); makeStream(stream, 0);
                                                const writer = Memory.alloc(0x18); makeWriter(writer, stream);
                                                const vt = value.readPointer();
                                                new NativeFunction(vt.add(0x28).readPointer(), 'void', ['pointer','pointer'])(value, writer);
                                                const size = stream.add(0x14).readS32();
                                                if (size > 0 && size < 65536) {
                                                    const file = new File('/data/user/0/com.supercell.moco.localtest/files/diagnostics/structured-default-' + type + '.bin', 'wb');
                                                    file.write(stream.add(0x30).readPointer().readByteArray(size)); file.close();
                                                }
                                                log('Structured native sample type=' + type + ' bytes=' + size);
                                            }
                                            try {
                                                const registry = owner.base.add(0xeefa08).readPointer().readPointer();
                                                const getData = new NativeFunction(registry.readPointer().add(0x18).readPointer(), 'pointer', ['pointer','uint64']);
                                                const names = [];
                                                const headers = [];
                                                for (let type=1; type<=4096; type++) {
                                                  for (let row=0; row<4; row++) {
                                                    const id = type * 100000 + row;
                                                    const value = getData(registry, id);
                                                    if (value.isNull()) continue;
                                                    if (headers.length < 100) headers.push({id, bytes: Array.from(new Uint8Array(value.readByteArray(128))).map(v=>v.toString(16).padStart(2,'0')).join('')});
                                                    for (let offset=0; offset<96; offset+=8) {
                                                    try {
                                                        const member = value.add(offset);
                                                        const length = member.add(4).readS32();
                                                        if (length < 1 || length > 128) continue;
                                                        const start = length < 8 ? member.add(8) : member.add(8).readPointer();
                                                        const name = start.readUtf8String(length);
                                                        if (/^[A-Za-z0-9_ .-]+$/.test(name)) names.push({id, offset, name});
                                                    } catch (_) {}
                                                    }
                                                  }
                                                }
                                                File.writeAllText('/data/user/0/com.supercell.moco.localtest/files/diagnostics/data-reference-first-rows.json', JSON.stringify(names));
                                                File.writeAllText('/data/user/0/com.supercell.moco.localtest/files/diagnostics/data-reference-headers.json', JSON.stringify(headers));
                                                log('Saved first-row data-reference names: ' + names.length);
                                                const linked=[];
                                                for(const id of [7500000,6700000,11301483,1300000,11300000,10800000,10900000]) {
                                                    const value=getData(registry,id);
                                                    if(value.isNull())continue;
                                                    const primary=value.sub(0x18);const fields=[];
                                                    for(let off=0x100;off<0x190;off+=8) {
                                                        try{
                                                            const target=primary.add(off).readPointer();
                                                            const text=target.add(0x28);const len=text.add(4).readS32();
                                                            if(len<1||len>100)continue;
                                                            const name=len<8?text.add(8).readUtf8String(len):text.add(8).readPointer().readUtf8String(len);
                                                            if(/^[A-Za-z0-9_ .-]+$/.test(name))fields.push({offset:off,name});
                                                        }catch(_){}
                                                    }
                                                    linked.push({id,fields});
                                                }
                                                File.writeAllText('/data/user/0/com.supercell.moco.localtest/files/diagnostics/starter-data-links.json',JSON.stringify(linked));
                                                const homeData = getData(registry, 10900000);
                                                if (homeData.isNull()) throw new Error('Verified typed Home data reference is unavailable');
                                                const scene = structured(1003);
                                                const frame = structured(1200);
                                                scene.add(0x10).writePointer(homeData.sub(0x18));
                                                scene.add(0x20).writePointer(frame.sub(8));
                                                frame.add(0xa0).writePointer(homeData.sub(0x18));
                                                frame.add(0xd0).writePointer(structured(1240).sub(8));
                                                const message = create(factory, 23491);
                                                message.add(0xa0).writePointer(scene.sub(8));
                                                const profileRegistry=message.add(0x90).readPointer();
                                                const lookupProfile=new NativeFunction(owner.base.add(0x82ab0c),'pointer',['pointer','uint64']);
                                                const resolved=[];
                                                for(const id of [1300000,11300000,11301483,6700000,7500000,2147483648+11301483]) {
                                                    const value=lookupProfile(profileRegistry,id);const globalValue=getData(registry,id);
                                                    let at108='null',name108='';
                                                    try{const target=value.sub(0x18).add(0x108).readPointer();at108=target.toString();
                                                        const text=target.add(0x28);const length=text.add(4).readS32();
                                                        if(length>0&&length<100)name108=length<8?text.add(8).readUtf8String(length):text.add(8).readPointer().readUtf8String(length);
                                                    }catch(_){}
                                                    resolved.push({id,exists:!value.isNull(),same:globalValue.equals(value),at108,name108});
                                                }
                                                File.writeAllText('/data/user/0/com.supercell.moco.localtest/files/diagnostics/profile-data-resolution.json',JSON.stringify(resolved));
                                                const zero = Memory.alloc(4096);
                                                zero.writeByteArray(new Uint8Array(4096));
                                                const stream = Memory.alloc(0x90); makeStream(stream, 0);
                                                new NativeFunction(owner.base.add(0x8d7b2c), 'void', ['pointer','pointer','int'])(stream, zero, 4096);
                                                const state = Memory.alloc(0xb0);
                                                new NativeFunction(owner.base.add(0x761c60), 'void', ['pointer','pointer','pointer'])(state, stream, message.add(0x90).readPointer());
                                                message.add(0xb0).writePointer(state);
                                                message.add(0xb8).writePointer(Memory.alloc(1));
                                                message.add(0xc0).writeS32(0);
                                                new NativeFunction(message.readPointer().add(0x10).readPointer(), 'void', ['pointer'])(message);
                                                const size = message.add(0x1c).readS32();
                                                if (size <= 0 || size > 65536) throw new Error('Unexpected native home-probe body size');
                                                const file = new File('/data/user/0/com.supercell.moco.localtest/files/diagnostics/home-scene-probe-body.bin', 'wb');
                                                file.write(message.add(0x40).readPointer().readByteArray(size)); file.close();
                                                log('Saved native scene-start probe body: ' + size + ' bytes');
                                                const ownMessage=create(factory,24548);
                                                const own=Memory.alloc(0x70);
                                                new NativeFunction(owner.base.add(0x755a34),'void',['pointer'])(own);
                                                const ownStream=Memory.alloc(0x90);makeStream(ownStream,0);
                                                new NativeFunction(owner.base.add(0x8d7b2c),'void',['pointer','pointer','int'])(ownStream,zero,4096);
                                                new NativeFunction(owner.base.add(0x755e34),'void',['pointer','pointer','pointer'])(own,ownStream,message.add(0x90).readPointer());
                                                const requiredHomeList=Memory.alloc(16);requiredHomeList.writeByteArray(new Uint8Array(16));
                                                own.add(0x18).readPointer().add(0xe0).writePointer(requiredHomeList);
                                                const starter=getData(registry,11300000);
                                                if(starter.isNull())throw new Error('Typed StartingWeapon reference unavailable');
                                                own.add(0x18).readPointer().add(0x88).readPointer().add(0x18).writePointer(starter.sub(0x18));
                                                ownMessage.add(0xa0).writePointer(own);
                                                primitiveTrace=[];primitiveTarget=ownMessage.add(8);
                                                new NativeFunction(ownMessage.readPointer().add(0x10).readPointer(),'void',['pointer'])(ownMessage);
                                                primitiveTarget=null;File.writeAllText('/data/user/0/com.supercell.moco.localtest/files/diagnostics/own-home-primitive-trace.json',JSON.stringify(primitiveTrace));
                                                const ownSize=ownMessage.add(0x1c).readS32();
                                                if(ownSize<1 || ownSize>65536)throw new Error('Own-home body limit');
                                                const ownFile=new File('/data/user/0/com.supercell.moco.localtest/files/diagnostics/own-home-probe-body.bin','wb');
                                                ownFile.write(ownMessage.add(0x40).readPointer().readByteArray(ownSize));ownFile.close();
                                                log('Saved native own-home sample: '+ownSize+' bytes');

                                            } catch (error) { log('Data-reference inspection failed: ' + error); }
                                            const rows = [];
                                            for (let type = 1; type <= 65535; type++) {
                                                const object = create(factory,type);
                                                if (object.isNull()) continue;
                                                const vt = object.readPointer();
                                                if (type === 29125) {
                                                    const id = Memory.alloc(8); id.writeU64(0);
                                                    object.add(0x90).writePointer(id);
                                                    new NativeFunction(vt.add(0x10).readPointer(), 'void', ['pointer'])(object);
                                                    const size = object.add(0x1c).readS32();
                                                    if (size > 0 && size < 10000) {
                                                        const encoded = new File('/data/user/0/com.supercell.moco.localtest/files/diagnostics/login-reply-default.bin', 'wb');
                                                        encoded.write(object.add(0x40).readPointer().readByteArray(size)); encoded.close();
                                                        log('Saved native default login reply: ' + size + ' bytes');
                                                    }
                                                }
                                                rows.push({type, supported: true, version: object.add(0x88).readS32(),
                                                    table: vt.sub(owner.base).toString(),
                                                    methods: Array.from({length: 8}, (_,i) => vt.add(i*8).readPointer().sub(owner.base).toString())});
                                            }
                                            File.writeAllText('/data/user/0/com.supercell.moco.localtest/files/diagnostics/message-factory-samples.json', JSON.stringify(rows));
                                            log('Saved native message-factory samples');
                                        } catch (error) { log('Message-factory sampling failed: ' + error); }
                                    }, 500);
                                }
                            } catch (e) { log('Incoming factory capture failed: ' + e); }
                        }
                    });
                }
                const port = game ? parameters.game_port : parameters.sdk_port;
                const copy = Memory.alloc(length);
                copy.writeByteArray(address.readByteArray(length));
                copy.add(2).writeU8(port >> 8); copy.add(3).writeU8(port & 255);
                if (family === 2 && length >= 16) {
                    copy.add(4).writeByteArray([127, 0, 0, 1]);
                } else if (family === 10 && length >= 28) {
                    copy.add(8).writeByteArray([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]);
                    copy.add(24).writeU32(0);
                } else return { allowed: false, address, length };
                log('Local socket route: caller=' + (owner === null ? '?' : owner.name) + ' originalPort=' + oldPort + ' localPort=' + port);
                return { allowed: true, address: copy, length, game };
            }
            for (const name of ['connect', 'sendto']) {
                const address = Module.getGlobalExportByName(name);
                const types = name === 'connect' ? ['int', 'pointer', 'uint'] : ['int', 'pointer', 'ulong', 'int', 'pointer', 'uint'];
                const original = new SystemFunction(address, name === 'connect' ? 'int' : 'long', types);
                Interceptor.replace(address, new NativeCallback(function (...args) {
                    const index = name === 'connect' ? 1 : 4;
                    const routed = route(args[index], args[index + 1], this.returnAddress);
                    if (!routed.allowed) { this.errno = 113; return -1; }
                    args[index] = routed.address;
                    if (parameters.connection_diagnostics === true && name === 'connect' && routed.game) gameSockets.add(args[0]);
                    const result = original(...args);
                    // Nonblocking connect relies on EINPROGRESS surviving
                    // the JavaScript bridge, including warm reconnects.
                    this.errno = result.errno;
                    if (name === 'connect' && routed.game)
                        log('Local game socket result=' + result.value + ' errno=' + result.errno);
                    return result.value;
                }, name === 'connect' ? 'int' : 'long', types));
            }
            if (parameters.connection_diagnostics === true) {
                for (const name of ['close', 'shutdown']) {
                    Interceptor.attach(Module.getGlobalExportByName(name), {
                        onEnter(args) {
                            const fd=args[0].toInt32();
                            if (!gameSockets.has(fd)) return;
                            if (name === 'close') gameSockets.delete(fd);
                            log('Game socket '+name+' fd='+fd+' caller='+DebugSymbol.fromAddress(this.returnAddress));
                            log('Game socket close stack='+Thread.backtrace(this.context,Backtracer.ACCURATE).map(a=>{
                                const module=Process.findModuleByAddress(a);
                                return module===null?a.toString():module.name+'+'+a.sub(module.base);
                            }).join(','));
                        }
                    });
                }
            }
            const sendmsgAddress = Module.getGlobalExportByName('sendmsg');
            const sendmsg = new NativeFunction(sendmsgAddress, 'long', ['int', 'pointer', 'int']);
            Interceptor.replace(sendmsgAddress, new NativeCallback(function (fd, message, flags) {
                const routed = route(message.readPointer(), message.add(8).readU32(), this.returnAddress);
                if (!routed.allowed) { errno().writeS32(113); return -1; }
                const copy = Memory.alloc(56); // ARM64 struct msghdr
                copy.writeByteArray(message.readByteArray(56));
                copy.writePointer(routed.address);
                return sendmsg(fd, copy, flags);
            }, 'long', ['int', 'pointer', 'int']));
            log('Local-network routing installed before original client startup');
        }
        let protectionBase = null;
        Interceptor.attach(Module.getGlobalExportByName('getuid'), {
            onLeave(result) {
                if (protectionBase !== null && this.returnAddress.equals(protectionBase.add(0x2231bc))) {
                    log('Loader UID classification value=' + result.toInt32());
                    result.replace(99000);
                    log('Applied isolated-process classification for offline loader compatibility');
                }
            }
        });
        for (const name of ['open', 'openat', 'access']) {
            const address = Module.findGlobalExportByName(name);
            if (address === null) continue;
            Interceptor.attach(address, {
                onEnter(args) {
                    try {
                        this.path = args[name === 'openat' ? 1 : 0].readUtf8String();
                    } catch (_) { this.path = null; }
                },
                onLeave(result) {
                    if (this.path !== null && (/moco|\.apk|\.dat|\/proc\/self\/maps/.test(this.path))) {
                        log(name + '(' + this.path + ') -> ' + result.toInt32());
                    }
                }
            });
        }
        Process.attachModuleObserver({
            onAdded(module) {
                if (module.name !== 'libsupercell_moco.so') return;
                protectionBase = module.base;
                log('Native protection module loaded: base=' + module.base + ' size=' + module.size);
                try { log('Loader dispatch pointer: ' + module.base.add(0x6d69b0).readPointer()); }
                catch (e) { log('Dispatch read error: ' + e); }
                // Keep protected instructions untouched during initialization.
            }
        });
        Interceptor.attach(Module.getGlobalExportByName('android_dlopen_ext'), {
            onEnter(args) {
                try { this.path = args[0].readUtf8String(); } catch (_) { this.path = ''; }
            },
            onLeave(result) {
                if (!this.path.endsWith('/libsupercell_moco.so')) return;
                log('Protection dlopen returned: ' + result);
                const module = Process.findModuleByName('libsupercell_moco.so');
                if (module !== null) {
                    const dispatch = module.base.add(0x6d69b0).readPointer();
                    log('Post-constructor dispatch=' + dispatch);
                    if (!dispatch.isNull()) log('Dispatch bytes=' + hexdump(dispatch, { length: 32, header: false, ansi: false }));
                    try {
                        const root = '/data/user/0/com.supercell.moco.localtest/files/diagnostics/';
                        for (const segment of [
                            { va: 0, size: 0x6953d0 },
                            { va: 0x6993d0, size: 178904 },
                            { va: 0x6c8ea8, size: 60584 }
                        ]) {
                            const file = new File(root + 'segment-' + segment.va.toString(16) + '.bin', 'wb');
                            file.write(module.base.add(segment.va).readByteArray(segment.size));
                            file.flush(); file.close();
                        }
                        const file = new File(root + 'metadata.json', 'w');
                        file.write(JSON.stringify({ base: module.base.toString(), dispatch: dispatch.toString() }));
                        file.close();
                        log('Saved runtime segments to isolated diagnostic folder');
                    } catch (e) { log('Runtime dump failed: ' + e); }
                    {
                            const getVMsAddress = Module.findGlobalExportByName('JNI_GetCreatedJavaVMs');
                            if (getVMsAddress === null) { log('VM query export unavailable'); return; }
                            const vmOut = Memory.alloc(Process.pointerSize);
                            const countOut = Memory.alloc(4);
                            const getVMs = new NativeFunction(getVMsAddress, 'int', ['pointer', 'int', 'pointer']);
                            if (getVMs(vmOut, 1, countOut) !== 0 || countOut.readS32() !== 1) { log('VM query failed'); return; }
                            const vm = vmOut.readPointer();
                            const envOut = Memory.alloc(Process.pointerSize);
                            const getEnv = new NativeFunction(vm.readPointer().add(6 * Process.pointerSize).readPointer(), 'int', ['pointer', 'pointer', 'int']);
                            const status = getEnv(vm, envOut, 0x10006);
                            log('Diagnostic GetEnv(1.6)=' + status);
                            if (status !== 0) return;
                            const table = envOut.readPointer().readPointer();
                            const classNames = new Map();
                            let reportMethod = null;
                            let reportClass = null;
                            let recordMethod = null;
                            for (const index of [141, 142, 143]) {
                                Interceptor.attach(table.add(index * Process.pointerSize).readPointer(), {
                                    onEnter(callArgs) {
                                        if (reportMethod !== null && recordMethod !== null && callArgs[2].equals(reportMethod)) {
                                            callArgs[1] = reportClass;
                                            callArgs[2] = recordMethod;
                                            log('Recording protection report in offline test harness');
                                            log('Report native caller offset=' + this.returnAddress.sub(module.base));
                                            log('Report native stack=' + Thread.backtrace(this.context, Backtracer.ACCURATE).map(a => a.sub(module.base).toString()).join(','));
                                            try {
                                                for (const address of [0x248000, 0x258000, 0x5c2000, 0x5e6000, 0x19b000, 0x45b000, 0x223000, 0x4db000]) {
                                                    const file = new File('/data/user/0/com.supercell.moco.localtest/files/diagnostics/check-' + address.toString(16) + '.bin', 'wb');
                                                    file.write(module.base.add(address).readByteArray(0x2000)); file.flush(); file.close();
                                                }
                                                log('Saved post-check decrypted code');
                                            } catch (e) { log('Post-check dump failed: ' + e); }
                                        }
                                    }
                                });
                            }
                            for (const spec of [
                                { name: 'FindClass', index: 6, textArg: 1 },
                                { name: 'GetMethodID', index: 33, textArg: 2 },
                                { name: 'GetStaticMethodID', index: 113, textArg: 2 },
                                { name: 'GetFieldID', index: 94, textArg: 2 },
                                { name: 'GetStaticFieldID', index: 144, textArg: 2 },
                                { name: 'NewStringUTF', index: 167, textArg: 1 }
                            ]) {
                                Interceptor.attach(table.add(spec.index * Process.pointerSize).readPointer(), {
                                    onEnter(callArgs) {
                                        this.env = callArgs[0];
                                        this.owner = callArgs[1].toString();
                                        this.fromProtection = this.returnAddress.compare(module.base) >= 0 &&
                                            this.returnAddress.compare(module.base.add(module.size)) < 0;
                                        try { this.label = callArgs[spec.textArg].readUtf8String(); }
                                        catch (_) { this.label = '?'; }
                                        if (spec.name === 'NewStringUTF' && this.label === '16') log('Report string caller offset=' + this.returnAddress.sub(module.base));
                                        if (spec.name === 'NewStringUTF' && this.label === 'com.supercell.moco' &&
                                            this.returnAddress.compare(module.base) >= 0 &&
                                            this.returnAddress.compare(module.base.add(module.size)) < 0) {
                                            this.redirect = Memory.allocUtf8String('com.supercell.moco.localtest');
                                            callArgs[1] = this.redirect;
                                            log('Redirected native package lookup to isolated test package');
                                        }
                                    },
                                    onLeave(value) {
                                        if (this.fromProtection) log(spec.name + '(' + this.label + ')=' + value);
                                        if (spec.name === 'FindClass' && !value.isNull()) classNames.set(value.toString(), this.label);
                                        if (spec.name === 'GetStaticMethodID' && this.label === 'a' &&
                                            classNames.get(this.owner) === 'ixhhs/e' && !value.isNull()) {
                                            reportMethod = ptr(value.toString());
                                            const find = new NativeFunction(table.add(6 * Process.pointerSize).readPointer(), 'pointer', ['pointer', 'pointer']);
                                            const globalRef = new NativeFunction(table.add(21 * Process.pointerSize).readPointer(), 'pointer', ['pointer', 'pointer']);
                                            const getMethod = new NativeFunction(table.add(113 * Process.pointerSize).readPointer(), 'pointer', ['pointer', 'pointer', 'pointer', 'pointer']);
                                            const helper = find(this.env, Memory.allocUtf8String('com/supercell/moco/localtest/DiagnosticFactory'));
                                            if (!helper.isNull()) {
                                                reportClass = globalRef(this.env, helper);
                                                recordMethod = getMethod(this.env, reportClass,
                                                    Memory.allocUtf8String('recordOfflineProtectionReport'), Memory.allocUtf8String('(Ljava/lang/String;)V'));
                                                log('Offline report recorder prepared: ' + recordMethod);
                                            }
                                        }
                                    }
                                });
                            }
                    }
                    Interceptor.flush();
                }
            }
        });
        Interceptor.flush();
        const ready = new File('/data/user/0/com.supercell.moco.localtest/files/diagnostics/bootstrap-ready-' + Process.id, 'w');
        ready.write(localNetwork ? 'local-network' : 'offline'); ready.flush(); ready.close();
    }
};
