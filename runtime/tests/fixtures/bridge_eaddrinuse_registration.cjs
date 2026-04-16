'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const vm = require('node:vm');

const extensionPath = path.resolve(__dirname, '..', '..', 'bridge', 'extension.js');
const extensionSource = fs.readFileSync(extensionPath, 'utf8');

function loadExtension(stubs) {
    const module = { exports: {} };
    const sandbox = {
        Buffer,
        clearTimeout,
        console,
        module,
        exports: module.exports,
        process: {
            env: stubs.env || {},
            pid: 4321
        },
        require: (name) => {
            if (name === 'crypto') {
                return require('node:crypto');
            }
            if (name === 'fs') {
                return stubs.fs;
            }
            if (name === 'net') {
                return stubs.net;
            }
            if (name === 'os') {
                return stubs.os || os;
            }
            if (name === 'path') {
                return path;
            }
            if (name === 'vscode') {
                return stubs.vscode;
            }
            throw new Error(`Unexpected module: ${name}`);
        },
        setTimeout
    };

    vm.runInNewContext(extensionSource, sandbox, { filename: extensionPath });
    return module.exports;
}

async function main() {
    let errorHandler;
    let writeFileCalls = 0;
    let unlinkCalls = 0;

    const fsStub = {
        existsSync: (targetPath) => {
            const normalized = String(targetPath).replace(/\//g, '\\').toLowerCase();
            return normalized.endsWith('\\.eide\\eide.yml') || normalized.includes('\\registrations\\');
        },
        promises: {
            mkdir: async () => undefined,
            writeFile: async () => {
                writeFileCalls += 1;
            }
        },
        unlinkSync: () => {
            unlinkCalls += 1;
        }
    };

    const server = {
        close: () => undefined,
        listen: (_pipePath, _callback) => {
            errorHandler({ code: 'EADDRINUSE' });
        },
        once: (eventName, handler) => {
            if (eventName === 'error') {
                errorHandler = handler;
            }
        },
        removeListener: () => undefined
    };

    const extension = loadExtension({
        fs: fsStub,
        net: {
            createServer: () => server
        },
        vscode: {
            workspace: {
                workspaceFile: {
                    fsPath: 'C:\\work\\demo\\demo.code-workspace'
                },
                workspaceFolders: [
                    {
                        uri: {
                            fsPath: 'C:\\work\\demo'
                        }
                    }
                ]
            }
        }
    });

    const context = { subscriptions: [] };
    await extension.activate(context);

    assert.equal(writeFileCalls, 0, 'non-owning bridge instances stay read-only');
    assert.equal(context.subscriptions.length, 1, 'activation still registers a disposer');

    context.subscriptions[0].dispose();
    assert.equal(unlinkCalls, 0, 'non-owning bridge instances leave shared registration intact');
}

main().catch((error) => {
    console.error(error && error.stack ? error.stack : error);
    process.exitCode = 1;
});
