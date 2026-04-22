Bu papkadagi raw SQL fayllar tarixiy ma'lumot sifatida qoldirilgan.

Production va yangi deploylar uchun schema boshqaruvining yagona asosiy manbasi:

```bash
alembic upgrade head
```

Ilova `APP_ENV=production` bo'lganda `AUTO_INIT_DB=true` bilan ishga tushmaydi.
Development muhitida `AUTO_INIT_DB=true` faqat lokal qulaylik uchun ishlatiladi.
