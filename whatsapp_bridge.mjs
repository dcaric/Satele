import makeWASocket, { useMultiFileAuthState, DisconnectReason, downloadContentFromMessage } from '@whiskeysockets/baileys';
import { Boom } from '@hapi/boom';
import pino from 'pino';
import axios from 'axios';
import path from 'path';
import qrcode from 'qrcode-terminal';
import fs from 'fs';
import express from 'express';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Configuration
const SERVER_URL = "http://localhost:8000/webhook/message";
const ANTIGRAVITY_TRIGGER = process.env.BOT_TRIGGER || "satele";
const AUTH_DIR = path.resolve(__dirname, '.mudslide_cache');
const MEDIA_DIR = path.resolve(__dirname, 'media');

if (!fs.existsSync(MEDIA_DIR)) fs.mkdirSync(MEDIA_DIR);

const logger = pino({ level: 'silent' });

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

async function startWhatsApp() {
    console.log("🚀 Starting WhatsApp Linked-Device Listener (using Baileys ESM)...");

    const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);

    const sock = makeWASocket.default({
        auth: state,
        logger,
        printQRInTerminal: false,
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
                setTimeout(() => startWhatsApp(), 5000);
            }
        } else if (connection === 'open') {
            console.log('✅ WhatsApp connection opened successfully!');
        }
    });

    sock.ev.on('messages.upsert', async m => {
        const { messages } = m;
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

            const allowedList = (process.env.ALLOWED_NUMBERS || "").split(',').map(n => n.trim()).filter(n => n);
            const senderId = sender.split('@')[0].split(':')[0];
            const isAllowed = fromMe || allowedList.includes(senderId);

            if (!isAllowed) continue;

            let mediaPath = null;
            if (isAudio && msg.message.audioMessage.ptt) {
                try {
                    mediaPath = await downloadMedia(msg.message.audioMessage, 'audio', 'ogg');
                    text = (text || "") + " [VOICE]";
                } catch (e) { }
            } else if (isImage) {
                try {
                    mediaPath = await downloadMedia(msg.message.imageMessage, 'image', 'jpg');
                    text = (text || "") + " [IMAGE]";
                } catch (e) { }
            } else if (isDocument) {
                try {
                    const ext = path.extname(msg.message.documentMessage.fileName || "").replace('.', '') || 'bin';
                    mediaPath = await downloadMedia(msg.message.documentMessage, 'document', ext);
                    text = (text || "") + " [FILE: " + (msg.message.documentMessage.fileName || "unknown") + "]";
                } catch (e) { }
            }

            if (text) {
                if (text.startsWith("🤖") || text.includes("[Bot]") || text.startsWith("✅") || text.startsWith("❌") || text.startsWith("🎙️")) return;

                const triggerRegex = new RegExp(`\\b${ANTIGRAVITY_TRIGGER}\\b`, 'i');
                if (triggerRegex.test(text) || (isAudio && mediaPath)) {
                    try {
                        await axios.post(SERVER_URL, {
                            text: text,
                            sender: targetSender,
                            source: 'whatsapp',
                            fromMe: fromMe,
                            mediaPath: mediaPath
                        });
                        const botName = ANTIGRAVITY_TRIGGER.charAt(0).toUpperCase() + ANTIGRAVITY_TRIGGER.slice(1);
                        const ackText = isAudio ? `🎙️ [${botName}] Listening...` : `🤖 [${botName}] Working...`;
                        await sock.sendMessage(targetSender, { text: ackText });
                    } catch (err) { }
                }
            }
        }
    });

    global.whatsappSock = sock;
}

const expressApp = express();
expressApp.use(express.json());

expressApp.post('/send', async (req, res) => {
    const { to, text } = req.body;
    if (global.whatsappSock && to && text) {
        try {
            await global.whatsappSock.sendMessage(to, { text: text });
            return res.json({ status: 'sent' });
        } catch (e) {
            return res.status(500).json({ error: e.message });
        }
    }
    res.status(500).json({ error: 'WhatsApp not connected' });
});

expressApp.listen(8001, () => console.log("📡 WhatsApp Send-API listening on 8001"));
startWhatsApp().catch(err => console.error("Critical Error:", err));
