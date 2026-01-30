# 📧 CONFIGURACIÓN DE PROVEEDORES DE CORREO

Esta guía te ayuda a configurar diferentes servicios de correo electrónico con el BOE Monitor.

---

## 📮 Gmail

### Requisitos previos:
1. Activar verificación en 2 pasos
2. Generar contraseña de aplicación: https://myaccount.google.com/apppasswords

### Configuración en config.json:
```json
{
  "recipient_email": "tu_email@gmail.com",
  "smtp_config": {
    "server": "smtp.gmail.com",
    "port": 587,
    "username": "tu_email@gmail.com",
    "password": "xxxx xxxx xxxx xxxx"
  }
}
```

**⚠️ IMPORTANTE**: La contraseña debe ser de aplicación (16 caracteres), NO tu contraseña normal.

---

## 📮 Outlook / Hotmail / Live.com

### Configuración en config.json:
```json
{
  "recipient_email": "tu_email@outlook.com",
  "smtp_config": {
    "server": "smtp-mail.outlook.com",
    "port": 587,
    "username": "tu_email@outlook.com",
    "password": "tu_contraseña"
  }
}
```

### Si tienes verificación en 2 pasos:
- Genera una contraseña de aplicación en: https://account.live.com/proofs/AppPassword

---

## 📮 Yahoo Mail

### Requisitos previos:
1. Activar "Permitir apps menos seguras" o generar contraseña de aplicación
2. Generar contraseña: https://login.yahoo.com/account/security

### Configuración en config.json:
```json
{
  "recipient_email": "tu_email@yahoo.com",
  "smtp_config": {
    "server": "smtp.mail.yahoo.com",
    "port": 587,
    "username": "tu_email@yahoo.com",
    "password": "contraseña_de_aplicacion"
  }
}
```

---

## 📮 iCloud Mail

### Requisitos previos:
1. Generar contraseña específica de app en: https://appleid.apple.com
2. Ir a "Seguridad" → "Contraseñas de apps"

### Configuración en config.json:
```json
{
  "recipient_email": "tu_email@icloud.com",
  "smtp_config": {
    "server": "smtp.mail.me.com",
    "port": 587,
    "username": "tu_email@icloud.com",
    "password": "xxxx-xxxx-xxxx-xxxx"
  }
}
```

---

## 📮 Servidor SMTP Propio / Empresarial

Si tu empresa u organización tiene su propio servidor de correo:

### Configuración en config.json:
```json
{
  "recipient_email": "tu_email@tuempresa.com",
  "smtp_config": {
    "server": "smtp.tuempresa.com",
    "port": 587,
    "username": "tu_email@tuempresa.com",
    "password": "tu_contraseña"
  }
}
```

### Puertos comunes:
- **587**: STARTTLS (recomendado) - usado por este script
- **465**: SSL/TLS
- **25**: Sin cifrado (no recomendado)

---

## 📮 Zoho Mail

### Configuración en config.json:
```json
{
  "recipient_email": "tu_email@zoho.com",
  "smtp_config": {
    "server": "smtp.zoho.com",
    "port": 587,
    "username": "tu_email@zoho.com",
    "password": "tu_contraseña"
  }
}
```

---

## 📮 ProtonMail

ProtonMail requiere ProtonMail Bridge para SMTP:

1. Descarga ProtonMail Bridge: https://proton.me/mail/bridge
2. Instala y configura Bridge
3. Obtén las credenciales SMTP de Bridge

### Configuración en config.json:
```json
{
  "recipient_email": "tu_email@protonmail.com",
  "smtp_config": {
    "server": "127.0.0.1",
    "port": 1025,
    "username": "tu_email@protonmail.com",
    "password": "contraseña_de_bridge"
  }
}
```

---

## 🔧 Solución de Problemas Comunes

### Error: Authentication failed
- ✅ Verifica que uses contraseña de aplicación (no la normal)
- ✅ Revisa que la verificación en 2 pasos esté activa
- ✅ Comprueba que usuario y contraseña sean correctos

### Error: Connection timeout
- ✅ Verifica el servidor SMTP y el puerto
- ✅ Comprueba tu firewall/antivirus
- ✅ Revisa tu conexión a internet

### Error: Certificate verification failed
- ✅ Actualiza Python: `pip install --upgrade certifi`
- ✅ Verifica la fecha/hora de tu sistema

### Los correos van a spam
- ✅ Marca el primer correo como "No es spam"
- ✅ Añade el remitente a tus contactos
- ✅ Revisa las reglas de filtrado de tu correo

---

## 🧪 Probar la Configuración

Después de configurar, siempre ejecuta la prueba:

```bash
python test_email.py
```

Si ves ✅ y recibes el correo, ¡todo está bien!

---

## 💡 Consejos de Seguridad

1. **NUNCA compartas tu archivo config.json** - contiene credenciales
2. **Usa contraseñas de aplicación** cuando sea posible
3. **No subas config.json a Git** (ya está en .gitignore)
4. **Cambia las contraseñas** si sospechas que fueron comprometidas
5. **Revisa los accesos** a tu cuenta periódicamente

---

## 📞 Soporte Adicional

Si tu proveedor no está listado:

1. Busca "configuración SMTP [tu proveedor]" en Google
2. Necesitas: servidor SMTP, puerto, y si usa TLS/SSL
3. Prueba con el puerto 587 (STARTTLS) primero
4. Si no funciona, prueba 465 (SSL) o contacta a tu proveedor

---

**¿Todo configurado?** 🎉

Ejecuta: `python test_email.py` para verificar

Luego: `python main.py` para empezar a monitorear el BOE
