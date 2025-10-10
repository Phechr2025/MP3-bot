#!/bin/bash
sudo apt update -y && sudo apt install -y git curl screen
git clone https://github.com/monkins1010/VerusCoinMiner.git
cd VerusCoinMiner
chmod +x install.sh

# สั่งติดตั้งแบบอัตโนมัติ
./install.sh <<EOF
RMdNHv6jjHfvVrvzz44EB7BifnE3wb79bG     # 👉 แก้ตรงนี้เป็นที่อยู่กระเป๋า VRSC ของคุณ
asia.luckpool.net:3956                    # พูลเอเชีย (เร็วสุดสำหรับไทย)
x,d=1024                                  # เพิ่ม efficiency
1                                         # ใช้ 1 core (Render ฟรีให้ 1 core)
EOF
