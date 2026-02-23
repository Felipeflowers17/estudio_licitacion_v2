import pandas as pd
from src.bd.database import SessionLocal, engine
from src.bd.models import Organismo

def cargar_organismos_desde_csv():
    print("="*60)
    print("INICIANDO CARGA MASIVA DE ORGANISMOS")
    print("="*60)
    
    archivo_csv = "Listado organismos compradores.csv"
    
    try:
        # 1. Leer el CSV con Pandas
        df = pd.read_csv(archivo_csv, sep=';', encoding='utf-8')
        
        print(f"Archivo leído correctamente. Filas encontradas: {len(df)}")
        print("Columnas detectadas:", df.columns.tolist())
        
        # 2. Conectar a la Base de Datos
        # Eliminada la instrucción Base.metadata.create_all()
        # La estructura de la base de datos debe gestionarse vía Alembic
        session = SessionLocal()
        
        contador_nuevos = 0
        contador_existentes = 0
        
        print("\nProcesando registros...")
        
        # 3. Iterar y Guardar
        for index, row in df.iterrows():
            codigo_str = str(row['Código']).strip()
            nombre_org = str(row['Nombre de la institución']).strip()
            
            organismo_existente = session.query(Organismo).filter_by(codigo=codigo_str).first()
            
            if organismo_existente:
                if organismo_existente.nombre != nombre_org:
                    organismo_existente.nombre = nombre_org
                contador_existentes += 1
            else:
                nuevo_org = Organismo(
                    codigo=codigo_str,
                    nombre=nombre_org,
                    puntaje=0
                )
                session.add(nuevo_org)
                contador_nuevos += 1
            
            # Guardamos por lotes cada 100 registros para no saturar la RAM
            if index % 100 == 0:
                session.commit()
                print(f"   ... procesados {index} registros")
        
        # Commit final
        session.commit()
        
        print("\n" + "="*60)
        print("CARGA COMPLETADA EXITOSAMENTE")
        print(f"   - Organismos Nuevos agregados: {contador_nuevos}")
        print(f"   - Organismos Existentes actualizados: {contador_existentes}")
        print(f"   - Total en base de datos: {session.query(Organismo).count()}")
        print("="*60)
        
    except FileNotFoundError:
        print(f"Error: No se encuentra el archivo '{archivo_csv}' en la raíz.")
    except Exception as e:
        print(f"Error crítico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'session' in locals():
            session.close()

if __name__ == "__main__":
    cargar_organismos_desde_csv()