import os

def create_missing_structure():
    # Lo que falta por crear
    missing_structure = {
        'docs/dataset.md': '',
        'db/schema.sql': '',
        'db/ddl/001_tables.sql': '',
        'app-image/Dockerfile': '',
        'app-image/requirements.txt': '',
        'data/.gitkeep': ''
    }
    
    for path, content in missing_structure.items():
        directory = os.path.dirname(path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            print(f"📁 Creado directorio: {directory}")
        
        if not os.path.exists(path):
            with open(path, 'w') as f:
                f.write(content)
            print(f"📄 Creado archivo: {path}")

if __name__ == "__main__":
    print("🔧 Creando estructura faltante...")
    create_missing_structure()
    print("✅ Estructura completada!")