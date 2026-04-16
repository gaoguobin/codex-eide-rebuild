'use strict';

// --- Imports ---

const crypto = require('crypto');
const fs = require('fs');
const net = require('net');
const os = require('os');
const path = require('path');
const vscode = require('vscode');

// --- Constants ---

const BRIDGE_VERSION = '0.1.0';
const BRIDGE_LOG_PREFIX = '[eide-rebuild.cli-bridge]';
const REGISTRATION_ENV = 'EIDE_REBUILD_REGISTRATION_ROOT';
const START_TIMEOUT_MS = 15000;
const BUILD_TIMEOUT_MS = 30 * 60 * 1000;
const POLL_INTERVAL_MS = 250;
const SETTLE_DELAY_MS = 700;

let bridgeState;

// --- Activation ---

async function activate(context) {
    const initialState = createBridgeState();
    if (!initialState) {
        return;
    }

    bridgeState = initialState;

    try {
        await startBridgeServer(bridgeState);
        context.subscriptions.push({
            dispose: () => disposeBridgeServer(bridgeState)
        });
    } catch (error) {
        console.error(`${BRIDGE_LOG_PREFIX} activation failed:`, error);
        disposeBridgeServer(bridgeState);
        bridgeState = undefined;
    }
}

function deactivate() {
    disposeBridgeServer(bridgeState);
}

// --- Bridge state ---

function createBridgeState() {
    const workspaceFile = vscode.workspace.workspaceFile && toWindowsPath(vscode.workspace.workspaceFile.fsPath);
    const workspaceRoot = getWorkspaceRoot();

    if (!workspaceFile || !workspaceRoot) {
        return undefined;
    }

    const eideFile = path.join(workspaceRoot, '.eide', 'eide.yml');
    if (!fs.existsSync(eideFile)) {
        return undefined;
    }

    const workspaceHash = hashWorkspacePath(workspaceFile);
    const registrationDir = process.env[REGISTRATION_ENV]
        ? path.resolve(process.env[REGISTRATION_ENV])
        : path.join(os.homedir(), '.vscode', 'eide-rebuild', 'registrations');

    return {
        busy: false,
        ownsServer: false,
        registrationOwned: false,
        registrationDir,
        registrationPath: path.join(registrationDir, `${workspaceHash}.json`),
        pipeName: `eide-cli-${workspaceHash}`,
        pipePath: `\\\\.\\pipe\\eide-cli-${workspaceHash}`,
        server: undefined,
        workspaceFile,
        workspaceKey: normalizePath(workspaceFile),
        workspaceRoot: toWindowsPath(workspaceRoot)
    };
}

function getWorkspaceRoot() {
    const folders = vscode.workspace.workspaceFolders || [];
    return folders.length > 0 ? folders[0].uri.fsPath : undefined;
}

function getLocalAppDataDir() {
    return process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local');
}

function toWindowsPath(inputPath) {
    return path.resolve(inputPath).replace(/\//g, '\\');
}

function normalizePath(inputPath) {
    return toWindowsPath(inputPath).toLowerCase();
}

function hashWorkspacePath(workspacePath) {
    return crypto.createHash('sha256').update(normalizePath(workspacePath)).digest('hex').slice(0, 16);
}

// --- Server lifecycle ---

async function startBridgeServer(state) {
    await fs.promises.mkdir(state.registrationDir, { recursive: true });

    let ownsServer = true;
    state.ownsServer = false;
    state.registrationOwned = false;
    state.server = net.createServer((socket) => {
        socket.setEncoding('utf8');
        attachSocketHandlers(state, socket);
    });

    await new Promise((resolve, reject) => {
        const onError = (error) => {
            state.server.removeListener('error', onError);

            if (error && error.code === 'EADDRINUSE') {
                ownsServer = false;
                resolve();
                return;
            }

            reject(error);
        };

        state.server.once('error', onError);
        state.server.listen(state.pipePath, () => {
            state.server.removeListener('error', onError);
            resolve();
        });
    });

    if (!ownsServer) {
        state.server = undefined;
        return;
    }

    state.ownsServer = true;
    state.registrationOwned = true;
    await writeRegistrationFile(state);
}

function disposeBridgeServer(state) {
    if (!state) {
        return;
    }

    try {
        if (state.server) {
            state.server.close();
        }
    } catch (error) {
        console.warn(`${BRIDGE_LOG_PREFIX} server close warning:`, error);
    }

    try {
        if (state.registrationOwned && state.registrationPath && fs.existsSync(state.registrationPath)) {
            fs.unlinkSync(state.registrationPath);
        }
    } catch (error) {
        console.warn(`${BRIDGE_LOG_PREFIX} registration cleanup warning:`, error);
    } finally {
        state.registrationOwned = false;
        state.ownsServer = false;
    }
}

async function writeRegistrationFile(state) {
    const payload = {
        bridgeVersion: BRIDGE_VERSION,
        pid: process.pid,
        pipeName: state.pipeName,
        updatedAt: new Date().toISOString(),
        workspacePath: state.workspaceFile
    };

    await fs.promises.writeFile(
        state.registrationPath,
        JSON.stringify(payload, null, 2),
        'utf8'
    );
}

// --- Request handling ---

function attachSocketHandlers(state, socket) {
    let buffer = '';

    socket.on('data', (chunk) => {
        buffer += chunk;

        while (true) {
            const newlineIndex = buffer.indexOf('\n');
            if (newlineIndex === -1) {
                break;
            }

            const line = buffer.slice(0, newlineIndex).trim();
            buffer = buffer.slice(newlineIndex + 1);

            if (!line) {
                continue;
            }

            handleRequestLine(state, socket, line).catch((error) => {
                console.error(`${BRIDGE_LOG_PREFIX} request handling failed:`, error);
                sendResponse(socket, {
                    ok: false,
                    errorCode: 'BRIDGE_ERROR',
                    message: error && error.message ? error.message : 'Bridge request failed.'
                });
            });
        }
    });

    socket.on('error', (error) => {
        console.warn(`${BRIDGE_LOG_PREFIX} socket warning:`, error);
    });
}

async function handleRequestLine(state, socket, line) {
    let request;

    try {
        request = JSON.parse(line);
    } catch (error) {
        sendResponse(socket, {
            ok: false,
            errorCode: 'INVALID_REQUEST',
            message: 'Request payload is not valid JSON.'
        });
        return;
    }

    if (request.action !== 'rebuild') {
        sendResponse(socket, {
            requestId: request.requestId || '',
            ok: false,
            errorCode: 'UNSUPPORTED_ACTION',
            message: `Unsupported action: ${request.action || ''}`
        });
        return;
    }

    if (normalizePath(request.workspacePath || '') !== state.workspaceKey) {
        sendResponse(socket, {
            requestId: request.requestId || '',
            ok: false,
            errorCode: 'WRONG_WORKSPACE',
            message: 'Bridge is attached to a different workspace.'
        });
        return;
    }

    if (state.busy) {
        sendResponse(socket, {
            requestId: request.requestId || '',
            ok: false,
            errorCode: 'BUSY',
            message: 'Bridge is already processing a rebuild request.'
        });
        return;
    }

    state.busy = true;
    const startedAt = Date.now();

    try {
        await ensureEideExtension();
        const buildResult = await runRebuildFlow(state);

        sendResponse(socket, {
            requestId: request.requestId || '',
            ok: buildResult.ok,
            target: buildResult.target || '',
            workspacePath: state.workspaceFile,
            logPath: buildResult.logPath || '',
            durationMs: Date.now() - startedAt,
            errorCode: buildResult.errorCode || '',
            message: buildResult.message || ''
        });
    } catch (error) {
        const errorCode = error && error.code ? error.code : 'BRIDGE_ERROR';
        sendResponse(socket, {
            requestId: request.requestId || '',
            ok: false,
            workspacePath: state.workspaceFile,
            logPath: '',
            durationMs: Date.now() - startedAt,
            errorCode,
            message: error && error.message ? error.message : 'Bridge rebuild failed.'
        });
    } finally {
        state.busy = false;
    }
}

function sendResponse(socket, payload) {
    try {
        socket.write(`${JSON.stringify(payload)}\n`);
    } finally {
        socket.end();
    }
}

// --- Rebuild flow ---

async function ensureEideExtension() {
    const extension = vscode.extensions.getExtension('cl.eide');
    if (!extension) {
        const error = new Error('EIDE extension is not installed.');
        error.code = 'EIDE_MISSING';
        throw error;
    }

    if (!extension.isActive) {
        await extension.activate();
    }
}

async function runRebuildFlow(state) {
    const buildRoot = path.join(state.workspaceRoot, 'build');
    const snapshot = takeBuildSnapshot(buildRoot);
    const targetHint = readLegacyModeTarget(state.workspaceRoot);

    await vscode.commands.executeCommand('eide.project.rebuild');

    const completion = await waitForBuildCompletion(buildRoot, snapshot, targetHint);
    const logPath = completion.buildDir ? path.join(completion.buildDir, 'compiler.log') : '';

    if (!logPath || !fs.existsSync(logPath)) {
        return {
            ok: false,
            target: completion.target || '',
            logPath,
            errorCode: 'LOG_MISSING',
            message: 'compiler.log was not generated for the completed rebuild.'
        };
    }

    return {
        ok: completion.ok,
        target: completion.target || '',
        logPath,
        errorCode: completion.ok ? '' : (completion.errorCode || 'BUILD_FAILED'),
        message: completion.message || (completion.ok ? 'rebuild finished' : 'rebuild failed')
    };
}

function takeBuildSnapshot(buildRoot) {
    const snapshot = new Map();
    const directories = listBuildTargetDirectories(buildRoot);

    for (const buildDir of directories) {
        snapshot.set(buildDir, getBuildState(buildDir));
    }

    return snapshot;
}

function getBuildState(buildDir) {
    return {
        compilerLog: statInfo(path.join(buildDir, 'compiler.log')),
        lockFile: statInfo(path.join(buildDir, '.lock')),
        unifyLog: statInfo(path.join(buildDir, 'unify_builder.log'))
    };
}

function createEmptyBuildState() {
    return {
        compilerLog: { mtimeMs: 0, size: 0 },
        lockFile: { mtimeMs: 0, size: 0 },
        unifyLog: { mtimeMs: 0, size: 0 }
    };
}

function listBuildTargetDirectories(buildRoot) {
    if (!fs.existsSync(buildRoot)) {
        return [];
    }

    const entries = fs.readdirSync(buildRoot, { withFileTypes: true });
    return entries
        .filter((entry) => entry.isDirectory())
        .map((entry) => path.join(buildRoot, entry.name));
}

function statInfo(filePath) {
    try {
        const info = fs.statSync(filePath);
        return {
            mtimeMs: info.mtimeMs,
            size: info.size
        };
    } catch (error) {
        return {
            mtimeMs: 0,
            size: 0
        };
    }
}

function didFileChange(previousInfo, currentInfo) {
    return previousInfo.mtimeMs !== currentInfo.mtimeMs || previousInfo.size !== currentInfo.size;
}

function didBuildStateChange(previousState, currentState) {
    return (
        didFileChange(previousState.compilerLog, currentState.compilerLog) ||
        didFileChange(previousState.lockFile, currentState.lockFile) ||
        didFileChange(previousState.unifyLog, currentState.unifyLog)
    );
}

function getCandidateBuildDirs(buildRoot, buildDirs, targetHint) {
    const candidates = [];
    const hintedDir = targetHint ? path.join(buildRoot, targetHint) : '';

    if (hintedDir) {
        candidates.push(hintedDir);
    }

    for (const buildDir of buildDirs) {
        if (buildDir !== hintedDir) {
            candidates.push(buildDir);
        }
    }

    return candidates;
}

function readLegacyModeTarget(workspaceRoot) {
    const eideFile = path.join(workspaceRoot, '.eide', 'eide.yml');
    if (!fs.existsSync(eideFile)) {
        return '';
    }

    try {
        const content = fs.readFileSync(eideFile, 'utf8');
        const match = content.match(/^\s*mode:\s*"?([^"\r\n]+)"?\s*$/m);
        return match ? match[1].trim() : '';
    } catch (error) {
        return '';
    }
}

async function waitForBuildCompletion(buildRoot, snapshot, targetHint) {
    const startDeadline = Date.now() + START_TIMEOUT_MS;
    const finishDeadline = Date.now() + BUILD_TIMEOUT_MS;

    let activeBuildDir;
    let activeTarget = '';
    let previousState;
    let lastActivityAt = 0;
    let sawCompletionSignal = false;

    while (Date.now() < finishDeadline) {
        await delay(POLL_INTERVAL_MS);

        const directories = listBuildTargetDirectories(buildRoot);

        if (!activeBuildDir) {
            const candidates = getCandidateBuildDirs(buildRoot, directories, targetHint);

            for (const buildDir of candidates) {
                const before = snapshot.get(buildDir) || createEmptyBuildState();
                const current = getBuildState(buildDir);

                if (didBuildStateChange(before, current)) {
                    activeBuildDir = buildDir;
                    activeTarget = path.basename(buildDir);
                    previousState = current;
                    lastActivityAt = Date.now();
                    sawCompletionSignal =
                        didFileChange(before.lockFile, current.lockFile) ||
                        didFileChange(before.unifyLog, current.unifyLog);

                    break;
                }
            }

            if (!activeBuildDir && Date.now() > startDeadline) {
                return {
                    ok: false,
                    target: '',
                    buildDir: '',
                    errorCode: 'BUILD_NOT_STARTED',
                    message: 'No build artifacts changed after rebuild was triggered.'
                };
            }

            continue;
        }

        const currentState = getBuildState(activeBuildDir);
        const lockChanged = didFileChange(previousState.lockFile, currentState.lockFile);
        const unifyChanged = didFileChange(previousState.unifyLog, currentState.unifyLog);
        const compilerChanged = didFileChange(previousState.compilerLog, currentState.compilerLog);

        if (lockChanged || unifyChanged || compilerChanged) {
            previousState = currentState;
            lastActivityAt = Date.now();
            sawCompletionSignal = sawCompletionSignal || lockChanged || unifyChanged;
        }

        if (sawCompletionSignal && lastActivityAt && Date.now() - lastActivityAt >= SETTLE_DELAY_MS) {
            const unifyLogPath = path.join(activeBuildDir, 'unify_builder.log');
            const lastRecord = readLastUnifyBuilderRecord(unifyLogPath);
            if (!lastRecord) {
                continue;
            }

            const success = /\[done\]\s*$/i.test(lastRecord);

            return {
                ok: success,
                target: activeTarget,
                buildDir: activeBuildDir,
                errorCode: success ? '' : 'BUILD_FAILED',
                message: success ? 'rebuild finished' : 'rebuild failed'
            };
        }
    }

    return {
        ok: false,
        target: activeTarget,
        buildDir: activeBuildDir || '',
        errorCode: 'BUILD_NOT_STARTED',
        message: 'Build completion signal did not arrive before timeout.'
    };
}

function readLastUnifyBuilderRecord(logPath) {
    if (!fs.existsSync(logPath)) {
        return '';
    }

    const content = fs.readFileSync(logPath, 'utf8');
    const lines = content.split(/\r?\n/).reverse();
    return lines.find((line) => /^\[\d{4}-\d{2}-\d{2} [^\]]+\]/.test(line.trim())) || '';
}

function delay(timeoutMs) {
    return new Promise((resolve) => {
        setTimeout(resolve, timeoutMs);
    });
}

module.exports = {
    activate,
    deactivate
};
