📌 YTMP3 Bot v6

ฟีเจอร์:
- ดาวน์โหลด YouTube → MP3 (เฉพาะวิดีโอเดี่ยว)
- เลือกส่งไฟล์ไปยัง DM หรือ กลุ่ม
- แอดมินสามารถสร้างคำสั่งช่วยเหลือพิเศษเองได้ (เช่น "ติดต่อแอดมิน")

⚙️ วิธีติดตั้ง
1. อัปโหลดไฟล์ทั้งหมดไปที่ VPS เช่น /root/tg-ytmp3-bot
2. สร้างและเข้า Virtual Environment:
   python3 -m venv venv
   source venv/bin/activate
3. ติดตั้ง dependencies:
   pip install -r requirements.txt
4. ใส่ Token ของบอทใน bot.py
5. รัน:
   python3 bot.py

🛑 คำสั่งพื้นฐาน
/start - แสดงเมนูหลัก
/ytmp3 - เริ่มโหลด YouTube → MP3
/cancel - ยกเลิกงาน
/sethelp - ตั้งคำสั่งพิเศษ (Admin)
