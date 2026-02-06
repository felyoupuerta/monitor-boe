#!/usr/bin/env python3
"""
Script de prueba de configuración de correo electrónico.
Verifica que la configuración SMTP sea correcta.
"""

import json
import sys
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

sys.path.insert(0, str(Path(__file__).parent.parent))
from logger_config import setup_logger

logger = setup_logger("test_email")


def test_email_config() -> bool:
    """
    Prueba la configuración de correo electrónico.
    
    Returns:
        True si la prueba fue exitosa
    """
    config_path = Path(__file__).parent.parent / 'config.json'
    
    if not config_path.exists():
        logger.error(f"Archivo de configuración no encontrado: {config_path}")
        print("\nCrea el archivo config.json a partir de config.example.json")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        logger.error(f"Error al leer config.json: {e}")
        return False
    
    # Extraer configuración
    recipient = config.get('recipient_email', [])
    smtp_config = config.get('smtp_config', {})
    
    if not smtp_config:
        logger.error("Configuración SMTP no encontrada")
        return False
    
    # Preparar destinatarios
    if isinstance(recipient, list):
        recipient_str = ", ".join(recipient)
    else:
        recipient_str = str(recipient)
    
    print("=" * 70)
    print("PRUEBA DE CONFIGURACIÓN DE CORREO ELECTRÓNICO".center(70))
    print("=" * 70)
    print()
    print(f"Servidor SMTP: {smtp_config.get('server')}:{smtp_config.get('port')}")
    print(f"Usuario: {smtp_config.get('username')}")
    print(f"Destinatario(s): {recipient_str}")
    print()
    print("Intentando enviar correo de prueba...")
    print()
    
    # Crear mensaje
    msg = MIMEMultipart('alternative')
    msg['Subject'] = "Prueba BOE Monitor - ¡Configuración Correcta!"
    msg['From'] = smtp_config.get('username', '')
    msg['To'] = recipient_str
    
    # Contenido HTML
    html_content = """
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                color: #333;
                background-color: #f4f4f4;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background-color: #ffffff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                background-color: #28a745;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 24px;
            }}
            .content h2 {{
                color: #2c3e50;
            }}
            .success {{
                color: #28a745;
                font-weight: bold;
            }}
            .info-box {{
                background-color: #ecf0f1;
                padding: 15px;
                border-left: 4px solid #3498db;
                margin: 20px 0;
                border-radius: 4px;
            }}
            .footer {{
                text-align: center;
                font-size: 12px;
                color: #7f8c8d;
                margin-top: 30px;
                border-top: 1px solid #ecf0f1;
                padding-top: 20px;
            }}
            ol {{
                line-height: 2;
            }}
            code {{
                background-color: #f4f4f4;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', monospace;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✓ ¡Configuración Exitosa!</h1>
            </div>
            
            <div class="content">
                <h2>Tu BOE Monitor está correctamente configurado</h2>
                
                <p>Este es un correo de prueba para verificar que el sistema de notificaciones 
                funciona correctamente.</p>
                
                <div class="info-box">
                    <h3>Próximos pasos:</h3>
                    <ol>
                        <li>El monitor se ejecutará automáticamente según tu configuración</li>
                        <li>Recibirás notificaciones cuando haya cambios en el BOE</li>
                        <li>Los datos históricos se guardarán en la carpeta <code>boe_data/</code></li>
                        <li>Revisa los logs en <code>logs/</code> para detalles de ejecución</li>
                    </ol>
                </div>
                
                <h3>Información de la configuración:</h3>
                <ul>
                    <li><strong>Servidor SMTP:</strong> """ + smtp_config.get('server', '') + """</li>
                    <li><strong>Puerto:</strong> """ + str(smtp_config.get('port', '')) + """</li>
                    <li><strong>Usuario:</strong> """ + smtp_config.get('username', '') + """</li>
                </ul>
                
                <div class="info-box">
                    <p class="success">¡Todo listo! El sistema está funcionando correctamente.</p>
                </div>
            </div>
            
            <div class="footer">
                <p>Si recibes este correo, significa que la configuración es correcta y el sistema está listo para monitorear el BOE.</p>
                <p>BOE Monitor - Generado automáticamente</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    try:
        print("🔌 Conectando al servidor SMTP...")
        
        with smtplib.SMTP(smtp_config.get('server', ''), smtp_config.get('port', 587), timeout=10) as server:
            print("  → Iniciando conexión segura (TLS)...")
            server.starttls()
            
            print("  → Autenticando usuario...")
            server.login(smtp_config.get('username', ''), smtp_config.get('password', ''))
            
            print("  → Enviando correo de prueba...")
            server.send_message(msg)
        
        print()
        print("=" * 70)
        print("¡ÉXITO! El correo de prueba se envió correctamente".center(70))
        print("=" * 70)
        print()
        print(f"✓ Revisa tu bandeja de entrada: {recipient_str}")
        print()
        print("Si no lo ves en pocos minutos, revisa la carpeta de SPAM.")
        print()
        
        logger.info("Prueba de correo exitosa")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print()
        print("=" * 70)
        print("ERROR DE AUTENTICACIÓN".center(70))
        print("=" * 70)
        print()
        print("Las credenciales son incorrectas. Verifica:")
        print()
        print("Para Gmail:")
        print("  1. Habilita verificación en 2 pasos en tu cuenta de Google")
        print("  2. Usa una 'Contraseña de aplicación', NO tu contraseña normal")
        print("  3. Genera una aquí: https://myaccount.google.com/apppasswords")
        print()
        print("Para otros proveedores:")
        print("  1. Verifica que el usuario y contraseña sean correctos")
        print("  2. Revisa que el servidor SMTP y puerto sean los correctos")
        print()
        
        logger.error("Error de autenticación SMTP")
        return False
        
    except smtplib.SMTPException as e:
        print()
        print("=" * 70)
        print("ERROR DE SMTP".center(70))
        print("=" * 70)
        print(f"Error: {e}")
        print()
        print("Verifica:")
        print(f"  • Servidor: {smtp_config.get('server')}")
        print(f"  • Puerto: {smtp_config.get('port')}")
        print("  • Tu conexión a internet")
        print("  • Que el servidor SMTP permita conexiones TLS")
        print()
        
        logger.error(f"Error SMTP: {e}")
        return False
        
    except Exception as e:
        print()
        print("=" * 70)
        print("ERROR INESPERADO".center(70))
        print("=" * 70)
        print(f"Error: {e}")
        print()
        print("Detalles del error:")
        import traceback
        traceback.print_exc()
        print()
        
        logger.error(f"Error inesperado: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    success = test_email_config()
    sys.exit(0 if success else 1)
