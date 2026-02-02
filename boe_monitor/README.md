### BOE
### FELIPE ANGERIZ 


### DEPENDENCIAS 
pip install -r requirements.txt

### archivo de configruracion
config.json  


### Estructura de archivos

boe_monitor/
├── main.py                  # Archivo main del proyecto, este importa a boe analyzer
├── boe_analyzer.py          #Script principal
├── config.json              #configuración
├── README.md               
├── boe_data/               # datos boe pasados
│   ├── boe_20240101.json
│   ├── boe_20240102.json
│   └── +++
└── logs/                   # Logs de ejecución

ejecutar analisi de Francia:
            python main.py --country fr

España:
            python main.py --country es


ARCHIVOS DE EJECUCION:
            /opt/run_monitor_espania.sh
            /opt/run_monitor_francia.sh

PARA EL CRONTAB LOS MOBIMOS COMO UN BINARIO:
            /usr/bin/monesp -----> monitor - españa(esp)
            /usr/bin/monfr -----> monitor - francia(fr)

ARCHIVO EN CRONTAB DE ROOT(SE EJECUTA TODOS LOS DÍAS A LAS 8 DE LA MAÑANA):
            0 8 * * * /usr/bin/monesp
            0 8 * * * /usr/bin/monfr




EXTRA POR SI SE TRABAJA COMO YO EN WINDOWS Y UNIX(POR LAS DUDAS):
            comando para pasar archivos de windows a UNIX(problemas con los espacios en blanco)
            sudo pacman -S dos2unix
            dos2unix <nombre del archivo>
