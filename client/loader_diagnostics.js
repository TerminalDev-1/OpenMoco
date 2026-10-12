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
            function configureLocalKey(owner) {
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
                    Interceptor.attach(owner.base.add(0xa35d2c), {
                        onEnter(args) {
                            try {
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
                                            const create = new NativeFunction(table.add(0x18).readPointer(), 'pointer', ['pointer','int']);
                                            const rows = [];
                                            for (const type of [...Array.from({length: 200}, (_,i) => 20000+i), ...Array.from({length: 100}, (_,i) => 24100+i)]) {
                                                const object = create(factory,type);
                                                if (object.isNull()) { rows.push({type, supported: false}); continue; }
                                                const vt = object.readPointer();
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
                return { allowed: true, address: copy, length };
            }
            for (const name of ['connect', 'sendto']) {
                const address = Module.getGlobalExportByName(name);
                const types = name === 'connect' ? ['int', 'pointer', 'uint'] : ['int', 'pointer', 'ulong', 'int', 'pointer', 'uint'];
                const original = new NativeFunction(address, name === 'connect' ? 'int' : 'long', types);
                Interceptor.replace(address, new NativeCallback(function (...args) {
                    const index = name === 'connect' ? 1 : 4;
                    const routed = route(args[index], args[index + 1], this.returnAddress);
                    if (!routed.allowed) { errno().writeS32(113); return -1; }
                    args[index] = routed.address;
                    return original(...args);
                }, name === 'connect' ? 'int' : 'long', types));
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
