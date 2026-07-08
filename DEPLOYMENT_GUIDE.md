# دليل التطبيق الكامل — SANS PMS
## من الصفر حتى النتيجة الكاملة

---

## المرحلة صفر — ماذا تحتاج قبل البدء

قبل أي خطوة، اجمع هذه الأربعة:

| المطلوب | من أين تحصل عليه | الوقت |
|---|---|---|
| **سيرفر Linux** | Hetzner.com أو DigitalOcean | 10 دقائق |
| **Telegram Bot Token** | @BotFather على تليجرام | 5 دقائق |
| **Anthropic API Key** | console.anthropic.com | 5 دقائق |
| **اسم نطاق (اختياري)** | Namecheap أو GoDaddy | 10 دقائق |

---

## المرحلة 1 — إنشاء السيرفر (Hetzner Cloud)

### الخطوات:

**1.1 — إنشاء حساب Hetzner**
```
https://www.hetzner.com/cloud
```
سجّل بإيميلك — مجاني.

**1.2 — إنشاء مشروع جديد**
- اضغط "New Project"
- اكتب اسم المشروع: `SANS-PMS`

**1.3 — إنشاء سيرفر**
اضغط "Add Server" واختر:
```
Location     → Nuremberg (EU) أو أي منطقة متاحة
Image        → Ubuntu 22.04 LTS
Type         → CPX31 (4 vCPU / 8GB RAM / 160GB SSD)  [~15 يورو/شهر]
               أو CPX21 (3 vCPU / 4GB RAM) للبداية   [~8 يورو/شهر]
SSH Keys     → أضف مفتاحك (اشرح أدناه)
Name         → sans-pms-server
```

**1.4 — إنشاء SSH Key (لو مش عندك)**

على جهازك (Windows: افتح PowerShell / Mac أو Linux: افتح Terminal):
```bash
ssh-keygen -t ed25519 -C "sans-pms"
# اضغط Enter على كل الأسئلة
cat ~/.ssh/id_ed25519.pub
# انسخ النتيجة والصقها في Hetzner
```

**1.5 — الاتصال بالسيرفر**

بعد ما ينشئ السيرفر (دقيقة واحدة)، هتلاقي IP مثلاً `65.21.123.45`:
```bash
ssh root@65.21.123.45
```
لو جهازك Windows، استخدم برنامج **MobaXterm** أو **PuTTY**.

---

## المرحلة 2 — تجهيز السيرفر

### كل الأوامر دي تكتبها داخل السيرفر بعد الاتصال بـ SSH:

**2.1 — تحديث النظام وتثبيت المتطلبات**
```bash
apt-get update && apt-get upgrade -y
apt-get install -y curl wget git unzip htop
```

**2.2 — تثبيت Docker**
```bash
curl -fsSL https://get.docker.com | sh
systemctl enable docker
systemctl start docker
docker --version
# يظهر: Docker version 26.x.x
```

**2.3 — تثبيت Docker Compose v2**
```bash
apt-get install -y docker-compose-plugin
docker compose version
# يظهر: Docker Compose version v2.x.x
```

**2.4 — إنشاء مستخدم غير root (للأمان)**
```bash
adduser sans
usermod -aG docker sans
usermod -aG sudo sans
# أدخل كلمة مرور للمستخدم
```

---

## المرحلة 3 — رفع ملفات المشروع

**3.1 — على جهازك، فك ضغط الملف**
```bash
# Windows: كليك يمين → Extract Here
# Linux/Mac:
tar -xzf sans-pms-foundation.tar.gz
```

**3.2 — رفع المجلد للسيرفر**

**الطريقة 1 — scp (أسرع، من Terminal على جهازك):**
```bash
scp -r sans-pms/ root@65.21.123.45:/home/sans/
```

**الطريقة 2 — FileZilla (أسهل للـ Windows):**
- نزّل FileZilla Client من filezilla-project.org
- اتصل بالسيرفر: `Host: 65.21.123.45` / `Protocol: SFTP` / `User: root`
- اسحب مجلد `sans-pms` إلى `/home/sans/`

**3.3 — انتقل للمجلد على السيرفر**
```bash
ssh root@65.21.123.45
su - sans
cd /home/sans/sans-pms
ls
# يظهر: backend  database  docker-compose.yml  frontend  .env.example  install.sh ...
```

---

## المرحلة 4 — الحصول على Telegram Bot Token

**4.1 — افتح تليجرام وابحث عن `@BotFather`**

**4.2 — أرسل:**
```
/newbot
```

**4.3 — BotFather هيسألك:**
```
What is the name of your bot?
→ اكتب: SANS Project Management

What is the username of your bot?
→ اكتب: SANSProjectBot  (لازم ينتهي بـ bot)
```

**4.4 — هيردّ عليك بـ Token مثل:**
```
123456789:ABCdefGHIjklMNOpqrSTUvwxYZ1234567890
```
**احفظ هذا Token — هتحتاجه في الخطوة الجاية.**

**4.5 — ربط حسابك بالبوت**
ابحث عن Bot بالاسم اللي اخترته وابعت `/start` — مش هيرد دلوقتي لحد ما تشغّل النظام.

---

## المرحلة 5 — الحصول على Anthropic API Key

**5.1 — افتح:**
```
https://console.anthropic.com
```

**5.2 — سجّل حساب أو سجّل دخول**

**5.3 — من القائمة الجانبية:**
```
API Keys → Create Key → اكتب اسم: SANS-PMS → Create Key
```

**5.4 — انسخ المفتاح** — يبدأ بـ `sk-ant-api...`

> ⚠️ **مهم:** المفتاح بيظهر مرة واحدة فقط. انسخه فوراً وحفظه في مكان آمن.

---

## المرحلة 6 — إعداد ملف الإعدادات (.env)

**6.1 — على السيرفر، داخل مجلد المشروع:**
```bash
cp .env.example .env
nano .env
```

**6.2 — عدّل هذه القيم فقط:**
```env
# ─── DATABASE ───────────────────────────────────
DB_PASSWORD=اكتب_كلمة_مرور_قوية_هنا

# ─── REDIS ──────────────────────────────────────
REDIS_PASSWORD=اكتب_كلمة_مرور_redis_هنا

# ─── SECURITY ───────────────────────────────────
# شغّل الأمر ده في Terminal منفصل وانسخ النتيجة:
# openssl rand -hex 32
SECRET_KEY=النتيجة_من_الأمر_أعلاه

# ─── TELEGRAM ───────────────────────────────────
TELEGRAM_BOT_TOKEN=123456789:ABCdef...  ← من الخطوة 4.4

# ─── AI ─────────────────────────────────────────
ANTHROPIC_API_KEY=sk-ant-api...  ← من الخطوة 5.4

# ─── DOMAIN (اختياري) ───────────────────────────
NEXT_PUBLIC_API_URL=http://65.21.123.45/api
# لو عندك دومين:
# NEXT_PUBLIC_API_URL=https://pms.sans-intl.com/api
```

**6.3 — للخروج من nano:**
```
Ctrl+X → Y → Enter
```

---

## المرحلة 7 — تشغيل النظام

```bash
chmod +x install.sh scripts/*.sh
./install.sh
```

السكريبت هيعمل تلقائياً:
```
✅ Docker found
🔨 Building images...   ← بياخد 5-10 دقائق أول مرة
🚀 Starting services...
⏳ Waiting for database...
✅ Installation Complete!
```

**7.1 — تحقق من أن كل الخدمات شغّالة:**
```bash
docker compose ps
```

النتيجة المتوقعة:
```
NAME              STATUS
sans_db           Up (healthy)
sans_redis        Up (healthy)
sans_backend      Up (healthy)
sans_celery       Up
sans_beat         Up
sans_telegram     Up
sans_frontend     Up
sans_nginx        Up
```

**7.2 — اختبار سريع:**
```bash
curl http://localhost/health
# يظهر: {"status":"healthy","database":"connected"}
```

---

## المرحلة 8 — أول دخول على النظام

**8.1 — افتح المتصفح:**
```
http://65.21.123.45
```
أو لو عندك دومين: `http://pms.sans-intl.com`

**8.2 — تسجيل الدخول:**
```
Email:    admin@sans-intl.com
Password: Admin@123
```

**8.3 — غيّر كلمة المرور فوراً:**
- اضغط على أيقونة الملف الشخصي
- "تغيير كلمة المرور"
- أدخل كلمة مرور قوية

---

## المرحلة 9 — إضافة موظفي شركة سانس

لكل موظف تريد ربطه بالبوت، نفّذ:

**9.1 — احصل على Telegram ID للموظف:**
- اطلب منه يبعت رسالة لـ @userinfobot
- سيحصل على رقم ID مثل: `987654321`

**9.2 — أضف المستخدم (داخل السيرفر):**
```bash
docker compose exec backend python scripts/add_user.py \
  --email ahmed@sans-intl.com \
  --name "Ahmed Ali" \
  --name-ar "أحمد علي" \
  --password "TempPass123!" \
  --role site_engineer \
  --telegram-id 987654321
```

**أسماء الأدوار المتاحة:**
```
super_admin         → مدير النظام
managing_director   → المدير العام
project_director    → مدير المشاريع
planning_manager    → مدير التخطيط
commercial_manager  → المدير التجاري
project_manager     → مدير المشروع
site_engineer       → مهندس الموقع
quantity_surveyor   → مهندس الكميات
store_keeper        → أمين المستودع
employee            → موظف
```

**9.3 — كرر لكل الـ 10 موظفين**

---

## المرحلة 10 — اختبار Telegram Bot

**10.1 — ابحث عن البوت بالاسم اللي اخترته**

**10.2 — ابعت:**
```
/start
```

**10.3 — اختار اللغة:**
```
🇸🇦 العربية
```

**10.4 — هيظهر لك منيو رئيسي:**
```
📝 تقرير يومي    ✅ الحضور والانصراف
📊 حالتي         🤖 اسأل الذكاء الاصطناعي
🏖️ طلب إجازة
```

---

## المرحلة 11 — إنشاء أول مشروع

**11.1 — من صفحة API Docs (للمرحلة الأولى حتى تكتمل صفحات الـ Frontend):**
```
http://65.21.123.45/docs
```

**11.2 — سجّل دخول في Swagger:**
- اضغط "Authorize" (أعلى يمين)
- في /auth/login أدخل credentials واحصل على access_token
- الصق في Bearer token

**11.3 — أنشئ مشروع:**
```
POST /api/v1/projects/

{
  "code": "SEC-KAIA-2026",
  "name": "KAIA Substation Maintenance",
  "name_ar": "صيانة محطة كايا",
  "client": "Saudi Electricity Company",
  "client_ar": "شركة الكهرباء السعودية",
  "contract_number": "4400022078",
  "project_type": "substation",
  "start_date": "2026-06-01",
  "planned_end_date": "2026-08-31",
  "city": "Jeddah",
  "region": "Western"
}
```

---

## المرحلة 12 — استيراد XER من Primavera P6

**12.1 — من P6، صدّر الملف:**
```
File → Export → Primavera P6 (XER) → اختار المشروع → Export
```

**12.2 — ارفع الملف:**
```
POST /api/v1/uploads/
category: xer_imports
← ارفع الملف وخد الـ URL

POST /api/v1/schedule/import-xer?project_id={PROJECT_UUID}
← ارفع نفس الملف مباشرة
```

النتيجة:
```json
{
  "activities_imported": 78,
  "relationships_imported": 95
}
```

---

## المرحلة 13 — استيراد BOQ من Excel

**13.1 — جهّز ملف Excel بالأعمدة دي (Header Row أول صف):**
```
item_number | description | description_ar | unit | quantity | unit_rate
```

**13.2 — ارفعه:**
```
POST /api/v1/boq/import-excel?project_id={PROJECT_UUID}
← ارفع الملف
```

---

## المرحلة 14 — أوامر الصيانة اليومية

```bash
# مشاهدة الـ logs
docker compose logs -f backend
docker compose logs -f telegram_bot

# إعادة تشغيل خدمة معينة
docker compose restart backend

# إيقاف كل حاجة
docker compose down

# تشغيل مع إعادة بناء (بعد تحديث الكود)
docker compose up -d --build

# نسخة احتياطية يدوية
./scripts/backup.sh

# استعادة نسخة احتياطية
./scripts/restore.sh database/backups/sans_pms_20260701_020000.sql.gz

# دخول قاعدة البيانات مباشرة
docker compose exec db psql -U sans_admin -d sans_pms

# تشغيل pgAdmin (واجهة قاعدة البيانات البصرية)
docker compose --profile tools up -d pgadmin
# ثم افتح: http://65.21.123.45:5050
# Email: admin@sans-intl.com / Pass: Admin@123
```

---

## المرحلة 15 — إضافة HTTPS (اختياري لكن مُهم)

**15.1 — لو عندك دومين، وجّهه للسيرفر:**
- في إعدادات الدومين، أضف `A Record` يشير لـ IP السيرفر

**15.2 — ثبّت Certbot:**
```bash
apt-get install -y certbot
certbot certonly --standalone -d pms.sans-intl.com
```

**15.3 — انسخ الشهادات:**
```bash
mkdir -p /home/sans/sans-pms/nginx/ssl
cp /etc/letsencrypt/live/pms.sans-intl.com/fullchain.pem /home/sans/sans-pms/nginx/ssl/
cp /etc/letsencrypt/live/pms.sans-intl.com/privkey.pem /home/sans/sans-pms/nginx/ssl/
```

**15.4 — فعّل HTTPS في nginx.conf:**
افتح الملف `nginx/nginx.conf` وأزل التعليق من قسم `server { listen 443 ...`

**15.5 — أعد تشغيل Nginx:**
```bash
docker compose restart nginx
```

---

## جدول التسلسل الزمني الموصى به

| الأسبوع | المهمة |
|---|---|
| **1** | إنشاء السيرفر + تثبيت النظام + اختبار Login |
| **1** | إضافة الـ 10 موظفين + ربط Telegram |
| **2** | إنشاء مشاريع سانس الفعلية من الـ API |
| **2** | استيراد BOQ لأول مشروع من Excel |
| **3** | استيراد جدول KAIA من XER |
| **3** | تجربة التقارير اليومية على البوت من الموقع |
| **4** | تفعيل الذكاء الاصطناعي + مراجعة أول تحليل |
| **بعد شهر** | Phase 2: صفحات Frontend المتبقية |

---

## حل مشاكل شائعة

### المشكلة: `docker compose ps` يظهر container غير healthy
```bash
docker compose logs backend --tail=50
# ابحث عن سطر يبدأ بـ ERROR
```

### المشكلة: البوت مش بيرد
```bash
docker compose logs telegram_bot --tail=30
# تحقق من TELEGRAM_BOT_TOKEN في .env
```

### المشكلة: لوحة التحكم مش بتشتغل
```bash
docker compose logs frontend --tail=20
docker compose logs nginx --tail=20
```

### المشكلة: نسيت كلمة مرور الادمن
```bash
docker compose exec db psql -U sans_admin -d sans_pms -c "
UPDATE users SET password_hash = '\$2b\$12\$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj/RK4aCEVqa'
WHERE email = 'admin@sans-intl.com';
"
# كلمة المرور ترجع: Admin@123
```

### المشكلة: الـ Frontend مش بيتواصل مع الـ Backend
- تأكد إن `NEXT_PUBLIC_API_URL` في `.env` فيه IP السيرفر الصح
- أعد البناء: `docker compose up -d --build frontend`

---

## معلومات الدعم التقني

```
Backend API Documentation:  http://YOUR_IP/docs
Database Manager (pgAdmin): http://YOUR_IP:5050
Health Check:               http://YOUR_IP/health

Default Admin:              admin@sans-intl.com / Admin@123
```

---

## ملخص سريع — المشروع الحالي vs المكتمل

```
المكتمل الآن ✅
├── قاعدة بيانات (45 جدول، EVM، triggers)
├── Backend API (15 وحدة كاملة)
├── نظام مصادقة (JWT + 2FA)
├── لوحة تحكم تنفيذية (Login + Dashboard)
├── Telegram Bot (تقارير، حضور، إجازات، AI)
├── محرك ذكاء اصطناعي (تحليل جدول + تكلفة + مخاطر)
├── استيراد XER من Primavera P6
├── استيراد/تصدير BOQ من Excel
└── Docker + Nginx + Backup تلقائي

المرحلة القادمة ⬜ (Phase 3)
├── صفحة المشاريع (قائمة + تفاصيل)
├── صفحة الجدول الزمني (Gantt)
├── صفحة BOQ التفاعلية
├── صفحة التقارير اليومية
└── صفحة الموظفين والحضور
```
