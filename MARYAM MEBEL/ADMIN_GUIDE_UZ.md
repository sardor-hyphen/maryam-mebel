# MARYAM MEBEL ADMIN QO'LLANMASI

Ushbu qo'llanma MARYAM MEBEL veb-sayti va Telegram botini boshqarish uchun mo'ljallangan. Qo'llanma ikkita qismdan iborat: veb-sayt administratori va Telegram bot administratori.

## 1. VEB-SAYT ADMINISTRATORI UCHUN QO'LLANMA

### 1.1 Kirish

Veb-sayt admin paneliga kirish uchun quyidagi URL manziliga o'ting:
```
https://maryammebel.uz/admin
```

Kirish ma'lumotlari (standart):
- **Foydalanuvchi nomi:** admin
- **Parol:** maryam2025

### 1.2 Boshqaruv paneli

Admin panelga kirgandan so'ng siz quyidagi bo'limlarni ko'rasiz:

1. **Statistika** - Mahsulotlar, xabarlar va o'qilmagan xabarlar soni
2. **Mahsulotlar ro'yxati** - Barcha mahsulotlar jadvali
3. **Xabarlar** - Foydalanuvchilardan kelgan xabarlar

### 1.3 Mahsulotlarni boshqarish

#### Yangi mahsulot qo'shish

1. Boshqaruv panelida "Yangi mahsulot qo'shish" tugmasini bosing
2. Quyidagi maydonlarni to'ldiring:
   - **Nomi** - Mahsulot nomi
   - **Slug** - URL uchun kalit so'z (avtomatik yaratiladi)
   - **Tavsif** - Mahsulot tavsifi
   - **Kategoriya** - Mahsulot kategoriyasi
   - **Material** - Ishlatilgan materiallar
   - **Yili** - Ishlab chiqarilgan yili
   - **Kafolat** - Kafolat muddati
   - **Tarkibi** - Mahsulot tarkibi
   - **Narx** - Mahsulot narxi
   - **Chegirma** - Chegirma foizi
   - **Faol** - Mahsulotni saytda ko'rsatish uchun belgilang
   - **Asosiy rasm** - Mahsulotning asosiy rasmi
   - **Galereya rasmlari** - Qo'shimcha rasmlar

3. "Saqlash" tugmasini bosing

#### Mavjud mahsulotni tahrirlash

1. Mahsulotlar jadvalida tahrirlamoqchi bo'lgan mahsulot uchun "Tahrirlash" tugmasini bosing
2. Kerakli o'zgarishlarni kiriting
3. "Saqlash" tugmasini bosing

#### Mahsulotni o'chirish

1. Mahsulotlar jadvalida o'chirmoqchi bo'lgan mahsulot uchun "O'chirish" tugmasini bosing
2. Tasdiqlash so'rovi paydo bo'ladi, "Tasdiqlash" tugmasini bosing

### 1.4 Buyurtmalarni boshqarish

Buyurtmalar Telegram boti orqali keladi va admin panelning "Buyurtmalar" bo'limida ko'rinadi.

1. "Buyurtmalar" menyusini tanlang
2. Jadvalda barcha buyurtmalarni ko'rasiz:
   - Buyurtma raqami
   - Yaratilgan sanasi
   - Holati
   - Xaridor ma'lumotlari

### 1.5 Xabarlarni boshqarish

Foydalanuvchilardan kelgan xabarlar "Boshqaruv paneli"ning "Xabarlar" bo'limida ko'rinadi.

1. Xabarlar jadvalida "Ko'rish" tugmasi orqali xabarni oching
2. Xabarni o'qilgan deb belgilash uchun "O'qilgan" tugmasini bosing

## 2. TELEGRAM BOT ADMINISTRATORI UCHUN QO'LLANMA

### 2.1 Botga kirish

Telegram botiga kirish uchun @MaryamMebelBot ni qidiring yoki quyidagi havoladan foydalaning:
```
https://t.me/maryam_mebel_supportbot
```

### 2.2 Admin buyruqlari

Botda maxsus admin buyruqlari mavjud:

1. **/panel** - Admin panelini ochadi
2. **/start** - Bosh menyuni ko'rsatadi

### 2.3 Admin paneli

#### Panelga kirish

1. Telegramda @MaryamMebelBot ni oching
2. `/panel` buyrug'ini yuboring
3. Ochiq murojaatlar ro'yxatini ko'rasiz

#### Murojaatlarni boshqarish

Admin panelida quyidagi amallarni bajarishingiz mumkin:

1. **Murojaatni ko'rish** - Murojaat raqamini tanlab, murojaat tafsilotlarini ko'ring
2. **Murojaatni qabul qilish** - "✅ Javob berishni boshlash" tugmasini bosib, murojaatni qabul qiling
3. **Javob yuborish** - Qabul qilingan murojaatga javob berish uchun xabarni "Reply" tugmasi orqali yuboring

#### Mavzular bo'yicha murojaatlar

Bot quyidagi mavzular bo'yicha murojaatlarni qo'llab-quvvatlaydi:
- 📦 Buyurtma holati
- ⚙️ Texnik yordam
- 🤝 Hamkorlik
- 💡 Taklif va shikoyat

### 2.4 Buyurtma boshqarish

Buyurtmalar "📦 Buyurtma holati" mavzusi ostida keladi. Ushbu buyurtmalarni quyidagicha boshqaring:

1. Admin panelida buyurtmani tanlang
2. "✅ Javob berishni boshlash" tugmasini bosing
3. Buyurtma holati to'g'risida xabar yuboring

### 2.5 Foydalanuvchi profili

Har bir foydalanuvchi profili quyidagi ma'lumotlarni o'z ichiga oladi:
- Foydalanuvchi ismi
- Murojaatlar soni
- Oxirgi murojaat sanasi
- Status (VIP yoki oddiy)
- Eslatmalar (agar mavjud bo'lsa)

### 2.6 Statistika

Bot quyidagi statistik ma'lumotlarni taqdim etadi:
- Javob kutayotgan murojaatlar soni
- Har bir mavzu bo'yicha murojaatlar
- Foydalanuvchilar soni

## 3. SOZLAMALAR

### 3.1 .env fayli

Bot va veb-sayt quyidagi sozlamalarni talab qiladi:

```
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=your_admin_telegram_id
EMPLOYER_ID=employer_telegram_id
TELEGRAM_CHANNELS=@channel1,@channel2
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_admin_password
SECRET_KEY=your_secret_key
```

### 3.2 Admin identifikatorlari

Bot faqat ro'yxatdan o'tgan adminlar uchun ishlaydi. Adminlar Telegram ID raqamlari quyidagicha belgilanadi:
```
ADMIN_IDS=123456789,987654321
```

## 4. MUAYYAN VAZIYATLARDA HARAKATLAR

### 4.1 Yangi admin qo'shish

Yangi admin qo'shish uchun .env faylida ADMIN_IDS qatoriga yangi admin Telegram ID raqamini qo'shing va botni qayta ishga tushiring.

### 4.2 Kanalga a'zo bo'lmaslik

Foydalanuvchilar murojaat yuborishdan oldin belgilangan kanallarga a'zo bo'lishi kerak. Kanallar ro'yxatini .env faylida TELEGRAM_CHANNELS qatorida belgilang.

### 4.3 Xatoliklarni bartaraf etish

Agar bot xato ishlayotgan bo'lsa:
1. Loglarni tekshiring
2. Barcha kerakli kutubxonalar o'rnatilganligini tekshiring
3. .env faylidagi sozlamalarni tekshiring
4. Ma'lumotlar bazasi faylini tekshiring

## 5. TEXNIK QO'LLAB-QUVVATLASH

### 5.1 Talablarni o'rnatish

Kerakli kutubxonalar:
```bash
pip install -r requirements.txt
```

### 5.2 Botni ishga tushirish

Botni polling rejimida ishga tushirish:
```bash
python bot.py
```

Webhook rejimida ishga tushirish:
```bash
python app.py webhook
```

### 5.3 Webhookni o'chirish

Webhookni o'chirish uchun:
```bash
python app.py remove-webhook
```

---

**Eslatma:** Ushbu qo'llanma MARYAM MEBEL tizimi uchun mo'ljallangan. Har qanday o'zgarishlar tizim funksiyalarini ta'sirlashi mumkin. O'zgarishlar kiritishdan oldin zaxira nusxasini oling.