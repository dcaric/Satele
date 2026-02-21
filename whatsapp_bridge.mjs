import scriptSelector from '@whiskeysockets/baileys';
const { default: makeWASocket, useMultiFileAuthState, DisconnectReason, downloadContentFromMessage } = scriptSelector;
import { Boom } from '@hapi/boom';
import pino from 'pino';
import axios from 'axios';
import path from 'path';
import { fileURLToPath } from 'url';
import qrcode from 'qrcode-terminal';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const SERVER_URL = "http://localhost:8000/webhook/message";
const ANTIGRAVITY_TRIGGER = process.env.BOT_TRIGGER || "satele";
const AUTH_DIR = path.resolve(__dirname, '.mudslide_cache');
const MEDIA_DIR = path.resolve(__dirname, 'media');

if (!fs.existsSync(MEDIA_DIR)) fs.mkdirSync(MEDIA_DIR);

const logger = pino({ level: 'silent' }); // Silent pino logs to keep terminal clean for QR

async function downloadMedia(message, type, extension = 'bin') {
    const stream = await downloadContentFromMessage(message, type);
    let buffer = Buffer.from([]);
    for await (const chunk of stream) {
        buffer = Buffer.concat([buffer, chunk]);
    }
    const fileName = `${Date.now()}.${extension}`;
    const filePath = path.join(MEDIA_DIR, fileName);
    fs.writeFileSync(filePath, buffer);
    return filePath;
}

// ... (Configuration remains same)

async function startWhatsApp() {
    console.log("🚀 Starting WhatsApp Linked-Device Listener (using Baileys)...");

    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

    const sock = makeWASocket({
        auth: state,
        logger,
        printQRInTerminal: false, // Turned off deprecated
        browser: ["Satele Remote", "Chrome", "1.0.0"]
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
        const { connection, lastDisconnect, qr } = update;

        if (qr) {
            console.log("\n📷 SCAN THIS QR CODE NOW:\n");
            qrcode.generate(qr, { small: true });
        }

        if (connection === 'close') {
            const shouldReconnect = (lastDisconnect.error instanceof Boom) ?
                lastDisconnect.error.output.statusCode !== DisconnectReason.loggedOut : true;

            console.log('❌ Connection closed. Reconnecting:', shouldReconnect);

            if (shouldReconnect) {
                // Prevent aggressive flooding loop
                const delay = 5000; // 5 seconds backoff
                console.log(`⏳ Waiting ${delay}ms before reconnecting...`);
                setTimeout(() => startWhatsApp(), delay);
            }
        } else if (connection === 'open') {
            console.log('✅ WhatsApp connection opened successfully!');
        }
    });

    // ... (rest of the file)

    // Listen for incoming messages
    sock.ev.on('messages.upsert', async m => {
        const { messages, type } = m;
        console.log(`📥 Received message event: ${type} (${messages.length} messages)`);

        for (const msg of messages) {
            let text = msg.message?.conversation ||
                msg.message?.extendedTextMessage?.text ||
                msg.message?.imageMessage?.caption ||
                msg.message?.documentMessage?.caption;

            const isAudio = !!msg.message?.audioMessage;
            const isImage = !!msg.message?.imageMessage;
            const isDocument = !!msg.message?.documentMessage;

            const fromMe = msg.key.fromMe;
            const sender = msg.key.remoteJid;
            const targetSender = fromMe ? sock.user.id.split(':')[0] + '@s.whatsapp.net' : sender;

            // --- WHITELIST CHECK ---
            // Allow self (fromMe) by default.
            // Check ALLOWED_NUMBERS env for others.
            const allowedList = (process.env.ALLOWED_NUMBERS || "").split(',').map(n => n.trim()).filter(n => n);
            const senderId = sender.split('@')[0].split(':')[0]; // Remove suffix and connection ID

            const isAllowed = fromMe || allowedList.includes(senderId);

            if (!isAllowed) {
                console.log(`🚫 START_IGNORE: Blocked message from unauthorized sender: ${sender}`);
                continue;
            }
            // -----------------------

            let mediaPath = null;

            if (isAudio && msg.message.audioMessage.ptt) {
                console.log("🎙️ Received Voice Note!");
                try {
                    mediaPath = await downloadMedia(msg.message.audioMessage, 'audio', 'ogg');
                    console.log(`✅ Saved voice note to ${mediaPath}`);
                    // For voice notes, we treat them as if they have the trigger implicitly 
                    // or we check if user said anything in text. Since it's PTT, we 
                    // usually just process it.
                    text = (text || "") + " [VOICE]";
                } catch (e) {
                    console.error("❌ Failed to download audio:", e.message);
                }
            } else if (isImage) {
                console.log("🖼️ Received Image!");
                try {
                    mediaPath = await downloadMedia(msg.message.imageMessage, 'image', 'jpg');
                    console.log(`✅ Saved image to ${mediaPath}`);
                    text = (text || "") + " [IMAGE]";
                } catch (e) {
                    console.error("❌ Failed to download image:", e.message);
                }
            } else if (isDocument) {
                console.log("📄 Received Document!");
                try {
                    const ext = path.extname(msg.message.documentMessage.fileName || "").replace('.', '') || 'bin';
                    mediaPath = await downloadMedia(msg.message.documentMessage, 'document', ext);
                    console.log(`✅ Saved document to ${mediaPath}`);
                    text = (text || "") + " [FILE: " + (msg.message.documentMessage.fileName || "unknown") + "]";
                } catch (e) {
                    console.error("❌ Failed to download document:", e.message);
                }
            }

            if (text) {
                console.log(`💬 Message from ${fromMe ? 'ME' : sender}: "${text}"`);

                // 1. Prevent Loops: Ignore messages that are likely bot outputs
                if (text.startsWith("🤖") || text.includes("[Bot]") ||
                    text.startsWith("✅") || text.startsWith("❌") || text.startsWith("🎙️")) {
                    console.log("🚫 Ignoring bot output message.");
                    return;
                }

                // 2. Trigger Check (using regex for word boundary to avoid "antigravity" matching "gravity")
                const triggerRegex = new RegExp(`\\b${ANTIGRAVITY_TRIGGER}\\b`, 'i');
                const isTriggered = triggerRegex.test(text) || (isAudio && mediaPath);

                if (isTriggered) {
                    console.log(`🎯 Trigger matched!`);

                    try {
                        await axios.post(SERVER_URL, {
                            text: text,
                            sender: targetSender,
                            source: 'whatsapp',
                            fromMe: fromMe,
                            mediaPath: mediaPath
                        });
                        console.log("✅ Forwarded to Antigravity server.");

                        // 3. Updated Acknowledgment (Avoid using the trigger word itself?)
                        // Actually, users want to know which bot replied (M3 vs Satele)
                        // But we capitalize it for niceness
                        const botName = ANTIGRAVITY_TRIGGER.charAt(0).toUpperCase() + ANTIGRAVITY_TRIGGER.slice(1);
                        const ackText = isAudio ? `🎙️ [${botName}] Listening...` : `🤖 [${botName}] Working...`;
                        await sock.sendMessage(targetSender, { text: ackText });
                    } catch (err) {
                        console.error("❌ Bridge Error:", err.message);
                    }
                }
            }
        }
    });

    // Handle credentials save
    sock.ev.on('creds.update', saveCreds);

    // Keep track of the socket to allow sending messages from the API
    global.whatsappSock = sock;
    global.whatsappSockUser = sock.user;
}

// REST server to allow Python/FastAPI to send WhatsApp messages back
import express from 'express';
const expressApp = express();
expressApp.use(express.json());

expressApp.post('/send', async (req, res) => {
    const { to, text } = req.body;
    console.log(`📤 Outgoing message to ${to}: ${text.substring(0, 50)}...`);
    if (global.whatsappSock && to && text) {
        try {
            await global.whatsappSock.sendMessage(to, { text: text });
            console.log("✅ Message sent successfully.");
            return res.json({ status: 'sent' });
        } catch (e) {
            console.error("❌ Failed to send message:", e.message);
            return res.status(500).json({ error: e.message });
        }
    }
    console.warn("⚠️ WhatsApp not connected or missing params");
    res.status(500).json({ error: 'WhatsApp not connected or missing params' });
});

expressApp.post('/send-media', async (req, res) => {
    const { to, filePath, caption } = req.body;
    console.log(`📤 Outgoing media to ${to}: ${filePath}`);

    if (!fs.existsSync(filePath)) {
        return res.status(404).json({ error: "File not found on server" });
    }

    if (global.whatsappSock && to) {
        try {
            // Determine mimetype (basic)
            const ext = path.extname(filePath).toLowerCase();
            let mimetype = 'application/octet-stream';
            if (['.jpg', '.jpeg', '.png'].includes(ext)) mimetype = 'image/jpeg';
            if (['.mp4'].includes(ext)) mimetype = 'video/mp4';
            if (['.pdf'].includes(ext)) mimetype = 'application/pdf';

            await global.whatsappSock.sendMessage(to, {
                document: { url: filePath },
                mimetype: mimetype,
                fileName: path.basename(filePath),
                caption: caption || ""
            });

            console.log("✅ Media sent successfully.");
            return res.json({ status: 'sent' });
        } catch (e) {
            console.error("❌ Failed to send media:", e.message);
            return res.status(500).json({ error: e.message });
        }
    }
    res.status(500).json({ error: 'WhatsApp not connected' });
});

expressApp.listen(8001, () => console.log("📡 WhatsApp Send-API listening on 8001"));

startWhatsApp().catch(err => console.error("Critical Error:", err));
