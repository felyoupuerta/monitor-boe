#!/usr/bin/env python3
import json
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

def test_email_config():
    config_path = Path('config.json')
    if not config_path.exists():
        print("Error: No se encuentra config.json")
        print("   Crea el archivo a partir de config.example.json")
        return False
    
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    recipient = config['recipient_email']
    smtp_config = config['smtp_config']
    if isinstance(recipient, list):
        recipient_str = ", ".join(recipient)
    else:
        recipient_str = recipient
    
    print("=" * 60)
    print("Prueba de Configuración de Correo Electrónico")
    print("=" * 60)
    print()
    print(f"Servidor SMTP: {smtp_config['server']}:{smtp_config['port']}")
    print(f"Usuario: {smtp_config['username']}")
    print(f"Destinatario: {recipient_str}")
    print()
    print("Intentando enviar correo de prueba...")
    print()
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Prueba de BOE Monitor - Configuración Correcta"
    msg['From'] = smtp_config['username']
    msg['To'] = recipient_str
    
    html_content = """
    <html>
    <head>
        <style>
            body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
            .header { background-color: #28a745; color: white; padding: 20px; text-align: center; border-radius: 5px; }
            .content { padding: 20px; }
            .success { color: #28a745; font-weight: bold; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>¡Configuración Exitosa!</h1>
        </div>
        <div class="content">
            <h2>Tu BOE Monitor está correctamente configurado</h2>
            <p>Este es un correo de prueba para verificar que el sistema de notificaciones funciona correctamente.</p>
            
            <h3>Próximos pasos:</h3>
            <ol>
                <li>El monitor se ejecutará automáticamente según tu configuración</li>
                <li>Recibirás notificaciones cuando haya cambios en el BOE</li>
                <li>Los datos históricos se guardarán en la carpeta <code>boe_data/</code></li>
            </ol>
            
            <h3>Información de la configuración:</h3>
            <ul>
                <li><strong>Servidor SMTP:</strong> """ + smtp_config['server'] + """</li>
                <li><strong>Usuario:</strong> """ + smtp_config['username'] + """</li>
                <li><strong>Destinatario:</strong> """ + recipient_str + """</li>
            </ul>
            
            <p class="success">¡Todo listo para monitorear el BOE!</p>
            
            <hr>
            <p style="font-size: 0.9em; color: #666;">
                Si recibes este correo, significa que la configuración es correcta y el sistema está funcionando.
            </p>
        </div>
    </body>
    </html>
    """
    
    html_part = MIMEText(html_content, 'html', 'utf-8')
    msg.attach(html_part)
    
    try:
        print("🔌 Conectando al servidor SMTP...")
        with smtplib.SMTP(smtp_config['server'], smtp_config['port'], timeout=10) as server:
            print("Iniciando conexión segura (TLS)...")
            server.starttls()
            
            print("Autenticando usuario...")
            server.login(smtp_config['username'], smtp_config['password'])
            
            print("Enviando correo de prueba...")
            server.send_message(msg)
        
        print()
        print("=" * 60)
        print("¡ÉXITO! El correo de prueba se envió correctamente")
        print("=" * 60)
        print()
        print(f"Revisa tu bandeja de entrada en: {recipient_str}")
        print()
        print("Si no lo ves, revisa la carpeta de spam.")
        print()
        print("Ahora puedes ejecutar el monitor principal:")
        print("  python main.py")
        print()
        return True
        
    except smtplib.SMTPAuthenticationError:
        print()
        print("=" * 60)
        print("ERROR DE AUTENTICACIÓN")
        print("=" * 60)
        print()
        print("Las credenciales son incorrectas. Verifica:")
        print()
        print("Para Gmail:")
        print("  1. Asegúrate de tener activada la verificación en 2 pasos")
        print("  2. Usa una 'Contraseña de aplicación', NO tu contraseña normal")
        print("  3. Genera una aquí: https://myaccount.google.com/apppasswords")
        print()
        print("Para otros proveedores:")
        print("  1. Verifica que el usuario y contraseña sean correctos")
        print("  2. Revisa que el servidor SMTP y puerto sean los correctos")
        print()
        return False
        
    except smtplib.SMTPException as e:
        print()
        print("=" * 60)
        print("ERROR DE SMTP")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        print("Verifica:")
        print(f"  - Servidor: {smtp_config['server']}")
        print(f"  - Puerto: {smtp_config['port']}")
        print("  - Tu conexión a internet")
        print()
        return False
        
    except Exception as e:
        print()
        print("=" * 60)
        print("ERROR INESPERADO")
        print("=" * 60)
        print(f"Error: {e}")
        print()
        return False

if __name__ == "__main__":
    success = test_email_config()
    sys.exit(0 if success else 1)
