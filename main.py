
import os
import base64
import json
import uuid as uuidlib
from dataclasses import dataclass
from typing import Optional, Dict, Any, Tuple

import httpx
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputFile
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

VERIFY_TLS = os.getenv("VERIFY_TLS", "true").lower() == "true"
DEFAULT_EXPIRE_DAYS = int(os.getenv("DEFAULT_EXPIRE_DAYS", "0"))
DEFAULT_TOTAL_GB = int(os.getenv("DEFAULT_TOTAL_GB", "0"))

# ---------- Config for two "profiles" (AIS / TRUE) ----------
from dataclasses import dataclass

@dataclass
class PanelProfile:
    name: str
    base: str
    username: str
    password: str
    inbound_id: int
    public_host: str

def env_profile(prefix: str, name: str) -> PanelProfile:
    return PanelProfile(
        name=name,
        base=os.getenv(f"{prefix}_PANEL_BASE", "").rstrip("/"),
        username=os.getenv(f"{prefix}_USERNAME", ""),
        password=os.getenv(f"{prefix}_PASSWORD", ""),
        inbound_id=int(os.getenv(f"{prefix}_INBOUND_ID", "0")),
        public_host=os.getenv(f"{prefix}_PUBLIC_HOST", ""),
    )

PROFILES = {
    "AIS": env_profile("AIS", "AIS"),
    "TRUE": env_profile("TRUE", "TRUE")
}

# --------- 3x-ui API client (handles multiple endpoint styles) ----------
class XUIError(Exception):
    pass

class XUI:
    def __init__(self, base: str, username: str, password: str, verify: bool = True):
        self.base = base.rstrip("/")
        self.username = username
        self.password = password
        self.verify = verify
        self.cookies = {}

    async def _login(self, client: httpx.AsyncClient) -> None:
        paths = ["/login", "/xui/login"]
        for p in paths:
            try:
                resp = await client.post(
                    self.base + p,
                    data={"username": self.username, "password": self.password},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=20,
                )
                if resp.status_code in (200, 302):
                    self.cookies.update(resp.cookies)
                    return
            except Exception:
                continue
        raise XUIError("Login failed — check base URL/username/password and enable API.")

    async def _request(self, method: str, path: str, client: httpx.AsyncClient, **kwargs):
        url = self.base + path
        resp = await client.request(method, url, cookies=self.cookies, timeout=25, **kwargs)
        return resp

    async def ensure_login(self, client: httpx.AsyncClient):
        if not self.cookies:
            await self._login(client)

    async def get_inbound(self, client: httpx.AsyncClient, inbound_id: int) -> Dict[str, Any]:
        await self.ensure_login(client)
        candidates = [
            ("GET", f"/panel/api/inbounds/get/{inbound_id}" ),
            ("GET", f"/panel/api/inbounds/get?id={inbound_id}" ),
            ("GET", f"/xui/inbound/get/{inbound_id}" ),
            ("POST", "/panel/api/inbounds/get" ),
            ("POST", "/xui/inbound/get" ),
        ]
        for method, path in candidates:
            try:
                json_body = None
                if path.endswith("/get") and method == "POST":
                    json_body = {"id": inbound_id}
                resp = await self._request(method, path, client, json=json_body)
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict) and data.get("success") is True and "obj" in data:
                        return data["obj"]
                    if isinstance(data, dict) and "obj" in data:
                        return data["obj"]
                    if isinstance(data, dict) and data.get("id") == inbound_id:
                        return data
            except Exception:
                continue
        raise XUIError("Cannot fetch inbound info. Check inbound ID or API path.")

    async def add_client(
        self,
        client: httpx.AsyncClient,
        inbound_id: int,
        email: str,
        uuid: str,
        total_gb: int = 0,
        expire_days: int = 0,
        enable: bool = True,
        flow: str = "",
    ) -> Dict[str, Any]:
        await self.ensure_login(client)

        payload_variants = [
            {
                "path": "/panel/api/inbounds/addClient",
                "json": {
                    "id": inbound_id,
                    "clients": [{
                        "id": uuid,
                        "email": email,
                        "flow": flow,
                        "limitIp": 0,
                        "totalGB": total_gb * 1024**3 if total_gb else 0,
                        "expiryTime": 0 if not expire_days else 0,
                        "enable": enable
                    }]
                }
            },
            {
                "path": "/panel/api/inbounds/addClient",
                "json": {
                    "id": inbound_id,
                    "settings": [{
                        "id": uuid,
                        "email": email,
                        "flow": flow,
                        "limitIp": 0,
                        "totalGB": total_gb * 1024**3 if total_gb else 0,
                        "expiryTime": 0 if not expire_days else 0,
                        "enable": enable
                    }]
                }
            },
            {
                "path": "/xui/inbound/addClient",
                "json": {
                    "id": inbound_id,
                    "email": email,
                    "enable": enable,
                    "uuid": uuid,
                    "flow": flow,
                    "limitIp": 0,
                    "totalGB": total_gb * 1024**3 if total_gb else 0,
                    "expiryTime": 0 if not expire_days else 0,
                    "tgId": "",
                    "subId": ""
                }
            },
        ]

        for variant in payload_variants:
            try:
                resp = await self._request("POST", variant["path"], client, json=variant["json"])
                if resp.status_code == 200:
                    data = resp.json()
                    if isinstance(data, dict) and (data.get("success") in (True, 1, "true", None)):
                        return data
            except Exception:
                continue
        raise XUIError("Add client failed on all known endpoints.")

# ---------- Helpers to build vmess link ----------
def build_vmess_link(
    inbound: Dict[str, Any],
    public_host: str,
    client_uuid: str,
    remark: str
):
    port = inbound.get("port")
    stream = inbound.get("streamSettings", {}) or inbound.get("stream", {})
    network = stream.get("network", "tcp")
    security = stream.get("security", "")
    tls = "tls" if security == "tls" else ""
    sni = ""
    host_header = ""
    path = ""

    if network == "ws":
        ws = (stream.get("wsSettings") or {}).get("headers") or {}
        host_header = ws.get("Host", ws.get("host", ""))
        path = (stream.get("wsSettings") or {}).get("path", "")
    elif network == "grpc":
        grpcset = stream.get("grpcSettings") or {}
        path = grpcset.get("serviceName", "")
    elif network == "tcp":
        pass

    if security == "tls":
        tls_settings = stream.get("tlsSettings") or stream.get("realitySettings") or {}
        sni = (tls_settings.get("serverName")
               or (tls_settings.get("alpn")[0] if isinstance(tls_settings.get("alpn"), list) and tls_settings["alpn"] else "")
               or public_host)

    vmess_json = {
        "v": "2",
        "ps": remark,
        "add": public_host,
        "port": str(port),
        "id": client_uuid,
        "aid": "0",
        "net": network,
        "type": "none",
        "host": host_header or public_host,
        "path": path or "/",
        "tls": tls,
        "sni": sni
    }
    link = "vmess://" + base64.urlsafe_b64encode(json.dumps(vmess_json, separators=(",", ":")).encode()).decode().strip("=")
    return link, vmess_json

# ---------- Telegram Bot flows ----------
CHOOSE_NET, ASK_FILENAME = range(2)

def kb_main():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ สร้าง VMESS (AIS)", callback_data="make_AIS")],
        [InlineKeyboardButton("➕ สร้าง VMESS (TRUE)", callback_data="make_TRUE")],
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "เลือกเครือข่ายที่ต้องการสร้าง vmess ครับ 👇", reply_markup=kb_main()
    )
    return CHOOSE_NET

async def choose_net(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, sel = query.data.split("_", 1)
    context.user_data["profile"] = sel
    await query.edit_message_text(
        f"พิมพ์ **ชื่อไฟล์/ชื่อโปรไฟล์** ที่ต้องการตั้ง (เช่น `Bio_Shop-TH-{sel}-User01`)\n"
        "ชื่อที่ตั้งนี้จะใช้เป็น Remark และชื่อไฟล์ `.txt` ที่ส่งกลับให้คุณ"
    )
    return ASK_FILENAME

async def receive_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    filename = update.message.text.strip()
    profile_key = context.user_data.get("profile")
    if not profile_key or profile_key not in PROFILES:
        await update.message.reply_text("โปรดลอง /start ใหม่อีกครั้ง")
        return ConversationHandler.END

    profile = PROFILES[profile_key]
    if not all([profile.base, profile.username, profile.password, profile.inbound_id, profile.public_host]):
        await update.message.reply_text("ค่า ENV ของโปรไฟล์นี้ยังไม่ครบ ตรวจสอบอีกครั้งครับ")
        return ConversationHandler.END

    await update.message.reply_text("กำลังสร้างผู้ใช้บน 3x-ui… รอสักครู่")

    async with httpx.AsyncClient(verify=VERIFY_TLS) as httpc:
        xui = XUI(base=profile.base, username=profile.username, password=profile.password, verify=VERIFY_TLS)
        try:
            inbound = await xui.get_inbound(httpc, profile.inbound_id)
            client_uuid = str(uuidlib.uuid4())
            await xui.add_client(
                httpc,
                inbound_id=profile.inbound_id,
                email=filename,
                uuid=client_uuid,
                total_gb=DEFAULT_TOTAL_GB,
                expire_days=DEFAULT_EXPIRE_DAYS,
                enable=True,
                flow=""
            )

            vmess_link, vmess_json = build_vmess_link(
                inbound=inbound,
                public_host=profile.public_host,
                client_uuid=client_uuid,
                remark=filename
            )

            text = (
                f"✅ สร้างเสร็จในหมวด *{profile_key}*\n"
                f"• Remark/ชื่อไฟล์: `{filename}`\n"
                f"• UUID: `{client_uuid}`\n"
                f"• Host: `{profile.public_host}`\n"
                f"• Port: `{inbound.get('port')}`\n"
                f"• Network: `{(inbound.get('streamSettings') or {}).get('network', 'tcp')}`\n\n"
                f"**vmess link:**\n`{vmess_link}`"
            )
            await update.message.reply_text(text, disable_web_page_preview=True)

            content = [
                f"# {filename}",
                "",
                "## VMESS",
                vmess_link,
                "",
                "## JSON (สำหรับ import บางแอป)",
                json.dumps(vmess_json, indent=2, ensure_ascii=False)
            ]
            b = "\n".join(content).encode()
            await update.message.reply_document(
                document=InputFile(bytes(b), filename=f"{filename}.txt"),
                caption="ไฟล์คอนฟิก (.txt)"
            )

        except XUIError as e:
            await update.message.reply_text(
                "❌ สร้างไม่สำเร็จ: " + str(e) +
                "\n• ตรวจสอบว่าเปิด API ใน 3x-ui แล้วหรือยัง\n"
                "• เช็ค URL ผู้ดูแล, Username/Password, และ Inbound ID\n"
                "• ถ้าใบรับรอง TLS ไม่ถูกต้อง ให้ตั้ง VERIFY_TLS=false"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ ผิดพลาดไม่คาดคิด: {e}")

    await update.message.reply_text("ต้องการสร้างเพิ่มเลือกจากเมนูครับ 👇", reply_markup=kb_main())
    return CHOOSE_NET

async def menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await choose_net(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ยกเลิกแล้ว พิมพ์ /start เพื่อเริ่มใหม่")
    return ConversationHandler.END

def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN is empty. Put it in environment variables.")
    app = Application.builder().token(BOT_TOKEN).build()

    flow = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSE_NET: [CallbackQueryHandler(menu_click, pattern=r"^make_")],
            ASK_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_filename)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )
    app.add_handler(flow)
    app.add_handler(CommandHandler("menu", start))
    app.run_polling()

if __name__ == "__main__":
    main()
