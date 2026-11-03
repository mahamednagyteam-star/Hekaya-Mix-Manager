# Hekaya Mix Manager Android

واجهة Android بلمس كاملة حول منطق `mix_v3.py` الأصلي. الواجهة توفر:

- إدخال الإيميل وكلمة المرور أو JWT وCookie.
- إدخال بيانات حساب الفرد والرصيد المستهدف.
- سجل حي للرسائل والتقدم.
- أزرار الإيقاف المؤقت والاستئناف.
- خانة إدخال إضافية لاختيارات الأرقام أو أي prompt يظهر أثناء التشغيل.

## البناء

يتطلب البناء بيئة Linux مع Java وAndroid SDK/NDK وBuildozer:

```bash
python3 -m pip install buildozer
cd android_app
buildozer -v android debug
```

الناتج يكون داخل `bin/`.

> يجب بناء APK على Android/Linux أو عبر CI. لا تضع ملفات التقدم أو بيانات الحسابات داخل المستودع.
