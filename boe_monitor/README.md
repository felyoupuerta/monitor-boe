### BOE
### FELIPE ANGERIZ 


### DEPENDENCIAS 
pip install -r requirements.txt

### archivo de configruracion
nano config.json  


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


